import pytest
import hmac
import hashlib
import base64
import json
from httpx import AsyncClient

from agentecom.integrations.shopify.client import ShopifyClient, verify_shopify_webhook_hmac
from agentecom.integrations.shopify.sync import ShopifyCatalogSync, strip_html
from agentecom.tools.commerce import hybrid_engine, tool_create_checkout_session
from agentecom.config import settings

MOCK_SHOPIFY_PRODUCT = {
    "id": 99887766,
    "title": "Nordic Merino Wool Crewneck",
    "body_html": "<p>Luxurious <strong>100% Merino wool</strong> crewneck sweater designed for sub-zero temperatures.</p>",
    "vendor": "ArcticWear",
    "product_type": "Apparel & Fashion",
    "tags": "winter, wool, premium, thermal",
    "images": [{"src": "https://cdn.shopify.com/s/files/sweater.jpg"}],
    "variants": [
        {
            "id": 11223344,
            "title": "Charcoal / Medium",
            "price": "145.00",
            "sku": "AW-MERINO-M",
            "inventory_quantity": 15,
            "weight": 450,
            "weight_unit": "g"
        },
        {
            "id": 11223345,
            "title": "Charcoal / Large",
            "price": "145.00",
            "sku": "AW-MERINO-L",
            "inventory_quantity": 8,
            "weight": 480,
            "weight_unit": "g"
        }
    ]
}


def test_strip_html_helper():
    raw = "<div><h1>Title</h1><p>Description with <a href='#'>links</a> and   spaces.</p></div>"
    clean = strip_html(raw)
    assert clean == "Title Description with links and spaces."


def test_shopify_webhook_hmac_verification():
    secret = "shpss_test_secret_key_12345"
    payload = b'{"id": 12345, "title": "Test Product"}'

    # Compute valid signature
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    # 1. Valid signature
    assert verify_shopify_webhook_hmac(payload, valid_hmac, secret) is True

    # 2. Tampered body
    tampered_payload = b'{"id": 12345, "title": "Tampered Product"}'
    assert verify_shopify_webhook_hmac(tampered_payload, valid_hmac, secret) is False

    # 3. Invalid signature
    assert verify_shopify_webhook_hmac(payload, "invalid_hmac_string", secret) is False

    # 4. Wrong secret
    assert verify_shopify_webhook_hmac(payload, valid_hmac, "wrong_secret") is False


def test_shopify_cart_permalink_generation():
    client = ShopifyClient(store_domain="my-awesome-brand.myshopify.com")

    # Single item
    items = [{"variant_id": 11223344, "quantity": 2}]
    link = client.generate_cart_permalink(items)
    assert link == "https://my-awesome-brand.myshopify.com/cart/11223344:2"

    # Multiple items
    items_multi = [
        {"variant_id": 11223344, "quantity": 1},
        {"variant_id": 11223345, "quantity": 3}
    ]
    link_multi = client.generate_cart_permalink(items_multi)
    assert link_multi == "https://my-awesome-brand.myshopify.com/cart/11223344:1,11223345:3"


def test_shopify_product_parsing():
    sync_service = ShopifyCatalogSync()
    records = sync_service.parse_shopify_product_to_records(MOCK_SHOPIFY_PRODUCT)

    assert len(records) == 2

    # Check Medium variant
    rec_m = records[0]
    assert rec_m["sku"] == "AW-MERINO-M"
    assert rec_m["name"] == "Nordic Merino Wool Crewneck - Charcoal / Medium"
    assert "100% Merino wool" in rec_m["description"]
    assert rec_m["price"] == 145.00
    assert rec_m["stock"] == 15
    assert rec_m["category"] == "Apparel & Fashion"

    attrs_m = json.loads(rec_m["attributes_json"])
    assert attrs_m["shopify_product_id"] == 99887766
    assert attrs_m["shopify_variant_id"] == 11223344
    assert "thermal" in attrs_m["tags"]

    # Check Large variant
    rec_l = records[1]
    assert rec_l["sku"] == "AW-MERINO-L"
    assert rec_l["stock"] == 8


@pytest.mark.asyncio
async def test_shopify_catalog_sync_and_hybrid_search(test_db_session):
    sync_service = ShopifyCatalogSync()

    # Ingest mock Shopify product
    affected_skus = await sync_service.sync_single_product(MOCK_SHOPIFY_PRODUCT)
    assert "AW-MERINO-M" in affected_skus
    assert "AW-MERINO-L" in affected_skus

    # Verify Hybrid Search finds the newly ingested Shopify product
    search_res = hybrid_engine.search_hybrid("Merino Wool Crewneck sweater", top_k=5)
    matched_skus = [p["sku"] for p in search_res]
    assert "AW-MERINO-M" in matched_skus or "AW-MERINO-L" in matched_skus

    # Verify checkout session creates Shopify cart link
    checkout_res = await tool_create_checkout_session(
        items=[{"sku": "AW-MERINO-M", "quantity": 1}],
        idempotency_key="idem_shopify_test_01"
    )
    assert "checkout_url" in checkout_res
    assert "cart/11223344:1" in checkout_res["checkout_url"]


@pytest.mark.asyncio
async def test_shopify_products_webhook_endpoint(async_client: AsyncClient, test_db_session):
    # Post webhook
    headers = {
        "X-Shopify-Topic": "products/update",
        "X-Shopify-Shop-Domain": "test-store.myshopify.com"
    }
    response = await async_client.post(
        "/webhooks/shopify/products",
        json=MOCK_SHOPIFY_PRODUCT,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["product_id"] == 99887766
    assert "AW-MERINO-M" in data["affected_skus"]


@pytest.mark.asyncio
async def test_widget_script_endpoint(async_client: AsyncClient):
    response = await async_client.get("/widget.js")
    assert response.status_code == 200
    assert "agentecom-bubble-btn" in response.text
    assert "agentecom-window" in response.text
