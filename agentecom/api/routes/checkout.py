from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel, Field
from agentecom.tools.commerce import tool_create_checkout_session, tool_confirm_checkout, CartItemInput

router = APIRouter(prefix="/checkout", tags=["Checkout Sessions & Orders"])

class CreateSessionRequest(BaseModel):
    items: List[CartItemInput]
    ttl_minutes: Optional[int] = 15

class ConfirmSessionRequest(BaseModel):
    session_id: str
    customer_email: Optional[str] = "agent-user@example.com"

@router.post("/session")
async def create_checkout_session(
    payload: CreateSessionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a short-lived isolated checkout session.
    Requires Idempotency-Key header or auto-generates if not provided.
    """
    if not idempotency_key:
        import uuid
        idempotency_key = f"idem_{uuid.uuid4().hex[:16]}"

    items_list = [item.model_dump() for item in payload.items]
    res = await tool_create_checkout_session(
        items=items_list,
        idempotency_key=idempotency_key,
        ttl_minutes=payload.ttl_minutes
    )

    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 400), detail=res["error"])
    return res

@router.post("/confirm")
async def confirm_checkout(
    payload: ConfirmSessionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Confirm an isolated checkout session and promote to permanent Order.
    Protects against duplicate charges and double-fired agent requests.
    """
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required for checkout confirmation.")

    res = await tool_confirm_checkout(
        session_id=payload.session_id,
        idempotency_key=idempotency_key,
        customer_email=payload.customer_email
    )

    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 400), detail=res["error"])
    return res
