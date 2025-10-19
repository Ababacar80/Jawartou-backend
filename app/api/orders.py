from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from typing import Optional
from app.core.database import get_database
from app.core.security import get_current_user, get_current_admin
from app.models.schemas import OrderCreate

router = APIRouter()


@router.post("")
async def create_order(
        data: OrderCreate,
        current_user: dict = Depends(get_current_user)
):
    """Créer une nouvelle commande"""
    db = get_database()
    user_id = str(current_user["_id"])

    # Valider que les items ne sont pas vides
    if not data.items:
        raise HTTPException(status_code=400, detail="La commande doit contenir au moins un article")

    # Vérifier la disponibilité du stock
    for item in data.items:
        if not ObjectId.is_valid(item.productId):
            raise HTTPException(status_code=400, detail=f"ID produit invalide: {item.productId}")

        product = await db.products.find_one({"_id": ObjectId(item.productId)})
        if not product:
            raise HTTPException(status_code=404, detail=f"Produit non trouvé: {item.name}")

    # Créer la commande
    order_doc = {
        "userId": user_id,
        "items": [item.dict() for item in data.items],
        "total": data.total,
        "shippingAddress": data.shippingAddress,
        "status": "pending",
        "paymentStatus": "unpaid",
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }

    result = await db.orders.insert_one(order_doc)
    order_id = str(result.inserted_id)

    # Vider le panier
    await db.carts.update_one(
        {"userId": user_id},
        {"$set": {
            "items": [],
            "total": 0,
            "updatedAt": datetime.now()
        }}
    )

    return {
        "success": True,
        "message": "Commande créée avec succès",
        "data": {
            "id": order_id,
            "userId": user_id,
            "total": data.total,
            "status": "pending",
            "createdAt": datetime.now().isoformat()
        }
    }


@router.get("")
async def get_user_orders(
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        current_user: dict = Depends(get_current_user)
):
    """Récupérer les commandes de l'utilisateur"""
    db = get_database()
    user_id = str(current_user["_id"])

    query = {"userId": user_id}
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    total_count = await db.orders.count_documents(query)

    cursor = db.orders.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    for order in orders:
        order["id"] = str(order.pop("_id"))

    return {
        "success": True,
        "count": len(orders),
        "total": total_count,
        "page": page,
        "totalPages": (total_count + limit - 1) // limit,
        "data": orders
    }


@router.get("/{order_id}")
async def get_order(
        order_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Récupérer les détails d'une commande"""
    db = get_database()
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")

    # Vérifier que c'est la commande de l'utilisateur
    if order["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    order["id"] = str(order.pop("_id"))

    return {
        "success": True,
        "data": order
    }


@router.put("/{order_id}/cancel")
async def cancel_order(
        order_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Annuler une commande"""
    db = get_database()
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    order = await db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")

    if order["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail="Seules les commandes en attente peuvent être annulées")

    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "status": "cancelled",
            "updatedAt": datetime.now()
        }}
    )

    return {
        "success": True,
        "message": "Commande annulée avec succès"
    }


# ============== ADMIN ROUTES ==============

@router.get("/admin/all")
async def get_all_orders(
        status: Optional[str] = None,
        limit: int = 100,
        current_admin: dict = Depends(get_current_admin)
):
    """Récupérer toutes les commandes (Admin uniquement)"""
    db = get_database()

    query = {}
    if status:
        query["status"] = status

    cursor = db.orders.find(query).sort("createdAt", -1).limit(limit)
    orders = await cursor.to_list(length=limit)

    for order in orders:
        order["id"] = str(order.pop("_id"))

    return {
        "success": True,
        "count": len(orders),
        "data": orders
    }


@router.get("/admin/stats")
async def get_order_stats(current_admin: dict = Depends(get_current_admin)):
    """Statistiques sur les commandes (Admin uniquement)"""
    db = get_database()

    total_orders = await db.orders.count_documents({})
    pending = await db.orders.count_documents({"status": "pending"})
    processing = await db.orders.count_documents({"status": "processing"})
    shipped = await db.orders.count_documents({"status": "shipped"})
    delivered = await db.orders.count_documents({"status": "delivered"})
    cancelled = await db.orders.count_documents({"status": "cancelled"})

    total_revenue = await db.orders.aggregate([
        {"$match": {"paymentStatus": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(length=1)

    return {
        "success": True,
        "data": {
            "totalOrders": total_orders,
            "totalRevenue": total_revenue[0]["total"] if total_revenue else 0,
            "byStatus": {
                "pending": pending,
                "processing": processing,
                "shipped": shipped,
                "delivered": delivered,
                "cancelled": cancelled
            }
        }
    }


@router.put("/admin/{order_id}/status")
async def update_order_status(
        order_id: str,
        new_status: str,
        current_admin: dict = Depends(get_current_admin)
):
    """Mettre à jour le statut d'une commande (Admin uniquement)"""
    db = get_database()

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valides: {valid_statuses}")

    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    result = await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "status": new_status,
            "updatedAt": datetime.now()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")

    return {
        "success": True,
        "message": f"Statut mis à jour à {new_status}"
    }