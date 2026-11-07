from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from agentecom.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
    connect_args={"timeout": 30} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migrate user_id column for SQLite development database
        for table_name in ["checkout_sessions", "orders", "shipment_trackings"]:
            try:
                res = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in res.fetchall()]
                if "user_id" not in columns:
                    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(128) DEFAULT 'default_shopper'"))
                    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_user_id ON {table_name} (user_id)"))
            except Exception:
                pass
