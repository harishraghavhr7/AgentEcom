import enum
import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from agentecom.db.database import Base

class SessionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class OrderStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(128), index=True, nullable=False)
    price = Column(Float, nullable=False)
    attributes_json = Column(Text, default="{}")  # JSON string of attributes like size, color, brand
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    embedding = relationship("ProductEmbedding", back_populates="product", uselist=False, cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    stock_count = Column(Integer, default=0, nullable=False)
    reserved_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="inventory")

    @property
    def available_count(self) -> int:
        return max(0, self.stock_count - self.reserved_count)


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding_json = Column(Text, nullable=False)  # Stored JSON array of float embeddings
    model_version = Column(String(64), default="all-MiniLM-L6-v2")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="embedding")


class CheckoutSession(Base):
    """
    Short-lived, isolated checkout sessions for AI agents.
    Segregated from core orders to avoid polluting order tables with retries or abandoned calls.
    """
    __tablename__ = "checkout_sessions"

    id = Column(String(64), primary_key=True, index=True)  # session_...
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    cart_json = Column(Text, nullable=False)  # Items array JSON
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.PENDING, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Order(Base):
    """
    Core permanent order table. Only written when a checkout session is confirmed.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    checkout_session_id = Column(String(64), nullable=False)
    items_json = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.CONFIRMED)
    customer_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReturnStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ShipmentStatus(str, enum.Enum):
    ORDER_PLACED = "ORDER_PLACED"
    PROCESSING = "PROCESSING"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"


class UserProfile(Base):
    """
    Long-term cross-session user persona memory (sizing, brand affinities, allergies, budget).
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    sizing_json = Column(Text, default="{}")  # e.g. {"clothing": "M", "shoe": 10}
    brand_affinities_json = Column(Text, default="[]")  # e.g. ["FlexiSpot", "Fellow"]
    preferences_json = Column(Text, default="{}")  # e.g. {"fit": "oversized", "budget_tier": "mid-range"}
    allergies_json = Column(Text, default="[]")  # e.g. ["latex", "wool"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ReturnRequest(Base):
    """
    Post-purchase Return Merchandise Authorization (RMA) record.
    """
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    rma_number = Column(String(64), unique=True, index=True, nullable=False)
    order_number = Column(String(64), index=True, nullable=False)
    sku = Column(String(64), nullable=False)
    reason = Column(String(255), nullable=False)
    status = Column(SQLEnum(ReturnStatus), default=ReturnStatus.APPROVED, index=True)
    rma_label_url = Column(String(255), nullable=True)
    is_out_of_policy = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ShipmentTracking(Base):
    """
    Simulated live courier tracking and delivery timeline.
    """
    __tablename__ = "shipment_trackings"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(64), unique=True, index=True, nullable=False)
    carrier = Column(String(64), default="FedEx Express")
    tracking_number = Column(String(128), unique=True, index=True, nullable=False)
    status = Column(SQLEnum(ShipmentStatus), default=ShipmentStatus.IN_TRANSIT)
    estimated_delivery = Column(String(128), nullable=True)
    current_location = Column(String(128), default="Regional Distribution Center")
    history_json = Column(Text, default="[]")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
