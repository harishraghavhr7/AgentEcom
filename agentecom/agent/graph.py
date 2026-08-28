"""
LangGraph Workflow Engine for AgentEcom.
Coordinates reasoning, commerce tool execution, and AI readability auditing.
Supports Ollama, Groq, and zero-key local fallback.
"""

import os
import time
import json
import uuid
import re
from typing import Dict, Any, List, Optional

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage
)
from langgraph.graph import StateGraph, START, END

from agentecom.agent.state import AgentState, ReadabilityMetric
from agentecom.agent.tools_langchain import (
    search_products,
    get_product_details,
    check_inventory_stock,
    create_checkout_session,
    confirm_checkout_order,
    COMMERCE_TOOLS
)
from agentecom.tools.commerce import (
    tool_search_products,
    tool_get_product,
    tool_create_checkout_session,
    tool_confirm_checkout,
    tool_check_inventory,
    tool_get_orders
)
from agentecom.core.cache import cache

SYSTEM_PROMPT = """You are a warm, knowledgeable, proactive, and friendly Autonomous AI Shopping Assistant for AgentEcom.
You have access to fast, idempotent commerce tools:
- `search_products`: Search for products in catalog. Use this to find, browse, or recommend products.
- `get_product_details`: Get full product specs, pricing, attributes (warranty, material, dimensions, battery), and live inventory by SKU.
- `check_inventory_stock`: Check availability and live stock count for a list of SKUs.
- `add_to_cart`: Add products to user cart by SKU and quantity.
- `get_order_history`: Look up past orders, purchase history, order details, order numbers, order dates, and tracking information.
- `create_checkout_session`: Create an isolated short-lived checkout session for items in the cart.
- `confirm_checkout_order`: Confirm and place an order idempotently.

CRITICAL INTENT ROUTING RULES:
1. ORDER HISTORY & TRACKING INTENT:
   - Whenever the user asks about past orders, previous purchases, order status, order placement dates/times, order IDs, or order details (e.g. 'get me informations of my previous order', 'show all my orders', 'what did I buy', 'order status', 'track ORD-XXXX', 'when did I purchase it'):
     -> ALWAYS CALL `get_order_history`.
     -> NEVER confuse order history inquiries with product catalog searches!
2. PRODUCT SEARCH & BROWSE INTENT:
   - When the user asks to browse, find, recommend, or search products:
     -> Call `search_products(query=..., max_price=..., category=...)`.
     -> If the user only provides a price constraint (e.g. 'under $300', 'cheaper options'), set the `query` argument to the previous search topic from Conversational Working Memory.
3. PRODUCT SPECIFICATIONS & DETAILS INTENT:
   - When the user asks for details, specs, warranty, material, or info for a specific SKU or the active product:
     -> Call `get_product_details(sku=...)`.
4. STOCK & INVENTORY INTENT:
   - When the user asks 'how many in stock', 'is it available', or 'units left':
     -> Call `check_inventory_stock(skus=[...])`.
5. ADD TO CART INTENT:
   - When the user says 'add to cart', 'add this product to the cart', 'add it', 'buy this':
     -> Call `add_to_cart(sku=..., quantity=...)`.
6. CHECKOUT & CONFIRMATION:
   - When the user says 'checkout' or 'proceed to checkout': call `create_checkout_session`.
   - When the user confirms ('confirm order', 'confirm purchase', 'place order', 'pay now'): call `confirm_checkout_order`.

Interactive Response Guidelines:
- Speak naturally, warmly, and conversationally.
- When presenting product search results, emphasize product names, SKU codes (e.g. `**SKU-4471**`), and prices in bold.
- Celebrate order placements with order number (`**ORD-XXXX**`) and summary.
"""

def extract_json_tool_calls(content: str) -> List[Dict[str, Any]]:
    """
    Extracts structured tool calls from LLM text responses that output JSON tool blocks.
    Supports <tool_call> tags, ```json markdown blocks, or raw JSON objects.
    """
    if not content:
        return []
    
    tool_calls = []

    # 1. Check for <tool_call>...</tool_call>
    tag_matches = re.findall(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL | re.IGNORECASE)
    for tm in tag_matches:
        try:
            data = json.loads(tm.strip())
            name = data.get("name") or data.get("tool")
            args = data.get("args") or data.get("parameters") or {}
            if name:
                tool_calls.append({"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"})
        except Exception:
            pass

    if tool_calls:
        return tool_calls

    # 2. Check for ```json ... ``` code blocks
    code_matches = re.findall(r'```(?:json)?\s*([\{\[].*?[\}\]])\s*```', content, re.DOTALL | re.IGNORECASE)
    for cm in code_matches:
        try:
            data = json.loads(cm.strip())
            if isinstance(data, dict):
                name = data.get("name") or data.get("tool")
                args = data.get("args") or data.get("parameters") or {}
                if name:
                    tool_calls.append({"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"})
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("tool")
                        args = item.get("args") or item.get("parameters") or {}
                        if name:
                            tool_calls.append({"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"})
        except Exception:
            pass

    if tool_calls:
        return tool_calls

    # 3. Check for standalone JSON dict in text
    json_candidate = re.search(r'\{\s*"(?:tool|name)"\s*:\s*"([^"]+)"\s*,\s*"(?:args|parameters)"\s*:\s*(\{.*?\})\s*\}', content, re.DOTALL)
    if json_candidate:
        try:
            name = json_candidate.group(1)
            args = json.loads(json_candidate.group(2))
            tool_calls.append({"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"})
        except Exception:
            pass

    return tool_calls


def get_llm_model(provider: str = "groq", model_name: Optional[str] = None, groq_api_key: Optional[str] = None, ollama_base_url: Optional[str] = None):
    """
    Factory to return configured LangChain ChatModel or None for local fallback.
    """
    groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
    ollama_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    if provider == "groq" and groq_key:
        try:
            from langchain_groq import ChatGroq
            m_name = model_name or "llama-3.3-70b-versatile"
            return ChatGroq(model_name=m_name, api_key=groq_key, temperature=0.2)
        except Exception:
            pass

    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            m_name = model_name or "llama3.2"
            return ChatOllama(model=m_name, base_url=ollama_url, temperature=0.2)
        except Exception:
            pass

    return None


async def agent_reasoning_node(state: AgentState) -> Dict[str, Any]:
    """
    LLM reasoning node that analyzes user request and decides tool calls or final answer,
    with full short-term conversational working memory including all entity attributes.
    """
    provider = state.get("provider", "groq")
    model_name = state.get("model_name")
    groq_api_key = state.get("groq_api_key")
    ollama_base_url = state.get("ollama_base_url")

    # Short-term memory context extraction
    short_term_memory = dict(state.get("short_term_memory") or {})
    active_prod = short_term_memory.get("active_product")
    active_order = short_term_memory.get("active_order") or state.get("order")
    recent_skus = list(short_term_memory.get("recent_skus", []))
    recent_queries = list(short_term_memory.get("recent_queries", []))
    last_category = short_term_memory.get("last_category")
    retrieved_prods = state.get("retrieved_products", [])

    # If active product is not explicitly set in memory but products were recently retrieved
    if not active_prod and retrieved_prods:
        active_prod = retrieved_prods[0]

    llm = get_llm_model(provider, model_name, groq_api_key, ollama_base_url)

    # Extract latest human message
    last_msg = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage) or (hasattr(m, "content") and not isinstance(m, ToolMessage) and not isinstance(m, AIMessage)):
            last_msg = m.content
            break
    if not last_msg and state["messages"]:
        last_msg = state["messages"][-1].content
    low = last_msg.lower().strip()

    if llm is not None:
        try:
            llm_with_tools = llm.bind_tools(COMMERCE_TOOLS)
            
            # Augment system prompt with live short-term working memory containing full entity attributes
            memory_lines = []

            # 1. Active Order Context & Attributes
            if active_order:
                items_desc = []
                for it in active_order.get("items", []):
                    u_price = it.get("unit_price") or it.get("price") or (it.get("item_total", 0) / it.get("quantity", 1) if it.get("quantity") else 0)
                    items_desc.append(f"{it.get('name', it.get('sku'))} (SKU: {it.get('sku')}, Qty: {it.get('quantity', 1)}, Unit Price: ${u_price:.2f})")
                items_str = "; ".join(items_desc) if items_desc else "None"
                memory_lines.append(
                    f"- ACTIVE / RETRIEVED ORDER ENTITY:\n"
                    f"  * Order Number: {active_order.get('order_number')}\n"
                    f"  * Purchase Date / Placed At: {active_order.get('created_at', 'N/A')}\n"
                    f"  * Order Status: {active_order.get('status')}\n"
                    f"  * Total Amount Paid: ${active_order.get('total_amount', 0):.2f}\n"
                    f"  * Idempotency Key: {active_order.get('idempotency_key', 'N/A')}\n"
                    f"  * Customer Email: {active_order.get('customer_email', 'N/A')}\n"
                    f"  * Purchased Items: {items_str}"
                )

            # 2. Active Product Context & Attributes
            if active_prod:
                attrs_dict = active_prod.get("attributes", {})
                attrs_formatted = ", ".join([f"{k}: {v}" for k, v in attrs_dict.items()]) if attrs_dict else "None specified"
                memory_lines.append(
                    f"- ACTIVE / RETRIEVED PRODUCT ENTITY & ATTRIBUTES:\n"
                    f"  * Product Name: {active_prod.get('name')}\n"
                    f"  * SKU: {active_prod.get('sku')}\n"
                    f"  * Price: ${active_prod.get('price', 0):.2f}\n"
                    f"  * Category: {active_prod.get('category', 'N/A')}\n"
                    f"  * Stock Count / Availability: {active_prod.get('stock_count', 'In stock')}\n"
                    f"  * Description: {active_prod.get('description', '')[:250]}\n"
                    f"  * Specifications & Attributes: {attrs_formatted}"
                )

            # 3. Cart & Checkout Session
            if state.get("cart"):
                cart_items_str = ", ".join([f"{i['sku']} (qty {i['quantity']})" for i in state["cart"]])
                memory_lines.append(f"- Current Cart Items: {cart_items_str}")
            if state.get("checkout_session"):
                cs = state["checkout_session"]
                memory_lines.append(f"- Active Checkout Session: ID `{cs.get('session_id')}`, Total: ${cs.get('total_amount', 0):.2f}, Status: {cs.get('status')}")

            if recent_skus:
                memory_lines.append(f"- Recently referenced SKUs: {', '.join(recent_skus[:5])}")
            if recent_queries:
                memory_lines.append(f"- Recent search topics: {', '.join(recent_queries[-3:])}")

            dynamic_prompt = SYSTEM_PROMPT
            if memory_lines:
                dynamic_prompt += "\n\n[CONVERSATIONAL SHORT-TERM WORKING MEMORY WITH ENTITY ATTRIBUTES]\n" + "\n".join(memory_lines) + "\n*Rule: When the user asks about attributes, dates, status, or details of recently placed/retrieved orders, answer directly from order working memory or call get_order_history without calling search_products.*"

            messages = [SystemMessage(content=dynamic_prompt)] + list(state["messages"])
            response = await llm_with_tools.ainvoke(messages)
            
            # Check native tool calls
            if getattr(response, "tool_calls", None):
                return {"messages": [response]}
            
            # Check extracted JSON tool calls in text content
            extracted_calls = extract_json_tool_calls(getattr(response, "content", ""))
            if extracted_calls:
                return {"messages": [AIMessage(content="", tool_calls=extracted_calls)]}

            # If we just executed a tool, LLM synthesized response is complete
            last_is_tool = isinstance(state["messages"][-1], ToolMessage) or (hasattr(state["messages"][-1], "tool_call_id") and getattr(state["messages"][-1], "tool_call_id", None))
            if last_is_tool:
                tool_content = state["messages"][-1].content
                if response.content and any(w in response.content.lower() for w in ["order", "purchase", "product", "item", "cart", "checkout", "stock", "found", "total", "session", "placed", "confirmed", "price"]):
                    return {"messages": [response]}
                return {"messages": [AIMessage(content=tool_content)]}

            # Detect if user requested an actionable commerce action
            sku_match = re.search(r'\b([A-Z0-9]{3,8}-[A-Z0-9\-]+)\b', last_msg, re.IGNORECASE)
            order_match = re.search(r'\b(ORD-[A-Z0-9\-]+)\b', last_msg, re.IGNORECASE)
            commerce_action_detected = bool(
                re.search(r'\b(find|search|show|browse|details?|specs?|order|orders|purchase|cart|checkout|confirm|stock|stocks|under|below|less\s+than|buy|pay|what\s+are|catalog)\b', low)
                or sku_match or order_match
            )
            # If purely conversational with no commerce action, return the LLM response
            if not commerce_action_detected and response.content:
                return {"messages": [response]}
        except Exception:
            pass

    # If the last message was a tool execution result and LLM is unavailable, return synthesized ToolMessage content
    last_is_tool = isinstance(state["messages"][-1], ToolMessage) or (hasattr(state["messages"][-1], "tool_call_id") and getattr(state["messages"][-1], "tool_call_id", None))
    if last_is_tool:
        return {"messages": [AIMessage(content=state["messages"][-1].content)]}

    # Deterministic Local Tool Planner & Intent Router (Zero-Key / Offline Fallback)
    tool_calls = []

    # Detect explicit SKU matches and Order numbers in the text
    sku_match = re.search(r'\b([A-Z0-9]{3,8}-[A-Z0-9\-]+)\b', last_msg, re.IGNORECASE)
    order_match = re.search(r'\b(ORD-[A-Z0-9\-]+)\b', last_msg, re.IGNORECASE)

    # 1. Order Entity Attribute & Placement Date/Time/Cost Questions (e.g. "when do i purchase it", "when was it ordered", "order date", "how much did i pay")
    is_order_date_q = bool(
        re.search(r'\b(when\s+(?:did|was|do)\s+i\s+(?:buy|purchase|order|place)|when\s+placed|order\s+date|purchase\s+date|date\s+of\s+(?:purchase|order)|time\s+of\s+(?:purchase|order)|order\s+placed\s+on|order\s+time)\b', low)
        or (re.search(r'\b(when\s+did\s+i|when\s+do\s+i|when\s+was)\b', low) and re.search(r'\b(purchase|buy|order|place)\b', low))
    )

    is_order_cost_q = bool(
        re.search(r'\b(how\s+much\s+did\s+i\s+pay|how\s+much\s+was\s+it|what\s+did\s+it\s+cost|total\s+paid|order\s+total|total\s+amount\s+paid|what\s+did\s+i\s+spend)\b', low)
        and not re.search(r'\b(under|below|less\s+than|budget|for\s+under)\b', low)
    )

    is_order_status_q = bool(re.search(r'\b(status\s+of\s+(?:my\s+|the\s+)?order|is\s+(?:my\s+|the\s+)?order\s+confirmed|tracking\s+status)\b', low))
    is_order_id_q = bool(re.search(r'\b(idempotency\s+key|order\s+id|order\s+number|customer\s+email|order\s+reference)\b', low) and not re.search(r'\b(confirm|checkout|pay)\b', low))

    if is_order_date_q or is_order_cost_q or is_order_status_q or is_order_id_q:
        target_ord = active_order
        if not target_ord:
            ord_res = await tool_get_orders(limit=1)
            if ord_res.get("orders"):
                target_ord = ord_res["orders"][0]
                short_term_memory["active_order"] = target_ord

        if target_ord:
            ord_num = target_ord.get("order_number", "N/A")
            created_at = target_ord.get("created_at", "Recently")
            status = target_ord.get("status", "CONFIRMED")
            total = target_ord.get("total_amount", 0)
            items = target_ord.get("items", [])
            items_desc = []
            for it in items:
                u_p = it.get("unit_price") or it.get("price") or (it.get("item_total", 0) / it.get("quantity", 1) if it.get("quantity") else 0)
                items_desc.append(f"**{it.get('name', it.get('sku'))}** (`{it.get('sku')}`) x{it.get('quantity', 1)} — ${u_p:.2f}")
            items_txt = "\n  - " + "\n  - ".join(items_desc) if items_desc else "No items listed"

            if is_order_date_q:
                content = (
                    f"### 📦 Order Placement Date & Time\n"
                    f"You placed Order **`{ord_num}`** on **{created_at}**.\n\n"
                    f"- **Order Status**: 🟢 `{status}`\n"
                    f"- **Total Amount Paid**: **${total:.2f}**\n"
                    f"- **Purchased Item(s)**:{items_txt}\n"
                    f"- **Idempotency Key**: `{target_ord.get('idempotency_key', 'N/A')}`"
                )
            elif is_order_cost_q:
                content = (
                    f"### 💳 Order Payment & Cost Summary\n"
                    f"The total amount paid for Order **`{ord_num}`** was **${total:.2f}**.\n\n"
                    f"- **Date**: *{created_at}*\n"
                    f"- **Status**: 🟢 `{status}`\n"
                    f"- **Purchased Item(s)**:{items_txt}"
                )
            elif is_order_status_q:
                content = (
                    f"### 📦 Order Status\n"
                    f"Order **`{ord_num}`** is currently 🟢 **`{status}`**.\n\n"
                    f"- **Placed On**: *{created_at}*\n"
                    f"- **Total Paid**: **${total:.2f}**\n"
                    f"- **Purchased Item(s)**:{items_txt}"
                )
            else:
                content = (
                    f"### 🔖 Order Details & Identifiers\n"
                    f"- **Order Number**: `{ord_num}`\n"
                    f"- **Placed At**: *{created_at}*\n"
                    f"- **Status**: 🟢 `{status}`\n"
                    f"- **Total Amount**: **${total:.2f}**\n"
                    f"- **Idempotency Key**: `{target_ord.get('idempotency_key', 'N/A')}`\n"
                    f"- **Customer Email**: `{target_ord.get('customer_email', 'N/A')}`"
                )
            return {"messages": [AIMessage(content=content)], "short_term_memory": short_term_memory}
        else:
            return {"messages": [AIMessage(content="You have not placed any orders in this session yet.\n\n💡 *Browse our catalog or search for items to place your first order!*")]}

    # 2. Confirm Order Placement (e.g. "place the order", "confirm purchase", "place order", "finalize checkout", "pay now")
    elif bool(re.search(r'\b(confirm\s+(?:order|purchase|checkout)|place\s+(?:the\s+|my\s+)?order|finalize\s+checkout|pay\s+now|confirm\s+checkout|order\s+now)\b', low)):
        sess_id = state.get("checkout_session", {}).get("session_id") if state.get("checkout_session") else "active_session"
        tool_calls.append({
            "name": "confirm_checkout_order",
            "args": {"session_id": sess_id, "customer_email": "agent-shopper@internal.ai"},
            "id": f"call_{uuid.uuid4().hex[:8]}"
        })

    # 3. General Order History / Previous Orders Inquiry (Flexible semantic matching)
    elif (
        not bool(re.search(r'\b(place|confirm|checkout|pay|finalize)\b', low)) and (
            bool(re.search(r'\b(?:previous|past|last|my|all|recent)\s+orders?\b', low))
            or bool(re.search(r'\b(?:order|purchase)\s*(?:history|details?|info|informations?|status|tracking)\b', low))
            or bool(re.search(r'\b(?:informations?|details?|info|status|track|tracking|history)\s+(?:of|about|for)\s+(?:all\s+|my\s+|the\s+|all\s+my\s+|previous\s+|past\s+|recent\s+)?orders?\b', low))
            or bool(re.search(r'\bwhat\s+(?:did\s+i\s+(?:buy|purchase)|have\s+i\s+bought|orders?\s+placed)\b', low))
            or (order_match and not bool(re.search(r'\b(confirm|checkout|pay)\b', low)))
        )
    ):
        ord_num = order_match.group(1).upper() if order_match else None
        tool_calls.append({
            "name": "get_order_history",
            "args": {"order_number": ord_num, "limit": 5} if ord_num else {"limit": 5},
            "id": f"call_{uuid.uuid4().hex[:8]}"
        })

    # 4. Product Entity Attributes & Specifications Questions (e.g. warranty, material, dimensions, battery, specs)
    elif (
        bool(re.search(r'\b(warranty|material|materials|dimensions?|weights?|specs?|specifications?|batter(?:y|ies)|attributes?|features?|colors?|height\s+range|weight\s+capacity)\b', low))
    ) and (sku_match or active_prod or recent_skus or retrieved_prods):
        target_p = None
        if sku_match:
            sku_c = sku_match.group(1).upper()
            prod_res = await tool_get_product(sku=sku_c)
            if "product" in prod_res:
                target_p = prod_res["product"]
        elif active_prod:
            target_p = active_prod
        elif retrieved_prods:
            target_p = retrieved_prods[0]

        if target_p:
            attrs = target_p.get("attributes", {})
            matched_attr = None
            for k, v in attrs.items():
                if k.lower() in low or any(word in low for word in k.lower().split()):
                    matched_attr = (k, v)
                    break

            lines = [f"### 📋 {target_p['name']} (`{target_p['sku']}`) Specifications\n"]
            if matched_attr:
                lines.append(f"🔍 **{matched_attr[0]}**: **{matched_attr[1]}**\n")
            lines.append(f"- **Price**: **${target_p['price']:.2f}**")
            lines.append(f"- **Category**: {target_p.get('category', 'N/A')}")
            lines.append(f"- **Stock Availability**: {target_p.get('stock_count', 'In stock')} units")
            if attrs:
                lines.append("\n**All Product Attributes & Specs**:")
                for k, v in attrs.items():
                    lines.append(f"- **{k}**: {v}")
            lines.append(f"\n*{target_p.get('description', '')}*")
            return {"messages": [AIMessage(content="\n".join(lines))], "short_term_memory": short_term_memory}
        else:
            ai_msg = AIMessage(content="Which product would you like attributes for? Please specify a product name or SKU.")
            return {"messages": [ai_msg]}

    # 5. Checkout Session Initiation
    elif bool(re.search(r'\b(proceed\s+to\s+checkout|create\s+checkout|checkout|buy\s+now|ready\s+to\s+pay)\b', low)):
        cart_items = [{"sku": i["sku"], "quantity": i["quantity"]} for i in state.get("cart", [])]
        if not cart_items and (sku_match or active_prod):
            target_sku = sku_match.group(1).upper() if sku_match else active_prod["sku"]
            cart_items = [{"sku": target_sku, "quantity": 1}]
        if cart_items:
            tool_calls.append({
                "name": "create_checkout_session",
                "args": {"skus_and_quantities": cart_items, "ttl_minutes": 15},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            })
    # 6. Add to Cart (with explicit SKU OR short-term memory pronoun resolution)
    elif bool(re.search(r'\b(add\s+to\s+(?:my\s+)?cart|put\s+(?:this\s+|it\s+)?in\s+(?:my\s+)?cart|add\s+(?:this\s+product|this|it|item|sku)|buy\s+this|order\s+this|i(?:\'ll|\s+will)\s+take\s+this|add\s+)\b', low)):
        target_sku = None
        if sku_match:
            target_sku = sku_match.group(1).upper()
        elif active_prod and active_prod.get("sku"):
            target_sku = active_prod["sku"]
        elif recent_skus:
            target_sku = recent_skus[0]
        elif retrieved_prods:
            target_sku = retrieved_prods[0].get("sku")

        if target_sku:
            tool_calls.append({
                "name": "add_to_cart",
                "args": {"sku": target_sku, "quantity": 1},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            })
        else:
            ai_msg = AIMessage(
                content="Which product would you like to add to your cart? Please search for a product or provide its SKU (e.g. `SKU-4471`)."
            )
            return {"messages": [ai_msg]}

    # 7. Stock Availability & Inventory Check (with explicit SKU OR short-term memory resolution)
    elif bool(re.search(r'\b(stocks?|available|availability|units?\s+left|how\s+many\s+left|how\s+many\s+available|how\s+many\s+stocks|in\s+stock|out\s+of\s+stock|inventory|how\s+much\s+left)\b', low)) and (sku_match or active_prod or recent_skus or retrieved_prods):
        target_sku = None
        if sku_match:
            target_sku = sku_match.group(1).upper()
        elif active_prod and active_prod.get("sku"):
            target_sku = active_prod["sku"]
        elif recent_skus:
            target_sku = recent_skus[0]
        elif retrieved_prods:
            target_sku = retrieved_prods[0].get("sku")

        if target_sku:
            tool_calls.append({
                "name": "check_inventory_stock",
                "args": {"skus": [target_sku]},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            })
        else:
            tool_calls.append({
                "name": "search_products",
                "args": {"query": last_msg, "limit": 6},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            })

    # 8. Product Details / Inquiry (with explicit SKU OR short-term memory resolution)
    elif (sku_match and len(last_msg.split()) <= 4) or bool(re.search(r'\b(details?\s+(?:for|of)\s+this|tell\s+me\s+more|more\s+info|specs?\s+of\s+this|show\s+details?|how\s+much\s+is\s+this|what\s+is\s+the\s+price|price\s+of\s+this|how\s+much\s+does\s+it\s+cost)\b', low)):
        target_sku = None
        if sku_match:
            target_sku = sku_match.group(1).upper()
        elif active_prod and active_prod.get("sku"):
            target_sku = active_prod["sku"]
        elif recent_skus:
            target_sku = recent_skus[0]
        elif retrieved_prods:
            target_sku = retrieved_prods[0].get("sku")

        if target_sku:
            tool_calls.append({
                "name": "get_product_details",
                "args": {"sku": target_sku},
                "id": f"call_{uuid.uuid4().hex[:8]}"
            })
        else:
            ai_msg = AIMessage(
                content="Which product would you like details for? Please specify a product name or SKU."
            )
            return {"messages": [ai_msg]}

    # 9. Product Search & Contextual Follow-up Refinements
    elif (
        bool(re.search(r'\b(products?|items?|catalog|browse|what\s+do\s+you\s+have|what\s+are|store|sell|find|search|looking\s+for|show\s+me|sweaters?|headphones?|chairs?|desks?|keyboards?|monitors?|kettles?|mouses?|mice|jackets?|shirts?|coffee|shoes?|boots?|bags?|skincare|cameras?)\b', low))
        or bool(re.search(r'(?:under|less\s+than|max|below|cheaper\s+than)\s*\$?\d+', low))
    ):
        max_p = None
        p_match = re.search(r'(?:under|less\s+than|max|below|cheaper\s+than)\s*\$?(\d+(?:\.\d+)?)', low)
        clean_q = last_msg
        if p_match:
            max_p = float(p_match.group(1))
            clean_q = re.sub(r'(?:under|less\s+than|max|below|cheaper\s+than)\s*\$?\d+(?:\.\d+)?', '', clean_q, flags=re.IGNORECASE).strip()

        for prefix in [
            "what are the products there", "what are the products", "what products do you have",
            "show all products", "show products", "list products", "browse catalog",
            "find me", "find", "search for", "search", "show me", "i am looking for",
            "looking for", "can you show", "show"
        ]:
            if clean_q.lower().startswith(prefix):
                clean_q = clean_q[len(prefix):].strip()

        # Follow-up search contextual refinement using short-term memory
        if (not clean_q or clean_q.lower() in ["cheaper", "cheaper ones", "options", "more", "under", ""]) and recent_queries:
            clean_q = recent_queries[-1]
        elif not clean_q:
            clean_q = "products"

        tool_calls.append({
            "name": "search_products",
            "args": {"query": clean_q, "max_price": max_p, "limit": 6},
            "id": f"call_{uuid.uuid4().hex[:8]}"
        })

    if tool_calls:
        ai_msg = AIMessage(content="", tool_calls=tool_calls)
    else:
        ai_msg = AIMessage(
            content=(
                "I am your Autonomous Commerce AI Agent powered by **LangGraph & AgentEcom**.\n\n"
                "I can:\n"
                "- Search catalog (e.g. *'Show all products'*, *'Find a cozy knit sweater under $60'*, or *'Show me noise canceling headphones'*)\n"
                "- Check product specs (e.g. *'Details for SKU-4471'* or *'Details for this'*)\n"
                "- Manage cart & checkout (e.g. *'Add this product to the cart'* -> *'Checkout'* -> *'Confirm purchase'*)\n"
                "- Track and view orders (e.g. *'Get me informations of my previous order'*)\n\n"
                "What product can I find for you?"
            )
        )

    return {"messages": [ai_msg]}


async def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes tool calls generated by the agent and captures structured commerce results
    while updating short-term conversational working memory.
    """
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []

    tool_messages = []
    tool_traces = list(state.get("tool_calls_made", []))
    retrieved_prods = list(state.get("retrieved_products", []))
    cart = list(state.get("cart", []))
    checkout_session = state.get("checkout_session")
    order = state.get("order")

    # Short-term working memory tracker
    short_term_memory = dict(state.get("short_term_memory") or {})
    if "recent_skus" not in short_term_memory:
        short_term_memory["recent_skus"] = []
    if "recent_queries" not in short_term_memory:
        short_term_memory["recent_queries"] = []
    active_prod = short_term_memory.get("active_product")
    recent_skus = list(short_term_memory.get("recent_skus", []))

    for tc in tool_calls:
        tool_name = tc.get("name")
        args = tc.get("args", {})
        call_id = tc.get("id", str(uuid.uuid4()))
        result_str = f"Executed {tool_name}."

        tool_traces.append({"tool": tool_name, "args": args})

        if tool_name == "search_products":
            raw_max = args.get("max_price")
            if isinstance(raw_max, dict):
                raw_max = raw_max.get("value") or raw_max.get("$lte") or raw_max.get("max") or (next(iter(raw_max.values()), None) if raw_max else None)
            try:
                max_p = float(raw_max) if raw_max is not None else None
            except (ValueError, TypeError):
                max_p = None

            q_text = str(args.get("query", "products")).strip()
            # If query has price phrase, extract it if max_p is None and clean q_text
            p_match = re.search(r'(?:under|less\s+than|max|below|cheaper\s+than)\s*\$?(\d+(?:\.\d+)?)', q_text, re.IGNORECASE)
            if p_match:
                if max_p is None:
                    max_p = float(p_match.group(1))
                q_text = re.sub(r'(?:under|less\s+than|max|below|cheaper\s+than)\s*\$?\d+(?:\.\d+)?', '', q_text, flags=re.IGNORECASE).strip()

            # Clean search query prefixes
            for prefix in [
                "find me a", "find me", "find a", "find", "search for a", "search for", "search",
                "show me a", "show me", "show all products", "show products", "show", "what are the products there",
                "what are the products", "what products do you have", "browse catalog", "looking for a", "looking for",
                "i am looking for", "can you show"
            ]:
                if q_text.lower().startswith(prefix):
                    q_text = q_text[len(prefix):].strip()

            last_user_msg = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
            is_pure_refinement = bool(re.match(r'^(?:under|below|less\s+than|cheaper\s+than|max)\s*\$?\d+$', last_user_msg.strip(), re.IGNORECASE)) or last_user_msg.strip().lower() in ["cheaper", "cheaper ones", "options", "more"]

            # If user query is a pure price filter or empty refinement, inherit recent_queries
            if (is_pure_refinement or not q_text or q_text.lower() in ["cheaper", "cheaper ones", "options", "more", "under", ""]) and short_term_memory.get("recent_queries"):
                q_text = short_term_memory["recent_queries"][-1]
            elif not q_text:
                q_text = "products"

            args["query"] = q_text
            args["max_price"] = max_p

            res = await tool_search_products(
                query=q_text,
                max_price=max_p,
                category=args.get("category"),
                limit=args.get("limit", 6)
            )
            prods = res.get("products", [])
            retrieved_prods = prods

            # Parse attributes if stored as string
            for p in prods:
                if "attributes" not in p and "attributes_json" in p:
                    try:
                        p["attributes"] = json.loads(p["attributes_json"]) if isinstance(p["attributes_json"], str) else p["attributes_json"]
                    except Exception:
                        p["attributes"] = {}

            # Update short-term memory with retrieved products & full attributes
            if prods:
                short_term_memory["active_product"] = prods[0]
                short_term_memory["recent_products"] = prods[:8]
                for p in prods[:5]:
                    if p["sku"] not in short_term_memory["recent_skus"]:
                        short_term_memory["recent_skus"].insert(0, p["sku"])
                short_term_memory["recent_skus"] = short_term_memory["recent_skus"][:10]

            q_text = args.get("query", "")
            if q_text and q_text not in short_term_memory["recent_queries"]:
                short_term_memory["recent_queries"].append(q_text)
                short_term_memory["recent_queries"] = short_term_memory["recent_queries"][-5:]
            if args.get("category"):
                short_term_memory["last_category"] = args.get("category")
            elif prods and prods[0].get("category"):
                short_term_memory["last_category"] = prods[0].get("category")

            lines = [f"I found **{len(prods)} product(s)** in the catalog:\n"]
            for p in prods:
                attrs_preview = ", ".join([f"{k}: {v}" for k, v in list((p.get("attributes") or {}).items())[:2]]) if p.get("attributes") else ""
                attrs_line = f"  *Specs: {attrs_preview}*\n" if attrs_preview else ""
                lines.append(f"- **{p['name']}** (`{p['sku']}`) — **${p['price']:.2f}** *(RRF Score: {p.get('_rrf_score', 0):.4f})*\n{attrs_line}  {p.get('description', '')[:100]}...")
            lines.append("\n💡 *To add an item to your cart, click '+ Add to Cart' or reply `Add [SKU] to cart` or `Add this product to the cart`.*")
            result_str = "\n".join(lines)

        elif tool_name == "get_product_details":
            sku = args.get("sku", "")
            res = await tool_get_product(sku=sku)
            if "product" in res:
                p = res["product"]
                retrieved_prods = [p]

                # Update short-term memory active product with full attributes
                short_term_memory["active_product"] = p
                if "recent_products" not in short_term_memory:
                    short_term_memory["recent_products"] = []
                short_term_memory["recent_products"] = [x for x in short_term_memory["recent_products"] if x.get("sku") != p["sku"]]
                short_term_memory["recent_products"].insert(0, p)
                short_term_memory["recent_products"] = short_term_memory["recent_products"][:10]

                if p["sku"] in short_term_memory["recent_skus"]:
                    short_term_memory["recent_skus"].remove(p["sku"])
                short_term_memory["recent_skus"].insert(0, p["sku"])
                short_term_memory["recent_skus"] = short_term_memory["recent_skus"][:10]
                
                action = args.get("action", "")
                last_user_msg = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
                is_cart_intent = (
                    action == "add_to_cart"
                    or any(w in last_user_msg.lower() for w in ["add to cart", "add to my cart", "add this", "add it", "add sku", "add", "buy"])
                ) and not any(w in last_user_msg.lower() for w in ["details", "spec", "tell me about", "what is the price"])

                is_order_date_intent = (
                    any(w in last_user_msg.lower() for w in ["when do i purchase", "when did i purchase", "when was it purchased", "when was it ordered", "when did i buy", "when was this placed", "purchase date", "order date"])
                    or (any(w in last_user_msg.lower() for w in ["when did i", "when do i", "when was"]) and any(w in last_user_msg.lower() for w in ["purchase", "buy", "order", "place"]))
                )

                if is_cart_intent:
                    existing = next((i for i in cart if i["sku"] == sku), None)
                    if existing:
                        existing["quantity"] += 1
                    else:
                        cart.append({"sku": sku, "name": p["name"], "price": p["price"], "quantity": 1})
                    result_str = f"Added **{p['name']}** (`{sku}`) to your cart for **${p['price']:.2f}**. Cart now has {len(cart)} item(s)."
                elif is_order_date_intent:
                    target_ord = short_term_memory.get("active_order") or state.get("order")
                    if not target_ord:
                        ord_res = await tool_get_orders(limit=1)
                        if ord_res.get("orders"):
                            target_ord = ord_res["orders"][0]
                            short_term_memory["active_order"] = target_ord
                    if target_ord:
                        result_str = (
                            f"### 📦 Order Placement Date & Time\n"
                            f"You placed Order **`{target_ord.get('order_number')}`** on **{target_ord.get('created_at', 'Recently')}**.\n\n"
                            f"- **Status**: 🟢 `{target_ord.get('status')}`\n"
                            f"- **Total Paid**: **${target_ord.get('total_amount', 0):.2f}**\n"
                            f"- **Item**: **{p['name']}** (`{sku}`)\n"
                            f"- **Idempotency Key**: `{target_ord.get('idempotency_key', 'N/A')}`"
                        )
                    else:
                        result_str = f"You have not placed an order for **{p['name']}** (`{sku}`) yet."
                else:
                    attrs_dict = p.get("attributes", {})
                    matched_attr = None
                    for k, v in attrs_dict.items():
                        if k.lower() in last_user_msg.lower() or any(word in last_user_msg.lower() for word in k.lower().split()):
                            matched_attr = (k, v)
                            break

                    lines = [f"### {p['name']} (`{p['sku']}`)\n"]
                    if matched_attr:
                        lines.append(f"🔍 **{matched_attr[0]}**: **{matched_attr[1]}**\n")
                    lines.append(f"- **Price**: ${p['price']:.2f}")
                    lines.append(f"- **Stock**: {p['stock_count']} available")
                    if attrs_dict:
                        lines.append(f"- **Attributes**: {', '.join([f'{k}: {v}' for k, v in attrs_dict.items()])}")
                    lines.append(f"- **Description**: {p['description']}")
                    result_str = "\n".join(lines)
            else:
                result_str = f"Product with SKU `{sku}` not found in catalog."
        elif tool_name == "add_to_cart":
            sku = args.get("sku", "")
            qty = args.get("quantity", 1)
            try:
                qty = int(qty)
            except (ValueError, TypeError):
                qty = 1

            if not sku:
                if active_prod and active_prod.get("sku"):
                    sku = active_prod["sku"]
                elif recent_skus:
                    sku = recent_skus[0]

            res = await tool_get_product(sku=sku)
            if "product" in res:
                p = res["product"]
                retrieved_prods = [p]
                short_term_memory["active_product"] = {
                    "sku": p["sku"], "name": p["name"], "price": p["price"], "category": p.get("category")
                }
                if p["sku"] in short_term_memory["recent_skus"]:
                    short_term_memory["recent_skus"].remove(p["sku"])
                short_term_memory["recent_skus"].insert(0, p["sku"])
                short_term_memory["recent_skus"] = short_term_memory["recent_skus"][:10]

                existing = next((i for i in cart if i["sku"] == sku), None)
                if existing:
                    existing["quantity"] += qty
                else:
                    cart.append({"sku": sku, "name": p["name"], "price": p["price"], "quantity": qty})
                result_str = f"Added **{p['name']}** (`{sku}`) to your cart for **${p['price']:.2f}**. Cart now has {len(cart)} item(s)."
            else:
                result_str = f"Product `{sku}` not found."

        elif tool_name == "create_checkout_session":
            raw_items = args.get("skus_and_quantities") or args.get("items")
            items = []
            if isinstance(raw_items, dict):
                if "sku" in raw_items:
                    items.append({"sku": str(raw_items["sku"]), "quantity": int(raw_items.get("quantity", 1))})
                else:
                    for k, v in raw_items.items():
                        items.append({"sku": str(k), "quantity": int(v) if str(v).isdigit() else 1})
            elif isinstance(raw_items, list):
                for it in raw_items:
                    if isinstance(it, dict):
                        if "sku" in it:
                            items.append({"sku": str(it["sku"]), "quantity": int(it.get("quantity", 1))})
                        else:
                            for k, v in it.items():
                                items.append({"sku": str(k), "quantity": int(v) if str(v).isdigit() else 1})
                    elif isinstance(it, str):
                        items.append({"sku": it, "quantity": 1})

            if not items and cart:
                items = [{"sku": i["sku"], "quantity": i["quantity"]} for i in cart]
            elif not items and active_prod and active_prod.get("sku"):
                items = [{"sku": active_prod["sku"], "quantity": 1}]
            elif not items and recent_skus:
                items = [{"sku": recent_skus[0], "quantity": 1}]
            
            idem_key = f"idem_sess_{uuid.uuid4().hex[:8]}"
            res = await tool_create_checkout_session(items=items, idempotency_key=idem_key, ttl_minutes=15)
            if "error" in res:
                result_str = f"Checkout session creation failed: {res['error']}"
            else:
                checkout_session = res
                result_str = (
                    f"### 💳 Checkout Session Created\n"
                    f"- **Session ID**: `{res['session_id']}`\n"
                    f"- **Total Amount**: **${res['total_amount']:.2f}**\n"
                    f"- **Status**: `{res['status']}` (Expires in 15 mins)\n"
                    f"- **Idempotency Key**: `{res['idempotency_key']}`\n\n"
                    f"Reply **'confirm purchase'** or click confirm to place the order."
                )

        elif tool_name == "confirm_checkout_order":
            sess_id = checkout_session.get("session_id") if checkout_session else args.get("session_id")

            # If no active session or placeholder session ID passed by LLM, auto-create session from cart/memory
            if not sess_id or sess_id in ["active_session", "create_checkout_session", "session_id", "None", ""]:
                items = []
                if cart:
                    items = [{"sku": i["sku"], "quantity": i["quantity"]} for i in cart]
                elif active_prod and active_prod.get("sku"):
                    items = [{"sku": active_prod["sku"], "quantity": 1}]
                elif recent_skus:
                    items = [{"sku": recent_skus[0], "quantity": 1}]
                
                if items:
                    idem_sess_key = f"idem_sess_{uuid.uuid4().hex[:8]}"
                    sess_res = await tool_create_checkout_session(items=items, idempotency_key=idem_sess_key, ttl_minutes=15)
                    if "session_id" in sess_res:
                        checkout_session = sess_res
                        sess_id = sess_res["session_id"]
                    else:
                        result_str = f"Unable to create checkout session: {sess_res.get('error', 'unknown error')}"
                        tool_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
                        continue
                else:
                    result_str = "Your shopping cart is empty. Please add items to your cart or search our catalog before placing an order."
                    tool_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
                    continue

            confirm_key = f"idem_order_{uuid.uuid4().hex[:8]}"
            res = await tool_confirm_checkout(session_id=sess_id, idempotency_key=confirm_key)
            if "error" in res:
                # If checkout session was expired or not found, try creating a fresh session from cart
                items = []
                if cart:
                    items = [{"sku": i["sku"], "quantity": i["quantity"]} for i in cart]
                elif active_prod and active_prod.get("sku"):
                    items = [{"sku": active_prod["sku"], "quantity": 1}]
                
                if items and "not found" in res["error"].lower():
                    idem_sess_key = f"idem_sess_{uuid.uuid4().hex[:8]}"
                    sess_res = await tool_create_checkout_session(items=items, idempotency_key=idem_sess_key, ttl_minutes=15)
                    if "session_id" in sess_res:
                        res = await tool_confirm_checkout(session_id=sess_res["session_id"], idempotency_key=confirm_key)

                if "error" in res:
                    result_str = f"Confirmation failed: {res['error']}"
                else:
                    order = res
                    cart = []
                    checkout_session = None
                    items_lines = []
                    for it in res.get("items", []):
                        items_lines.append(f"- **{it.get('name', it.get('sku'))}** (`{it.get('sku')}`) x{it.get('quantity', 1)} — ${it.get('price', 0):.2f}")
                    items_txt = "\n".join(items_lines) if items_lines else ""
                    result_str = (
                        f"### 🎉 Order Placed Successfully!\n"
                        f"- **Order Number**: `{res['order_number']}`\n"
                        f"- **Total Paid**: **${res['total_amount']:.2f}**\n"
                        f"- **Status**: 🟢 `CONFIRMED`\n"
                        f"- **Idempotency Key**: `{res['idempotency_key']}`\n\n"
                        f"**Purchased Items**:\n{items_txt}\n\n"
                        f"Inventory reserved and deducted atomically without duplicate orders."
                    )
            else:
                order = res
                cart = []
                checkout_session = None
                short_term_memory["active_order"] = res
                if "recent_orders" not in short_term_memory:
                    short_term_memory["recent_orders"] = []
                short_term_memory["recent_orders"].insert(0, res)

                items_lines = []
                for it in res.get("items", []):
                    u_p = it.get("unit_price") or it.get("price") or (it.get("item_total", 0) / it.get("quantity", 1) if it.get("quantity") else 0)
                    items_lines.append(f"- **{it.get('name', it.get('sku'))}** (`{it.get('sku')}`) x{it.get('quantity', 1)} — ${u_p:.2f}")
                items_txt = "\n".join(items_lines) if items_lines else ""
                result_str = (
                    f"### 🎉 Order Placed Successfully!\n"
                    f"- **Order Number**: `{res['order_number']}`\n"
                    f"- **Total Paid**: **${res['total_amount']:.2f}**\n"
                    f"- **Status**: 🟢 `CONFIRMED`\n"
                    f"- **Idempotency Key**: `{res['idempotency_key']}`\n\n"
                    f"**Purchased Items**:\n{items_txt}\n\n"
                    f"Inventory reserved and deducted atomically without duplicate orders."
                )
            retrieved_prods = []
        elif tool_name == "check_inventory_stock":
            skus = args.get("skus", [])
            if isinstance(skus, str):
                skus = [skus]
            if not skus:
                if active_prod and active_prod.get("sku"):
                    skus = [active_prod["sku"]]
                elif recent_skus:
                    skus = [recent_skus[0]]

            res = await tool_check_inventory(skus=skus)
            inv_dict = res.get("inventory", {})
            if inv_dict:
                lines = ["### 📦 Live Inventory & Stock Availability\n"]
                for sku_k, info in inv_dict.items():
                    stock_qty = info.get("available_stock", 0)
                    status_badge = f"🟢 **{stock_qty} unit(s) available in stock**" if stock_qty > 0 else "🔴 **Out of stock**"
                    lines.append(f"- **{info.get('name', sku_k)}** (`{sku_k}`): {status_badge} (**${info.get('price', 0):.2f}**)")
                
                lines.append("\n💡 *To add to your cart, click `+ Add to Cart` below or reply `Add this product to the cart`.*")
                result_str = "\n".join(lines)

                # Ensure product card is populated for UI
                if not retrieved_prods and skus:
                    prod_res = await tool_get_product(sku=skus[0])
                    if "product" in prod_res:
                        retrieved_prods = [prod_res["product"]]
            else:
                result_str = f"No stock records found for SKU(s): {', '.join(skus) if skus else 'none specified'}."

        elif tool_name in ["get_order_history", "get_orders"]:
            ord_num = args.get("order_number")
            if ord_num:
                ord_clean = str(ord_num).strip()
                ord_match = re.search(r'\b(ORD-[A-Z0-9\-]+)\b', ord_clean, re.IGNORECASE)
                if ord_match:
                    ord_num = ord_match.group(1).upper()
                elif ord_clean.upper().startswith("ORD-"):
                    ord_num = ord_clean.upper()
                elif ord_clean.lower() in ["", "none", "null", "all", "orders", "my orders", "all orders", "undefined"] or len(ord_clean.split()) > 1:
                    ord_num = None

            lim = args.get("limit", 5)
            try:
                lim = int(lim)
            except (ValueError, TypeError):
                lim = 5

            res = await tool_get_orders(order_number=ord_num, limit=lim)
            orders = res.get("orders", [])

            # Also check short-term memory and session state for active/recent orders
            if not orders and short_term_memory.get("active_order"):
                orders = [short_term_memory["active_order"]]
            elif not orders and short_term_memory.get("recent_orders"):
                orders = list(short_term_memory["recent_orders"])
            elif state.get("order") and not any(o.get("order_number") == state["order"].get("order_number") for o in orders):
                orders.insert(0, state["order"])

            if orders:
                short_term_memory["active_order"] = orders[0]
                short_term_memory["recent_orders"] = orders[:5]
                order = orders[0]

                lines = [f"### 📦 Purchase & Order History ({len(orders)} order(s) found)\n"]
                for o in orders:
                    status_badge = "🟢 `CONFIRMED`" if o.get("status") in ["CONFIRMED", "COMPLETED"] else f"🟡 `{o.get('status')}`"
                    date_str = f" • *{o.get('created_at', '')}*" if o.get("created_at") else ""
                    lines.append(f"#### Order `{o.get('order_number')}` {status_badge}{date_str}")
                    lines.append(f"- **Total Paid**: **${o.get('total_amount', 0):.2f}**")
                    if o.get("idempotency_key"):
                        lines.append(f"- **Idempotency Key**: `{o.get('idempotency_key')}`")

                    items = o.get("items", [])
                    if items:
                        lines.append("- **Purchased Items**:")
                        for item in items:
                            price = item.get("unit_price") or item.get("price") or (item.get("item_total", 0) / item.get("quantity", 1) if item.get("quantity") else 0)
                            lines.append(f"  - **{item.get('name', item.get('sku'))}** (`{item.get('sku')}`) x{item.get('quantity', 1)} — ${price:.2f}")
                    lines.append("")

                result_str = "\n".join(lines).strip()
            else:
                result_str = (
                    "### 📦 Purchase & Order History\n"
                    "No orders found in your purchase history.\n\n"
                    "💡 *Browse our catalog with 'Show all products' or search for items to place your first order!*"
                )
            retrieved_prods = []

        else:
            result_str = f"Executed {tool_name}."

        tool_messages.append(ToolMessage(content=result_str, tool_call_id=call_id))

    provider = state.get("provider", "groq")
    model_name = state.get("model_name")
    groq_api_key = state.get("groq_api_key")
    ollama_base_url = state.get("ollama_base_url")
    llm = get_llm_model(provider, model_name, groq_api_key, ollama_base_url)

    if llm is not None:
        return {
            "messages": tool_messages,
            "tool_calls_made": tool_traces,
            "retrieved_products": retrieved_prods,
            "short_term_memory": short_term_memory,
            "cart": cart,
            "checkout_session": checkout_session,
            "order": order
        }
    else:
        # Local zero-key fallback mode
        final_reply = "\n\n".join([tm.content for tm in tool_messages])
        assistant_final = AIMessage(content=final_reply)

        return {
            "messages": [assistant_final],
            "tool_calls_made": tool_traces,
            "retrieved_products": retrieved_prods,
            "short_term_memory": short_term_memory,
            "cart": cart,
            "checkout_session": checkout_session,
            "order": order
        }


async def readability_auditor_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes token reduction %, execution latency, and generates AI Readability audit.
    """
    elapsed_ms = (time.perf_counter() - state.get("start_time", time.perf_counter())) * 1000
    
    last_msg = state["messages"][-1].content if state.get("messages") else ""
    user_msg = state["messages"][0].content if state.get("messages") else ""

    prods = state.get("retrieved_products", [])
    raw_chars = len(user_msg) + len(last_msg) + sum(len(str(p)) for p in prods) * 3
    est_raw_tokens = max(40, raw_chars // 4)
    compressed_tokens = max(20, (len(user_msg) + len(last_msg) + len(json.dumps(state.get("tool_calls_made", [])))) // 4)
    reduction_pct = round(max(0.0, ((est_raw_tokens - compressed_tokens) / est_raw_tokens) * 100), 1)

    executed_tools = [tc["tool"] for tc in state.get("tool_calls_made", [])]

    readability = {
        "estimated_raw_tokens": est_raw_tokens,
        "compressed_tool_tokens": compressed_tokens,
        "token_reduction_pct": reduction_pct,
        "retrieval_relevance_score": 1.0 if prods else 0.9,
        "execution_latency_ms": round(elapsed_ms, 3),
        "cache_hits": cache.metrics.hits,
        "tools_executed": executed_tools,
        "graph_steps": len(state.get("messages", []))
    }

    return {"readability": readability}


def should_continue(state: AgentState) -> str:
    """Conditional routing edge from agent reasoning node."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "readability"


def route_after_tools(state: AgentState) -> str:
    """If tools returned ToolMessages and an LLM is active, route back to agent for conversational synthesis."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, ToolMessage) or (hasattr(last_msg, "tool_call_id") and getattr(last_msg, "tool_call_id", None)):
        return "agent"
    return "readability"


# Build the LangGraph Workflow
def build_commerce_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_reasoning_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("readability", readability_auditor_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "readability": "readability"
        }
    )
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "agent": "agent",
            "readability": "readability"
        }
    )
    workflow.add_edge("readability", END)

    return workflow.compile()

# Global compiled LangGraph application
commerce_langgraph_app = build_commerce_agent_graph()
