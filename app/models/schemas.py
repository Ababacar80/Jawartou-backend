from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


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


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
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


class OrderCreate(BaseModel):
    items: List[OrderItem]
    total: float
    shippingAddress: Dict[str, str]


class OrderResponse(BaseModel):
    id: str = Field(alias="_id")
    userId: str
    items: List[OrderItem]
    total: float
    status: str
    shippingAddress: Dict[str, str]
    createdAt: datetime

    class Config:
        populate_by_name = True