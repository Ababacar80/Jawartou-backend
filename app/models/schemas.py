from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============== USER ==============
class UserRegister(BaseModel):
    firstName: str
    lastName: str
    phone: str
    password: str


class UserLogin(BaseModel):
    phone: str
    password: str


class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    firstName: str
    lastName: str
    phone: str
    role: str
    createdAt: datetime

    class Config:
        populate_by_name = True


# ============== PRODUCT ==============
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    colors: List[str]
    sizes: Optional[List[str]] = []
    images: Optional[List[str]] = []
    stock: Optional[Dict[str, Dict[str, int]]] = None


# ✅ UNIQUE ProductUpdate avec TOUS les champs
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    promoPrice: Optional[float] = None  # ✅ IMPORTANT
    description: Optional[str] = None
    image: Optional[str] = None
    images: Optional[List[str]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    colors: Optional[List[str]] = None
    sizes: Optional[List[str]] = None
    featured: Optional[bool] = None
    onPromotion: Optional[bool] = None  # ✅ IMPORTANT
    stock: Optional[Dict[str, Dict[str, int]]] = None
    active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    price: float
    description: str
    category: str
    colors: List[str]
    sizes: List[str]
    images: List[str]
    stock: Dict[str, Any]
    active: bool
    createdAt: datetime

    class Config:
        populate_by_name = True


# ============== CART ==============
class CartItem(BaseModel):
    productId: str
    quantity: int
    size: str
    color: str
    price: float


class CartAdd(BaseModel):
    productId: str
    quantity: int = 1
    size: str
    color: str


class CartUpdate(BaseModel):
    items: List[CartItem]


class CartResponse(BaseModel):
    id: str = Field(alias="_id")
    userId: str
    items: List[CartItem]
    total: float
    updatedAt: datetime

    class Config:
        populate_by_name = True


# ============== ORDER ==============
class OrderItem(BaseModel):
    productId: str
    name: str
    price: float
    quantity: int
    size: str
    color: str


class ShippingInfo(BaseModel):
    firstName: str
    lastName: str
    address: str
    city: str
    phone: str
    email: Optional[EmailStr] = None
    country: str = "Sénégal"


class PaymentInfo(BaseModel):
    paymentMethod: str  # cash, wave, paypal, pickup
    status: str = "pending"  # pending, paid, failed


class OrderCreate(BaseModel):
    items: List[OrderItem]
    shippingInfo: ShippingInfo
    paymentInfo: PaymentInfo
    shippingMethod: str
    subtotal: float
    shippingCost: float
    total: float


class OrderResponse(BaseModel):
    id: str = Field(alias="_id")
    userId: str
    items: List[OrderItem]
    total: float
    status: str
    shippingInfo: ShippingInfo
    paymentInfo: PaymentInfo
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True


# ============== ENUMS ==============
class PaymentMethod(str, Enum):
    cash = "cash"
    wave = "wave"
    paypal = "paypal"
    pickup = "pickup"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class OrderStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"