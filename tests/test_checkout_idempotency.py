import pytest
import uuid
import datetime
from sqlalchemy import select
from agentecom.core.checkout import checkout_manager, CheckoutError
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import CheckoutSession, SessionStatus, Order, Inventory, Product

@pytest.mark.asyncio
async def test_create_checkout_session_isolation(test_db_session):
    idempotency_key = f"idem_{uuid.uuid4().hex}"
    items = [{"sku": "SKU-4471", "quantity": 2}]
    
    # 1. Create session
    async with AsyncSessionLocal() as session_db:
        session, is_new = await checkout_manager.create_checkout_session(
            db=session_db,
            items=items,
            idempotency_key=idempotency_key,
            ttl_minutes=10
        )
        assert is_new is True
        assert session.status == SessionStatus.PENDING
        assert session.total_amount == 117.00  # 58.50 * 2

        # Verify orders table has NOT been touched (isolated session)
        orders = (await session_db.execute(select(Order))).scalars().all()
        assert len(orders) == 0

    # 2. Re-send exact same creation request (agent retry simulation)
    async with AsyncSessionLocal() as session_db2:
        session2, is_new2 = await checkout_manager.create_checkout_session(
            db=session_db2,
            items=items,
            idempotency_key=idempotency_key
        )
        assert is_new2 is False
        assert session2.id == session.id

@pytest.mark.asyncio
async def test_confirm_checkout_idempotency(test_db_session):
    idempotency_key_session = f"idem_sess_{uuid.uuid4().hex}"
    idempotency_key_confirm = f"idem_conf_{uuid.uuid4().hex}"
    
    # Check initial stock
    async with AsyncSessionLocal() as session_db:
        p_stmt = select(Product).where(Product.sku == "SKU-4471")
        p = (await session_db.execute(p_stmt)).scalar_one()
        
        inv_stmt = select(Inventory).where(Inventory.product_id == p.id)
        inv_before = (await session_db.execute(inv_stmt)).scalar_one().stock_count

        # 1. Create session for 2 units
        session, _ = await checkout_manager.create_checkout_session(
            db=session_db,
            items=[{"sku": "SKU-4471", "quantity": 2}],
            idempotency_key=idempotency_key_session
        )

        # 2. Confirm checkout session -> becomes Order
        order1, is_new_ord1 = await checkout_manager.confirm_checkout(
            db=session_db,
            session_id=session.id,
            idempotency_key=idempotency_key_confirm
        )
        assert is_new_ord1 is True
        assert order1.idempotency_key == idempotency_key_confirm
        assert order1.total_amount == 117.00

        # Verify stock decremented by 2
        inv_after1 = (await session_db.execute(inv_stmt)).scalar_one().stock_count
        assert inv_after1 == inv_before - 2

        # 3. Agent duplicate / retry fire on confirm checkout
        order2, is_new_ord2 = await checkout_manager.confirm_checkout(
            db=session_db,
            session_id=session.id,
            idempotency_key=idempotency_key_confirm
        )
        assert is_new_ord2 is False
        assert order2.order_number == order1.order_number

        # Verify stock was NOT decremented again!
        inv_after2 = (await session_db.execute(inv_stmt)).scalar_one().stock_count
        assert inv_after2 == inv_before - 2

@pytest.mark.asyncio
async def test_expired_session_cannot_be_confirmed(test_db_session):
    idempotency_key = f"idem_{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as session_db:
        session, _ = await checkout_manager.create_checkout_session(
            db=session_db,
            items=[{"sku": "SKU-4471", "quantity": 1}],
            idempotency_key=idempotency_key
        )
        
        # Manually backdate expiration to simulate time passing
        session.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        await session_db.commit()

        with pytest.raises(CheckoutError) as exc_info:
            await checkout_manager.confirm_checkout(
                db=session_db,
                session_id=session.id,
                idempotency_key=f"conf_{uuid.uuid4().hex}"
            )
        assert exc_info.value.status_code == 410
