"""
Retail Store Owner & Merchant Operations API Router.
Enables store personnel to add products, adjust stock, manage pricing,
and monitor real-time inventory levels.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from agentecom.services.merchant import (
    merchant_service,
    ProductCreateSchema,
    ProductUpdateSchema,
    StockAdjustSchema,
    BulkStockItem
)

router = APIRouter(prefix="/merchant", tags=["Merchant & Retail Store Operations"])


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreateSchema):
    """
    Store owner adds a new product to the catalog with pricing, initial stock,
    and attributes. Automatically synched to SQLite, Cache, and FastMCP.
    """
    try:
        return await merchant_service.add_product(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.get("/products")
async def list_products(
    query: Optional[str] = Query(None, description="Search by title, SKU, or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    stock_status: Optional[str] = Query(None, description="'all', 'in_stock', 'low_stock', 'out_of_stock'"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive products"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """
    List store products with real-time stock levels, category filters, and pagination.
    """
    try:
        return await merchant_service.list_products(
            query=query,
            category=category,
            stock_status=stock_status,
            is_active=is_active,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/products/{sku}")
async def get_product(sku: str):
    """
    Retrieve full merchant product profile and inventory levels by SKU.
    """
    try:
        return await merchant_service.get_product(sku)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.patch("/products/{sku}")
@router.put("/products/{sku}")
async def update_product(sku: str, payload: ProductUpdateSchema):
    """
    Update product title, description, category, price, attributes, or active status.
    """
    try:
        return await merchant_service.update_product(sku, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.post("/products/{sku}/stock")
async def adjust_stock(sku: str, payload: StockAdjustSchema):
    """
    Update or adjust stock count for a SKU.
    - mode='set': Overwrites stock to exact quantity.
    - mode='adjust': Increments or decrements stock count.
    """
    try:
        return await merchant_service.update_stock(
            sku=sku,
            quantity=payload.quantity,
            mode=payload.mode,
            reason=payload.reason
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update stock: {str(e)}")


@router.post("/inventory/bulk-adjust")
async def bulk_adjust_stock(items: List[BulkStockItem]):
    """
    Bulk update stock levels across multiple SKUs in a single call.
    """
    try:
        return await merchant_service.bulk_update_stock(items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk stock update failed: {str(e)}")


@router.delete("/products/{sku}")
async def delete_product(
    sku: str,
    permanent: bool = Query(False, description="If True, permanently deletes from DB. If False, soft deletes (sets is_active=False).")
):
    """
    Archive (soft-delete) or permanently remove a product from the store catalog.
    """
    try:
        return await merchant_service.delete_product(sku=sku, soft_delete=not permanent)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


@router.get("/metrics")
async def get_store_metrics():
    """
    Retrieve store inventory KPIs: total catalog items, stock units, low stock alerts,
    total inventory valuation in USD, and category breakdown.
    """
    try:
        return await merchant_service.get_store_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
