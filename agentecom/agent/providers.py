"""
Multi-Model Provider Integrations & Resilient Fallback Cascade for AgentEcom.
Supported Providers:
1. OpenRouter (OpenAI-compatible high-performance routing API)
2. Google Gemini (Native Generative Language v1beta API)
3. Groq (High-speed Cloud LLM API via ChatGroq)
4. Ollama (Local LLM via ChatOllama)
5. Local Deterministic Tool Planner (Offline Zero-Key Fallback)
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Sequence
import httpx
from pydantic import Field

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage
)
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun
)

from agentecom.config import settings, reload_settings

logger = logging.getLogger("agentecom.providers")


# ==============================================================================
# 1. Schema Sanitization Helpers for OpenRouter & Gemini
# ==============================================================================

def sanitize_schema_for_gemini(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes Pydantic JSON schemas into Google Gemini v1beta schema specifications.
    Removes unsupported keys ($schema, title, anyOf) and capitalizes types.
    """
    clean: Dict[str, Any] = {}
    stype = schema.get("type")
    
    # Handle Optional types represented as anyOf: [{'type': 'string'}, {'type': 'null'}]
    if not stype and "anyOf" in schema:
        types = [x.get("type") for x in schema["anyOf"] if x.get("type") != "null"]
        stype = types[0] if types else "STRING"
        
    raw_type = (stype or "STRING").upper()
    if raw_type in ["STR", "STRING", "TEXT"]:
        clean["type"] = "STRING"
    elif raw_type in ["INT", "INTEGER"]:
        clean["type"] = "INTEGER"
    elif raw_type in ["FLOAT", "NUMBER", "DECIMAL"]:
        clean["type"] = "NUMBER"
    elif raw_type in ["BOOL", "BOOLEAN"]:
        clean["type"] = "BOOLEAN"
    elif raw_type in ["ARRAY", "LIST"]:
        clean["type"] = "ARRAY"
    elif raw_type in ["OBJECT", "DICT"]:
        clean["type"] = "OBJECT"
    else:
        clean["type"] = "STRING"

    if "description" in schema:
        clean["description"] = str(schema["description"])
    if "enum" in schema:
        clean["enum"] = [str(e) for e in schema["enum"]]

    if clean["type"] == "OBJECT" or "properties" in schema:
        clean["type"] = "OBJECT"
        clean["properties"] = {}
        for prop, prop_schema in schema.get("properties", {}).items():
            clean["properties"][prop] = sanitize_schema_for_gemini(prop_schema)
        if "required" in schema and isinstance(schema["required"], list):
            clean["required"] = [str(r) for r in schema["required"]]
    elif clean["type"] == "ARRAY" or "items" in schema:
        clean["type"] = "ARRAY"
        items = schema.get("items", {"type": "STRING"})
        clean["items"] = sanitize_schema_for_gemini(items)

    return clean


def format_messages_for_openai(messages: Sequence[BaseMessage]) -> List[Dict[str, Any]]:
    """Formats LangChain messages into standard OpenAI chat completion messages."""
    formatted = []
    for m in messages:
        if isinstance(m, SystemMessage):
            formatted.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            formatted.append({"role": "user", "content": m.content})
        elif isinstance(m, ToolMessage):
            formatted.append({
                "role": "tool",
                "tool_call_id": getattr(m, "tool_call_id", f"call_{uuid.uuid4().hex[:8]}"),
                "content": str(m.content)
            })
        elif isinstance(m, AIMessage):
            msg_dict: Dict[str, Any] = {"role": "assistant", "content": m.content or ""}
            if hasattr(m, "tool_calls") and m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc.get("args", {}))
                        }
                    }
                    for tc in m.tool_calls
                ]
            formatted.append(msg_dict)
        else:
            formatted.append({"role": "user", "content": getattr(m, "content", "")})
    return formatted


# ==============================================================================
# 2. OpenRouter Chat Model
# ==============================================================================

class ChatOpenRouter(BaseChatModel):
    """
    Native LangChain ChatModel implementation for OpenRouter API.
    Provides high-speed routing to Llama 3.3, Claude, GPT-4o-mini, Mistral, and more.
    """
    api_key: str
    model_name: str = "meta-llama/llama-3.3-70b-instruct"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.2
    timeout_seconds: float = 35.0
    bound_tools: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "openrouter-chat"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ChatOpenRouter":
        schemas = []
        for t in tools:
            if hasattr(t, "args_schema") and t.args_schema:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.args_schema.model_json_schema()
                    }
                })
            elif isinstance(t, dict):
                schemas.append(t)
        return self.model_copy(update={"bound_tools": schemas})

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        import asyncio
        return asyncio.run(self._agenerate(messages, stop=stop, **kwargs))

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        formatted = format_messages_for_openai(messages)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted,
            "temperature": self.temperature,
        }
        if self.bound_tools:
            payload["tools"] = self.bound_tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AgentEcom",
            "X-Title": "AgentEcom Autonomous Shopping Agent",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    err_text = err_json.get("error", {}).get("message", err_text)
                except Exception:
                    pass
                raise RuntimeError(f"OpenRouter API error ({resp.status_code}): {err_text}")
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenRouter API returned no choices: {data}")

        choice_msg = choices[0].get("message", {})
        content = choice_msg.get("content") or ""
        tool_calls = []

        raw_tcs = choice_msg.get("tool_calls", [])
        if raw_tcs:
            for rtc in raw_tcs:
                fn = rtc.get("function", {})
                name = fn.get("name")
                raw_args = fn.get("arguments", "{}")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                else:
                    args = raw_args or {}
                tool_calls.append({
                    "name": name,
                    "args": args,
                    "id": rtc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                })

        ai_msg = AIMessage(content=content, tool_calls=tool_calls)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])


# ==============================================================================
# 3. Google Gemini Chat Model
# ==============================================================================

class ChatGemini(BaseChatModel):
    """
    Native LangChain ChatModel implementation for Google Gemini REST API.
    Supports gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro with function calling.
    """
    api_key: str
    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.2
    timeout_seconds: float = 35.0
    bound_tools: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "gemini-chat"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ChatGemini":
        declarations = []
        for t in tools:
            if hasattr(t, "args_schema") and t.args_schema:
                raw_schema = t.args_schema.model_json_schema()
                sanitized = sanitize_schema_for_gemini(raw_schema)
                declarations.append({
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": sanitized
                })
            elif isinstance(t, dict):
                declarations.append(t)
        return self.model_copy(update={"bound_tools": declarations})

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        import asyncio
        return asyncio.run(self._agenerate(messages, stop=stop, **kwargs))

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        contents = []
        system_texts = []

        for m in messages:
            if isinstance(m, SystemMessage):
                system_texts.append(m.content)
            elif isinstance(m, HumanMessage):
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif isinstance(m, AIMessage):
                parts = []
                if m.content:
                    parts.append({"text": m.content})
                if hasattr(m, "tool_calls") and m.tool_calls:
                    for tc in m.tool_calls:
                        parts.append({"functionCall": {"name": tc["name"], "args": tc.get("args", {})}})
                if not parts:
                    parts.append({"text": " "})
                contents.append({"role": "model", "parts": parts})
            elif isinstance(m, ToolMessage):
                t_name = getattr(m, "name", "commerce_tool") or "commerce_tool"
                # Content can be dict or json str
                c_data = m.content
                if isinstance(c_data, str):
                    try:
                        c_data = json.loads(c_data)
                    except Exception:
                        c_data = {"output": m.content}
                elif not isinstance(c_data, dict):
                    c_data = {"output": str(c_data)}

                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": t_name,
                            "response": c_data
                        }
                    }]
                })
            else:
                contents.append({"role": "user", "parts": [{"text": getattr(m, "content", "")}]})

        # Ensure alternating user/model or merge consecutive messages if needed
        merged_contents = []
        for c in contents:
            if merged_contents and merged_contents[-1]["role"] == c["role"]:
                merged_contents[-1]["parts"].extend(c["parts"])
            else:
                merged_contents.append(c)

        # Gemini requires starting with user role
        while merged_contents and merged_contents[0]["role"] == "model":
            merged_contents.pop(0)

        if not merged_contents:
            merged_contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        payload: Dict[str, Any] = {
            "contents": merged_contents,
            "generationConfig": {
                "temperature": self.temperature,
            }
        }

        if system_texts:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_texts)}]
            }

        if self.bound_tools:
            payload["tools"] = [{
                "function_declarations": self.bound_tools
            }]

        clean_model = self.model_name
        if clean_model.startswith("models/"):
            clean_model = clean_model[len("models/"):]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    err_text = err_json.get("error", {}).get("message", err_text)
                except Exception:
                    pass
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {err_text}")
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini API returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_pieces = []
        tool_calls = []

        for part in parts:
            if "text" in part:
                text_pieces.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "name": fc.get("name"),
                    "args": fc.get("args", {}),
                    "id": f"call_{uuid.uuid4().hex[:8]}"
                })

        ai_msg = AIMessage(content="".join(text_pieces), tool_calls=tool_calls)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])


# ==============================================================================
# 4. Ollama Model Resolver
# ==============================================================================

def resolve_ollama_model(preferred_model: Optional[str], base_url: str) -> str:
    """Checks if preferred_model is installed in Ollama; falls back to an available model."""
    target = preferred_model or getattr(settings, "OLLAMA_MODEL_NAME", "llama3.2")
    try:
        import urllib.request
        clean_url = base_url.rstrip("/")
        req = urllib.request.Request(f"{clean_url}/api/tags", headers={"User-Agent": "AgentEcom"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            installed_full = [m.get("name", "") for m in data.get("models", [])]
            installed_short = [m.split(":")[0] for m in installed_full]

            for name in installed_full:
                if name == target or name.startswith(f"{target}:"):
                    return name
            for name in installed_short:
                if name == target:
                    return target

            for candidate in ["llama3.2", "llama3.1", "mistral", "qwen2.5", "llama3"]:
                for full_name in installed_full:
                    if candidate in full_name.lower():
                        return full_name

            if installed_full:
                return installed_full[0]
    except Exception:
        pass
    return target


# ==============================================================================
# 5. Model Factory
# ==============================================================================

def clean_api_key(key: Optional[str]) -> Optional[str]:
    """Cleans API keys by stripping quotes, whitespace, and rejecting placeholder text."""
    if not key:
        return None
    cleaned = str(key).strip().strip("'\"")
    if not cleaned or cleaned.lower() in [
        "none", "null", "undefined", "your_api_key_here",
        "your_groq_api_key", "your_gemini_api_key", "your_openrouter_api_key",
        "gsk_...", "aizasy...", "sk-or-v1-..."
    ]:
        return None
    return cleaned


def create_chat_model(
    provider: str,
    model_name: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> Optional[BaseChatModel]:
    """
    Factory to return configured BaseChatModel for a specific provider.
    Returns None if required credentials or configuration are absent.
    """
    prov = (provider or "").lower().strip()

    # 1. OpenRouter
    if prov in ["openrouter", "open_router"]:
        raw_key = openrouter_api_key or getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
        key = clean_api_key(raw_key)
        if not key:
            refreshed = reload_settings()
            key = clean_api_key(getattr(refreshed, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY"))
        if key:
            m_name = model_name
            if not m_name or "gemini" in m_name.lower() or ("/" not in m_name and "llama" in m_name.lower()):
                m_name = getattr(settings, "OPENROUTER_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")
            b_url = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            return ChatOpenRouter(api_key=key, model_name=m_name, base_url=b_url, temperature=0.2)
        return None

    # 2. Google Gemini
    if prov in ["gemini", "google", "google_gemini"]:
        raw_key = gemini_api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        key = clean_api_key(raw_key)
        if not key:
            refreshed = reload_settings()
            key = clean_api_key(getattr(refreshed, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        if key:
            m_name = model_name
            if not m_name or "llama" in m_name.lower() or "mistral" in m_name.lower() or "qwen" in m_name.lower() or "/" in m_name:
                m_name = getattr(settings, "GEMINI_MODEL_NAME", "gemini-1.5-flash")
            return ChatGemini(api_key=key, model_name=m_name, temperature=0.2)
        return None

    # 3. Groq Cloud API
    if prov in ["groq", "cloud"]:
        raw_key = groq_api_key or getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        key = clean_api_key(raw_key)
        if not key:
            refreshed = reload_settings()
            key = clean_api_key(getattr(refreshed, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY"))
        if key:
            try:
                from langchain_groq import ChatGroq
                m_name = model_name
                if not m_name or "gemini" in m_name.lower() or "/" in m_name:
                    m_name = getattr(settings, "GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
                return ChatGroq(model_name=m_name, api_key=key, temperature=0.2)
            except Exception as e:
                logger.warning(f"Could not initialize ChatGroq: {e}")
                return None
        return None

    # 4. Local Ollama LLM
    if prov in ["ollama", "local_ollama"]:
        b_url = ollama_base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        resolved = resolve_ollama_model(model_name, b_url)
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=resolved, base_url=b_url, temperature=0.2)
        except Exception:
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(model=resolved, base_url=b_url, temperature=0.2)
            except Exception as e:
                logger.warning(f"Could not initialize ChatOllama: {e}")
                return None

    return None


# ==============================================================================
# 6. Multi-Model Fallback Cascade Runner
# ==============================================================================

def get_candidate_cascade_order(
    requested_provider: Optional[str] = None,
    custom_cascade: Optional[str] = None
) -> List[str]:
    """
    Determines the ordered list of LLM providers to try.
    Cascade order default: groq -> gemini -> openrouter
    If a specific provider is chosen, it is tried FIRST, followed by the others.
    """
    raw_cascade = custom_cascade or getattr(settings, "FALLBACK_CASCADE_ORDER", "groq,gemini,openrouter")
    standard_order = [p.strip().lower() for p in raw_cascade.split(",") if p.strip()]

    req = (requested_provider or "groq").lower().strip()
    if req in ["local", "offline", "zero-key"]:
        return []

    if req in ["fallback", "auto", "cascade", "all", "groq"]:
        candidates = []
        for p in standard_order:
            if p not in candidates:
                candidates.append(p)
        return candidates

    # Place requested provider at head of cascade, followed by others
    candidates = [req]
    for p in standard_order:
        if p != req and p not in candidates:
            candidates.append(p)
    return candidates


async def invoke_chat_model_with_fallback(
    messages: List[BaseMessage],
    tools: Optional[Sequence[Any]] = None,
    requested_provider: Optional[str] = None,
    custom_cascade: Optional[str] = None,
    groq_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes an LLM chat invocation with automatic multi-model fallback cascade.
    Default order: groq -> gemini -> openrouter
    If all external LLMs fail or if 'local' is requested, drops to offline deterministic planner.

    Returns a dict with:
        - "response": AIMessage or None
        - "provider_used": str (e.g. "groq", "gemini", "openrouter", "local")
        - "fallback_active": bool
        - "fallback_reason": Optional[str]
        - "cascade_attempted": List[str]
    """
    candidates = get_candidate_cascade_order(requested_provider, custom_cascade)
    if not candidates:
        return {
            "response": None,
            "provider_used": "local",
            "fallback_active": True,
            "fallback_reason": "Zero-key deterministic local planner requested",
            "cascade_attempted": []
        }

    failure_reasons: List[str] = []
    attempted: List[str] = []

    for prov in candidates:
        attempted.append(prov)
        # Only use requested model_name if it matches this provider; otherwise use provider default
        prov_model = model_name if (prov == (requested_provider or "").lower().strip()) else None

        try:
            model = create_chat_model(
                provider=prov,
                model_name=prov_model,
                groq_api_key=groq_api_key,
                gemini_api_key=gemini_api_key,
                openrouter_api_key=openrouter_api_key,
                ollama_base_url=ollama_base_url
            )
        except Exception as e:
            msg = f"{prov} init error: {str(e).splitlines()[0]}"
            failure_reasons.append(msg)
            logger.warning(f"Fallback cascade: {msg}. Trying next provider...")
            continue

        if model is None:
            msg = f"{prov}: credentials missing or unconfigured"
            failure_reasons.append(msg)
            logger.info(f"Fallback cascade: {msg}. Advancing to next provider...")
            continue

        try:
            model_to_call = model.bind_tools(tools) if tools else model
            resp = await model_to_call.ainvoke(messages)
            
            is_fallback = (prov != candidates[0])
            fallback_reason = (
                f"Primary provider '{candidates[0]}' failed ({'; '.join(failure_reasons)}). Fell back to '{prov}'."
                if is_fallback else None
            )

            logger.info(f"LLM call succeeded using provider '{prov}'. Fallback active: {is_fallback}")
            return {
                "response": resp,
                "provider_used": prov,
                "fallback_active": is_fallback,
                "fallback_reason": fallback_reason,
                "cascade_attempted": attempted
            }
        except Exception as e:
            err_msg = str(e).splitlines()[0][:140]
            msg = f"{prov} execution error: {err_msg}"
            failure_reasons.append(msg)
            logger.warning(f"Fallback cascade: {msg}. Advancing to next provider...")
            continue

    total_reason = f"All cascade LLMs failed ({'; '.join(failure_reasons)}). Active fallback: local deterministic planner."
    logger.warning(f"All LLMs in cascade failed: {total_reason}")
    return {
        "response": None,
        "provider_used": "local",
        "fallback_active": True,
        "fallback_reason": total_reason,
        "cascade_attempted": attempted
    }
