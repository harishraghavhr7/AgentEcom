import json
import asyncio
from sqlalchemy import select, delete
from agentecom.db.database import AsyncSessionLocal, init_db
from agentecom.db.models import Product, Inventory, CheckoutSession, Order, ProductEmbedding
from agentecom.core.cache import cache

SAMPLE_PRODUCTS = [
    {
        "sku": "SKU-4471",
        "name": "Cozy Oversized Knit Sweater",
        "description": "Ultra-soft chunky knit oversized sweater crafted from 100% merino wool blend. Perfect for cold winter days, casual layering, and cozy loungewear.",
        "category": "Apparel & Fashion",
        "price": 58.50,
        "stock": 45,
        "attributes": {"color": "Oatmeal Beige", "size": "L", "material": "Merino Wool Blend", "gender": "Unisex"}
    },
    {
        "sku": "SKU-4472",
        "name": "Vintage Corduroy Button-Down Shirt",
        "description": "Retro relaxed-fit corduroy long-sleeve shirt in deep forest green. Breathable cotton construction with chest pocket.",
        "category": "Apparel & Fashion",
        "price": 42.00,
        "stock": 25,
        "attributes": {"color": "Forest Green", "size": "M", "material": "100% Cotton Corduroy"}
    },
    {
        "sku": "PATAG-DWN-882",
        "name": "Alpine Ultralight Down Jacket",
        "description": "800-fill-power water-resistant goose down jacket. Packable into its own pocket, windproof ripstop nylon shell for extreme mountaineering.",
        "category": "Apparel & Fashion",
        "price": 229.00,
        "stock": 18,
        "attributes": {"color": "Matte Black", "size": "L", "rating": 4.9, "waterproof": True}
    },
    {
        "sku": "SONY-WH1000XM5",
        "name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        "description": "Industry-leading active noise canceling over-ear headphones with 2 processors, 8 microphones, 30-hour battery life, and crystal-clear hands-free calling.",
        "category": "Consumer Electronics",
        "price": 348.00,
        "stock": 30,
        "attributes": {"brand": "Sony", "connectivity": "Bluetooth 5.2", "battery_hours": 30, "anc": True}
    },
    {
        "sku": "APPL-AIRPODS-PRO2",
        "name": "Apple AirPods Pro (2nd Generation) USB-C",
        "description": "Wireless in-ear earbuds with up to 2x more Active Noise Cancellation, Adaptive Audio, Transparency mode, and personalized Spatial Audio.",
        "category": "Consumer Electronics",
        "price": 239.00,
        "stock": 50,
        "attributes": {"brand": "Apple", "port": "USB-C", "anc": True, "water_resistant": "IP54"}
    },
    {
        "sku": "LOGI-MX-MST3S",
        "name": "Logitech MX Master 3S Performance Wireless Mouse",
        "description": "Ergonomic wireless mouse with Quiet Clicks, 8000 DPI track-on-glass sensor, MagSpeed electromagnetic scrolling, and multi-device Bluetooth/Logi Bolt support.",
        "category": "Computer Accessories",
        "price": 99.99,
        "stock": 60,
        "attributes": {"brand": "Logitech", "dpi": 8000, "connectivity": "Wireless/Bluetooth"}
    },
    {
        "sku": "KEYCH-Q1-PRO",
        "name": "Keychron Q1 Pro Wireless Custom Mechanical Keyboard",
        "description": "75% layout all-aluminum QMK/VIA wireless mechanical keyboard with hot-swappable Red switches, double-gasket design, and RGB backlighting.",
        "category": "Computer Accessories",
        "price": 199.00,
        "stock": 12,
        "attributes": {"switches": "Gateron Jupiter Red", "layout": "75%", "wireless": True}
    },
    {
        "sku": "DELL-U2723QE",
        "name": "Dell UltraSharp 27 4K USB-C Hub Monitor (U2723QE)",
        "description": "27-inch 4K UHD (3840 x 2160) IPS Black monitor with 2000:1 contrast ratio, 98% DCI-P3 color gamut, 90W USB-C Power Delivery hub, and RJ45 ethernet.",
        "category": "Computer Accessories",
        "price": 579.00,
        "stock": 15,
        "attributes": {"resolution": "4K UHD", "panel": "IPS Black", "size_inches": 27, "power_delivery_w": 90}
    },
    {
        "sku": "HERM-AER-CHAIR",
        "name": "Herman Miller Aeron Ergonomic Mesh Chair",
        "description": "Iconic high-performance ergonomic task chair with breathable Pellicle mesh, PostureFit SL adjustable spinal support, and fully adjustable tilt & arms.",
        "category": "Office & Furniture",
        "price": 1195.00,
        "stock": 8,
        "attributes": {"brand": "Herman Miller", "material": "8Z Pellicle Mesh", "ergonomic": True, "size": "B"}
    },
    {
        "sku": "FLEX-E7-DESK",
        "name": "FlexiSpot E7 Pro Dual-Motor Standing Desk",
        "description": "Heavy-duty motorized height adjustable sit-stand desk with solid bamboo desktop, dual motors, anti-collision system, and 4 memory presets.",
        "category": "Office & Furniture",
        "price": 499.00,
        "stock": 20,
        "attributes": {"motor": "Dual", "desktop": "Solid Bamboo", "weight_capacity_lbs": 355}
    },
    {
        "sku": "CHEMEX-OTT-6C",
        "name": "Chemex Classic Eight-Cup Pour-Over Glass Coffeemaker",
        "description": "Classic hourglass pour-over brewer made of non-porous borosilicate glass with polished wood collar and leather tie. Produces pure, sediment-free coffee.",
        "category": "Kitchen & Home",
        "price": 48.95,
        "stock": 40,
        "attributes": {"material": "Borosilicate Glass", "capacity_cups": 8, "brand": "Chemex"}
    },
    {
        "sku": "FELL-STAG-EKG",
        "name": "Fellow Stagg EKG Electric Gooseneck Kettle",
        "description": "Precision pour-over electric kettle with variable temperature control, LCD screen, 60-minute temperature hold, and sleek matte black minimalist aesthetic.",
        "category": "Kitchen & Home",
        "price": 165.00,
        "stock": 22,
        "attributes": {"color": "Matte Black", "capacity_liters": 0.9, "temp_control": True}
    }
]

async def seed_database(force_reset: bool = False):
    await init_db()
    async with AsyncSessionLocal() as session:
        if force_reset:
            await session.execute(delete(Inventory))
            await session.execute(delete(ProductEmbedding))
            await session.execute(delete(CheckoutSession))
            await session.execute(delete(Order))
            await session.execute(delete(Product))
            await session.commit()
        else:
            result = await session.execute(select(Product))
            existing = result.scalars().all()
            if existing:
                return

        for p_data in SAMPLE_PRODUCTS:
            prod = Product(
                sku=p_data["sku"],
                name=p_data["name"],
                description=p_data["description"],
                category=p_data["category"],
                price=p_data["price"],
                attributes_json=json.dumps(p_data.get("attributes", {}))
            )
            session.add(prod)
            await session.flush()

            inv = Inventory(
                product_id=prod.id,
                stock_count=p_data["stock"],
                reserved_count=0
            )
            session.add(inv)

        await session.commit()
        await cache.clear()

if __name__ == "__main__":
    asyncio.run(seed_database(force_reset=True))
