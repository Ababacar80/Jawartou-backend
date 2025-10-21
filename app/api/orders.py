# app/api/orders.py - Endpoints complets
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.core.security import get_current_user
from app.models.schemas import OrderStatus, PaymentStatus

router = APIRouter()


class CreateOrderRequest(BaseModel):
    shippingAddress: str
    paymentMethod: str = "wave"


class OrderResponse(BaseModel):
    id: str
    userId: str
    items: list
    total: float
    status: str
    paymentStatus: str
    shippingAddress: str
    createdAt: str
    updatedAt: str


@router.post("/create")
async def create_order(
    data: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Créer une commande à partir du panier
    - Récupère le panier de l'utilisateur
    - Crée la commande
    - Vide le panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # 1. Récupérer le panier
    cart = await db.carts.find_one({"user": user_id})

    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Le panier est vide")

    # 2. Calculer le total
    total = sum(item["price"] * item["quantity"] for item in cart["items"])

    # 3. Créer la commande
    order = {
        "user": user_id,
        "items": cart["items"],
        "total": total,
        "status": OrderStatus.PENDING.value,
        "paymentStatus": PaymentStatus.PENDING.value,
        "shippingAddress": data.shippingAddress,
        "paymentMethod": data.paymentMethod,
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }

    result = await db.orders.insert_one(order)
    order["_id"] = result.inserted_id

    # 4. Vider le panier
    await db.carts.update_one(
        {"user": user_id},
        {"$set": {"items": [], "lastUpdated": datetime.now()}}
    )

    return {
        "success": True,
        "message": "Commande créée avec succès",
        "order": {
            "id": str(order["_id"]),
            "userId": user_id,
            "items": order["items"],
            "total": order["total"],
            "status": order["status"],
            "paymentStatus": order["paymentStatus"],
            "shippingAddress": order["shippingAddress"],
            "createdAt": order["createdAt"].isoformat(),
            "updatedAt": order["updatedAt"].isoformat()
        }
    }


@router.get("")
async def get_user_orders(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Récupérer toutes les commandes de l'utilisateur
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # Récupérer les commandes
    cursor = db.orders.find({"user": user_id}).skip(skip).limit(limit).sort("createdAt", -1)
    orders = await cursor.to_list(length=limit)

    # Sérialiser
    serialized_orders = []
    for order in orders:
        serialized_orders.append({
            "id": str(order["_id"]),
            "userId": order["user"],
            "items": order.get("items", []),
            "total": order.get("total", 0),
            "status": order.get("status"),
            "paymentStatus": order.get("paymentStatus"),
            "shippingAddress": order.get("shippingAddress", ""),
            "createdAt": order.get("createdAt", datetime.now()).isoformat(),
            "updatedAt": order.get("updatedAt", datetime.now()).isoformat()
        })

    return {
        "success": True,
        "count": len(serialized_orders),
        "orders": serialized_orders
    }


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Récupérer une commande spécifique
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # Validation de l'ID
    try:
        obj_id = ObjectId(order_id)
    except:
        raise HTTPException(status_code=400, detail="ID de commande invalide")

    # Récupérer la commande
    order = await db.orders.find_one({"_id": obj_id, "user": user_id})

    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")

    return {
        "success": True,
        "order": {
            "id": str(order["_id"]),
            "userId": order["user"],
            "items": order.get("items", []),
            "total": order.get("total", 0),
            "status": order.get("status"),
            "paymentStatus": order.get("paymentStatus"),
            "shippingAddress": order.get("shippingAddress", ""),
            "createdAt": order.get("createdAt").isoformat(),
            "updatedAt": order.get("updatedAt").isoformat()
        }
    }


@router.get("")
async def get_cart(current_user: dict = Depends(get_current_user)):
    """
    Récupérer le panier de l'utilisateur
    """
    db = get_database()
    user_id = str(current_user["_id"])

    cart = await db.carts.find_one({"user": user_id})

    if not cart:
        return {
            "success": True,
            "cart": {
                "items": [],
                "total": 0,
                "lastUpdated": datetime.now().isoformat()
            }
        }

    # Calculer le total
    total = sum(item["price"] * item["quantity"] for item in cart.get("items", []))

    return {
        "success": True,
        "cart": {
            "items": cart.get("items", []),
            "total": total,
            "lastUpdated": cart.get("lastUpdated", datetime.now()).isoformat()
        }
    }


# app/api/cart.py - Mise à jour avec les endpoints corrects
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_database
from app.core.security import get_current_user
from bson import ObjectId

router = APIRouter()


class AddToCartRequest(BaseModel):
    productId: str
    quantity: int = 1


class UpdateCartRequest(BaseModel):
    quantity: int


@router.post("/add")
async def add_to_cart(
    data: AddToCartRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ajouter un produit au panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # Récupérer le produit
    try:
        product_id = ObjectId(data.productId)
    except:
        raise HTTPException(status_code=400, detail="ID produit invalide")

    product = await db.products.find_one({"_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    if product.get("stock", 0) < data.quantity:
        raise HTTPException(status_code=400, detail="Stock insuffisant")

    # Préparer l'item
    cart_item = {
        "productId": str(product["_id"]),
        "name": product["name"],
        "price": product.get("promoPrice", product["price"]),
        "quantity": data.quantity,
        "image": product.get("image", "")
    }

    # Ajouter au panier
    await db.carts.update_one(
        {"user": user_id},
        {
            "$push": {"items": cart_item},
            "$set": {"lastUpdated": datetime.now()}
        },
        upsert=True
    )

    return {"success": True, "message": "Produit ajouté au panier"}


@router.get("")
async def get_cart(current_user: dict = Depends(get_current_user)):
    """
    Récupérer le panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    cart = await db.carts.find_one({"user": user_id})

    if not cart:
        cart = {"items": [], "user": user_id}

    total = sum(item["price"] * item["quantity"] for item in cart.get("items", []))

    return {
        "success": True,
        "cart": {
            "items": cart.get("items", []),
            "total": total,
            "lastUpdated": cart.get("lastUpdated", datetime.now()).isoformat()
        }
    }


@router.put("/update/{item_index}")
async def update_cart_item(
    item_index: int,
    data: UpdateCartRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Mettre à jour la quantité d'un article
    """
    db = get_database()
    user_id = str(current_user["_id"])

    cart = await db.carts.find_one({"user": user_id})

    if not cart or item_index >= len(cart.get("items", [])):
        raise HTTPException(status_code=404, detail="Article non trouvé")

    cart["items"][item_index]["quantity"] = data.quantity
    cart["lastUpdated"] = datetime.now()

    await db.carts.update_one(
        {"user": user_id},
        {"$set": {"items": cart["items"], "lastUpdated": cart["lastUpdated"]}}
    )

    return {"success": True, "message": "Article mis à jour"}


@router.delete("/remove/{item_index}")
async def remove_from_cart(
    item_index: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Retirer un article du panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    cart = await db.carts.find_one({"user": user_id})

    if not cart or item_index >= len(cart.get("items", [])):
        raise HTTPException(status_code=404, detail="Article non trouvé")

    cart["items"].pop(item_index)
    cart["lastUpdated"] = datetime.now()

    await db.carts.update_one(
        {"user": user_id},
        {"$set": {"items": cart["items"], "lastUpdated": cart["lastUpdated"]}}
    )

    return {"success": True, "message": "Article retiré"}


@router.delete("/clear")
async def clear_cart(current_user: dict = Depends(get_current_user)):
    """
    Vider le panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    await db.carts.update_one(
        {"user": user_id},
        {"$set": {"items": [], "lastUpdated": datetime.now()}},
        upsert=True
    )

    return {"success": True, "message": "Panier vidé"}