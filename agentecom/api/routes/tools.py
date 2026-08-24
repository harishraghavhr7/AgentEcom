from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from agentecom.tools.commerce import (
    tool_search_products,
    tool_get_product,
    tool_check_inventory,
    tool_create_checkout_session,
    tool_confirm_checkout,
    SearchProductsInput,
    GetProductInput,
    CheckInventoryInput,
    CreateCheckoutInput,
    ConfirmCheckoutInput
)

router = APIRouter(prefix="/tools", tags=["AI Agent Tools"])

AGENT_TOOL_DEFINITIONS = [
    {
        "name": "search_products",
        "description": "Hybrid semantic and lexical search for products in the catalog. Handles exact SKUs, product names, and natural language descriptions.",
        "parameters": SearchProductsInput.model_json_schema()
    },
    {
        "name": "get_product",
        "description": "Fetch detailed product information, live pricing, attributes, and stock availability by unique SKU.",
        "parameters": GetProductInput.model_json_schema()
    },
    {
        "name": "check_inventory",
        "description": "Bulk check real-time available inventory counts for a list of SKU codes.",
        "parameters": CheckInventoryInput.model_json_schema()
    },
    {
        "name": "create_checkout_session",
        "description": "Create an isolated, short-lived checkout session with an idempotency key before finalizing purchase.",
        "parameters": CreateCheckoutInput.model_json_schema()
    },
    {
        "name": "confirm_checkout",
        "description": "Confirm and finalize an isolated checkout session to convert it into a confirmed Order. Requires idempotency key.",
        "parameters": ConfirmCheckoutInput.model_json_schema()
    }
]

class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary matching the tool's parameter schema")

@router.get("/schema")
async def get_tool_schemas():
    """Returns OpenAI/MCP-compatible function calling schemas for AI agents."""
    return {"tools": AGENT_TOOL_DEFINITIONS}

@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a commerce tool dynamically."""
    name = request.tool_name
    args = request.arguments

    if name == "search_products":
        parsed = SearchProductsInput(**args)
        return await tool_search_products(
            query=parsed.query,
            category=parsed.category,
            min_price=parsed.min_price,
            max_price=parsed.max_price,
            limit=parsed.limit
        )
    elif name == "get_product":
        parsed = GetProductInput(**args)
        return await tool_get_product(sku=parsed.sku)
    elif name == "check_inventory":
        parsed = CheckInventoryInput(**args)
        return await tool_check_inventory(skus=parsed.skus)
    elif name == "create_checkout_session":
        parsed = CreateCheckoutInput(**args)
        items_dict = [item.model_dump() for item in parsed.items]
        return await tool_create_checkout_session(
            items=items_dict,
            idempotency_key=parsed.idempotency_key,
            ttl_minutes=parsed.ttl_minutes
        )
    elif name == "confirm_checkout":
        parsed = ConfirmCheckoutInput(**args)
        return await tool_confirm_checkout(
            session_id=parsed.session_id,
            idempotency_key=parsed.idempotency_key,
            customer_email=parsed.customer_email
        )
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found.")
