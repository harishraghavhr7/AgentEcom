"""
FastMCP Server implementation for AgentEcom.
Implements the Model Context Protocol (MCP v2024-11-05) specification:
- Tools: dynamic registration, JSON schema reflection, and execution.
- Prompts: prompt templates, parameterized arguments, and rendering.
- Resources: static and parameterized URI resources.
- Transports: Direct in-memory, FastAPI / SSE, HTTP JSON-RPC, and stdio.
"""

import sys
import json
import inspect
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union, get_type_hints
from pydantic import BaseModel
from fastapi import FastAPI, Request, APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger("agentecom.mcp")

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class MCPPromptArgument(BaseModel):
    name: str
    description: Optional[str] = None
    required: bool = True

class MCPPromptDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: List[MCPPromptArgument] = []

class MCPResourceDefinition(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: str = "application/json"


def python_type_to_json_schema(py_type: Any) -> Dict[str, Any]:
    """Map python types and typing hints to JSON Schema types."""
    if py_type in (str, Optional[str]):
        return {"type": "string"}
    if py_type in (int, Optional[int]):
        return {"type": "integer"}
    if py_type in (float, Optional[float]):
        return {"type": "number"}
    if py_type in (bool, Optional[bool]):
        return {"type": "boolean"}
    if getattr(py_type, "__origin__", None) is list:
        elem_args = getattr(py_type, "__args__", [str])
        elem_schema = python_type_to_json_schema(elem_args[0]) if elem_args else {"type": "string"}
        return {"type": "array", "items": elem_schema}
    if getattr(py_type, "__origin__", None) is dict:
        return {"type": "object"}
    if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
        return py_type.model_json_schema()
    return {"type": "string"}


class FastMCPServer:
    """
    High-Performance FastMCP Server for AgentEcom.
    Coordinates tools, prompts, resources, and database gateways.
    """

    def __init__(self, name: str = "agentecom-mcp-server", version: str = "2.0.0"):
        self.name = name
        self.version = version
        self._tools: Dict[str, Callable] = {}
        self._tool_definitions: Dict[str, MCPToolDefinition] = {}
        self._prompts: Dict[str, Callable] = {}
        self._prompt_definitions: Dict[str, MCPPromptDefinition] = {}
        self._resources: Dict[str, Callable] = {}
        self._resource_definitions: Dict[str, MCPResourceDefinition] = {}
        self._active_sse_queues: Dict[str, asyncio.Queue] = {}

    # --------------------------------------------------------------------------
    # 1. Registration Decorators
    # --------------------------------------------------------------------------

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator to register a tool on the FastMCP Server.
        Automatically reflects parameter schemas from function signature and docstrings.
        """
        def decorator(func: Callable):
            tool_name = name or func.__name__
            doc = description or (inspect.getdoc(func) or "").strip()
            
            sig = inspect.signature(func)
            type_hints = {}
            try:
                type_hints = get_type_hints(func)
            except Exception:
                pass

            properties = {}
            required = []

            for p_name, param in sig.parameters.items():
                if p_name in ("self", "cls"):
                    continue
                p_type = type_hints.get(p_name, param.annotation if param.annotation != inspect.Parameter.empty else str)
                
                # Check if param is a Pydantic model
                if inspect.isclass(p_type) and issubclass(p_type, BaseModel):
                    schema = p_type.model_json_schema()
                    properties[p_name] = schema
                else:
                    properties[p_name] = python_type_to_json_schema(p_type)

                if param.default == inspect.Parameter.empty:
                    required.append(p_name)

            input_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }

            self._tools[tool_name] = func
            self._tool_definitions[tool_name] = MCPToolDefinition(
                name=tool_name,
                description=doc or f"Executes {tool_name}",
                inputSchema=input_schema
            )
            return func
        return decorator

    def prompt(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator to register an MCP Prompt template.
        """
        def decorator(func: Callable):
            p_name = name or func.__name__
            doc = description or (inspect.getdoc(func) or "").strip()
            sig = inspect.signature(func)
            
            args = []
            for arg_name, param in sig.parameters.items():
                if arg_name in ("self", "cls"):
                    continue
                is_req = (param.default == inspect.Parameter.empty)
                args.append(MCPPromptArgument(name=arg_name, description=f"Argument: {arg_name}", required=is_req))

            self._prompts[p_name] = func
            self._prompt_definitions[p_name] = MCPPromptDefinition(
                name=p_name,
                description=doc or f"Prompt template {p_name}",
                arguments=args
            )
            return func
        return decorator

    def resource(self, uri: str, name: Optional[str] = None, description: Optional[str] = None, mime_type: str = "application/json"):
        """
        Decorator to register an MCP Resource.
        """
        def decorator(func: Callable):
            res_name = name or func.__name__
            doc = description or (inspect.getdoc(func) or "").strip()
            self._resources[uri] = func
            self._resource_definitions[uri] = MCPResourceDefinition(
                uri=uri,
                name=res_name,
                description=doc or f"Resource at {uri}",
                mimeType=mime_type
            )
            return func
        return decorator

    # --------------------------------------------------------------------------
    # 2. Execution & Query APIs
    # --------------------------------------------------------------------------

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered tool directly with given arguments."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found on FastMCP Server.")
        func = self._tools[name]
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {name}: {e}")
            raise

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render a registered prompt with given arguments."""
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not found on FastMCP Server.")
        func = self._prompts[name]
        args = arguments or {}
        try:
            if inspect.iscoroutinefunction(func):
                rendered = await func(**args)
            else:
                rendered = func(**args)
            
            if isinstance(rendered, str):
                messages = [{"role": "user", "content": {"type": "text", "text": rendered}}]
            elif isinstance(rendered, list):
                messages = rendered
            else:
                messages = [{"role": "user", "content": {"type": "text", "text": str(rendered)}}]

            return {
                "description": self._prompt_definitions[name].description,
                "messages": messages
            }
        except Exception as e:
            logger.exception(f"Error rendering prompt {name}: {e}")
            raise

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a registered resource by URI (exact or pattern match)."""
        func = self._resources.get(uri)
        matched_args = {}

        if not func:
            # Check pattern match (e.g. orders://{order_number})
            for pattern_uri, handler in self._resources.items():
                if "{" in pattern_uri and "}" in pattern_uri:
                    # Simple pattern matcher
                    prefix = pattern_uri.split("{")[0]
                    suffix = pattern_uri.split("}")[1] if len(pattern_uri.split("}")) > 1 else ""
                    if uri.startswith(prefix) and (not suffix or uri.endswith(suffix)):
                        param_name = pattern_uri[len(prefix):pattern_uri.find("}")]
                        param_val = uri[len(prefix):len(uri)-len(suffix) if suffix else None]
                        matched_args[param_name] = param_val
                        func = handler
                        break

        if not func:
            raise KeyError(f"Resource '{uri}' not found on FastMCP Server.")

        try:
            if inspect.iscoroutinefunction(func):
                content = await func(**matched_args)
            else:
                content = func(**matched_args)
            
            text_val = json.dumps(content, indent=2) if isinstance(content, (dict, list)) else str(content)
            mime = self._resource_definitions.get(uri, MCPResourceDefinition(uri=uri, name="dynamic", mimeType="application/json")).mimeType

            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": mime,
                        "text": text_val
                    }
                ]
            }
        except Exception as e:
            logger.exception(f"Error reading resource {uri}: {e}")
            raise

    # --------------------------------------------------------------------------
    # 3. Model Context Protocol JSON-RPC 2.0 Handler
    # --------------------------------------------------------------------------

    async def handle_jsonrpc(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes standard JSON-RPC 2.0 MCP requests:
        initialize, tools/list, tools/call, prompts/list, prompts/get, resources/list, resources/read.
        """
        req_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {}) or {}

        def success_resp(result: Any) -> Dict[str, Any]:
            resp = {"jsonrpc": "2.0", "result": result}
            if req_id is not None:
                resp["id"] = req_id
            return resp

        def error_resp(code: int, message: str, data: Any = None) -> Dict[str, Any]:
            resp = {
                "jsonrpc": "2.0",
                "error": {"code": code, "message": message}
            }
            if data is not None:
                resp["error"]["data"] = data
            if req_id is not None:
                resp["id"] = req_id
            return resp

        if not method:
            return error_resp(-32600, "Invalid Request: 'method' field is required")

        # 1. MCP Lifecycle: initialize
        if method == "initialize":
            return success_resp({
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "prompts": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "logging": {}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            })

        # 2. MCP Lifecycle: notifications/initialized or ping
        if method in ("notifications/initialized", "initialized"):
            return success_resp({"status": "acknowledged"})
        if method == "ping":
            return success_resp({})

        # 3. Tools
        if method == "tools/list":
            tools_list = [t.model_dump() for t in self._tool_definitions.values()]
            return success_resp({"tools": tools_list})

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if not tool_name or tool_name not in self._tools:
                return error_resp(-32602, f"Tool '{tool_name}' not found")
            try:
                res = await self.call_tool(tool_name, arguments)
                text_content = json.dumps(res, indent=2) if isinstance(res, (dict, list)) else str(res)
                return success_resp({
                    "content": [{"type": "text", "text": text_content}],
                    "isError": False
                })
            except Exception as e:
                return success_resp({
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                })

        # 4. Prompts
        if method == "prompts/list":
            prompts_list = [p.model_dump() for p in self._prompt_definitions.values()]
            return success_resp({"prompts": prompts_list})

        if method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})
            if not prompt_name or prompt_name not in self._prompts:
                return error_resp(-32602, f"Prompt '{prompt_name}' not found")
            try:
                rendered = await self.get_prompt(prompt_name, arguments)
                return success_resp(rendered)
            except Exception as e:
                return error_resp(-32000, f"Prompt render failure: {str(e)}")

        # 5. Resources
        if method == "resources/list":
            res_list = [r.model_dump() for r in self._resource_definitions.values()]
            return success_resp({"resources": res_list})

        if method == "resources/read":
            uri = params.get("uri")
            if not uri:
                return error_resp(-32602, "Resource 'uri' parameter is required")
            try:
                content = await self.read_resource(uri)
                return success_resp(content)
            except KeyError:
                return error_resp(-32002, f"Resource URI '{uri}' not found")
            except Exception as e:
                return error_resp(-32000, f"Resource read failure: {str(e)}")

        return error_resp(-32601, f"Method '{method}' not implemented")

    # --------------------------------------------------------------------------
    # 4. FastAPI & SSE Transport Integration
    # --------------------------------------------------------------------------

    def mount_to_fastapi(self, app: FastAPI, prefix: str = "/mcp") -> APIRouter:
        """
        Mounts FastMCP Server endpoints onto a FastAPI application:
        - GET  {prefix}/sse: Server-Sent Events stream for MCP sessions
        - POST {prefix}/messages: JSON-RPC message inbox
        - POST {prefix}/rpc: Direct stateless JSON-RPC 2.0 handler
        - GET  {prefix}/tools: REST list of registered tools
        - GET  {prefix}/prompts: REST list of registered prompts
        - GET  {prefix}/resources: REST list of registered resources
        """
        router = APIRouter(prefix=prefix, tags=["Model Context Protocol (FastMCP)"])

        @router.get("/health")
        async def mcp_health():
            return {
                "server": self.name,
                "version": self.version,
                "protocol": "MCP 2024-11-05",
                "registered_tools_count": len(self._tools),
                "registered_prompts_count": len(self._prompts),
                "registered_resources_count": len(self._resources),
                "status": "online"
            }

        @router.post("/rpc")
        async def json_rpc_handler(request: Request):
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            response = await self.handle_jsonrpc(body)
            return JSONResponse(content=response)

        @router.get("/sse")
        async def sse_endpoint(request: Request):
            """
            MCP standard SSE transport connection.
            Emits an initial endpoint notification so the client knows where to POST messages.
            """
            import uuid
            session_id = f"mcp_sess_{uuid.uuid4().hex[:12]}"
            queue: asyncio.Queue = asyncio.Queue()
            self._active_sse_queues[session_id] = queue

            async def event_generator():
                try:
                    # Initial endpoint event per MCP SSE spec
                    endpoint_uri = f"{prefix}/messages?sessionId={session_id}"
                    yield f"event: endpoint\ndata: {endpoint_uri}\n\n"

                    while True:
                        if await request.is_disconnected():
                            break
                        try:
                            msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                            yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                        except asyncio.TimeoutError:
                            # Keep-alive comment
                            yield ": keep-alive\n\n"
                finally:
                    self._active_sse_queues.pop(session_id, None)

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        @router.post("/messages")
        async def post_message(request: Request, sessionId: Optional[str] = None):
            try:
                payload = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")

            response = await self.handle_jsonrpc(payload)

            # If sessionId is connected via SSE, dispatch response to their queue
            if sessionId and sessionId in self._active_sse_queues:
                await self._active_sse_queues[sessionId].put(response)
                return JSONResponse({"status": "accepted"})

            # Direct response if stateless
            return JSONResponse(response)

        @router.get("/tools")
        async def list_tools():
            return {"tools": [t.model_dump() for t in self._tool_definitions.values()]}

        @router.get("/prompts")
        async def list_prompts():
            return {"prompts": [p.model_dump() for p in self._prompt_definitions.values()]}

        @router.get("/resources")
        async def list_resources():
            return {"resources": [r.model_dump() for r in self._resource_definitions.values()]}

        app.include_router(router)
        return router

    # --------------------------------------------------------------------------
    # 5. stdio CLI Mode (Claude Desktop / Cursor support)
    # --------------------------------------------------------------------------

    async def run_stdio(self):
        """Run standard stdio loop for desktop MCP clients."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        writer_transport, writer_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            try:
                req = json.loads(line.decode("utf-8").strip())
                resp = await self.handle_jsonrpc(req)
                writer.write((json.dumps(resp) + "\n").encode("utf-8"))
                await writer.drain()
            except Exception as e:
                err = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": None
                }
                writer.write((json.dumps(err) + "\n").encode("utf-8"))
                await writer.drain()


# Global Singleton Server
fastmcp_server = FastMCPServer(name="AgentEcom FastMCP Commerce Server", version="2.0.0")
