# app/api/orders.py - UPDATED FOR JAWARTOU
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.core.security import get_current_user
from app.models.schemas import OrderStatus, PaymentStatus
import uuid

router = APIRouter()


# ============================================
# MODELS
# ============================================

class OrderItem(BaseModel):
    productId: str
    name: str
    quantity: int
    image: str | None = None
    price: float
    size: str | None = None
    color: str | None = None


class ShippingInfo(BaseModel):
    firstName: str
    lastName: str
    phone: str
    address: str
    city: str
    email: str
    country: str


class PaymentInfo(BaseModel):
    paymentMethod: str
    status: str


class CreateOrderRequest(BaseModel):
    items: list[OrderItem]
    shippingInfo: ShippingInfo
    paymentInfo: PaymentInfo
    shippingMethod: str
    subtotal: float
    shippingCost: float
    total: float
    notes: str | None = None


# ============================================
# POST - CRÉER UNE COMMANDE (JAWARTOU)
# ============================================

@router.post("")
async def create_order(
        data: CreateOrderRequest,
        current_user: dict = Depends(get_current_user)
):
    """
    Créer une nouvelle commande (Format Jawartou)

    ✅ Accepte les items, shippingInfo, paymentInfo, etc.
    ✅ Génère un numéro de commande unique
    ✅ Sauvegarde en DB
    ✅ Vide le panier
    """
    db = get_database()
    user_id = str(current_user["_id"])

    try:
        # Validation
        if not data.items or len(data.items) == 0:
            raise HTTPException(status_code=400, detail="La commande doit contenir au moins un article")

        # Générer un numéro de commande unique: CMD-XXXXX
        order_number = f"CMD-{uuid.uuid4().hex[:8].upper()}"

        # Préparer les données
        order = {
            "orderNumber": order_number,
            "user": user_id,
            "items": [item.dict() for item in data.items],
            "shippingInfo": data.shippingInfo.dict(),
            "paymentInfo": data.paymentInfo.dict(),
            "shippingMethod": data.shippingMethod,
            "subtotal": data.subtotal,
            "shippingCost": data.shippingCost,
            "total": data.total,
            "notes": data.notes or "",
            "status": "pending",  # ✅ Utilise directement la string
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }

        # Sauvegarder en DB
        result = await db.orders.insert_one(order)
        order["_id"] = result.inserted_id

        print(f"✅ Commande créée: {order_number} | User: {user_id}")

        # Vider le panier
        await db.carts.update_one(
            {"user": user_id},
            {"$set": {"items": [], "lastUpdated": datetime.utcnow()}}
        )

        return {
            "success": True,
            "data": {
                "id": str(order["_id"]),
                "orderNumber": order_number,
                "items": order["items"],
                "shippingInfo": order["shippingInfo"],
                "total": order["total"],
                "subtotal": order["subtotal"],
                "shippingCost": order["shippingCost"],
                "status": order["status"],
                "paymentInfo": order["paymentInfo"],
                "shippingMethod": order["shippingMethod"],
                "createdAt": order["createdAt"].isoformat(),
                "updatedAt": order["updatedAt"].isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur création commande: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET - RÉCUPÉRER TOUTES LES COMMANDES DE L'UTILISATEUR
# ============================================

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

    try:
        # Récupérer les commandes
        cursor = db.orders.find({"user": user_id}).skip(skip).limit(limit).sort("createdAt", -1)
        orders = await cursor.to_list(length=limit)

        # Sérialiser
        serialized_orders = []
        for order in orders:
            serialized_orders.append({
                "id": str(order["_id"]),
                "orderNumber": order.get("orderNumber", ""),
                "userId": order["user"],
                "items": order.get("items", []),
                "shippingInfo": order.get("shippingInfo", {}),
                "total": order.get("total", 0),
                "subtotal": order.get("subtotal", 0),
                "shippingCost": order.get("shippingCost", 0),
                "status": order.get("status", "pending"),
                "paymentInfo": order.get("paymentInfo", {}),
                "shippingMethod": order.get("shippingMethod", "standard"),
                "createdAt": order.get("createdAt", datetime.utcnow()).isoformat(),
                "updatedAt": order.get("updatedAt", datetime.utcnow()).isoformat()
            })

        return {
            "success": True,
            "count": len(serialized_orders),
            "data": serialized_orders
        }
    except Exception as e:
        print(f"❌ Erreur récupération commandes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET - RÉCUPÉRER UNE COMMANDE SPÉCIFIQUE
# ============================================

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

    try:
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
            "data": {
                "id": str(order["_id"]),
                "orderNumber": order.get("orderNumber", ""),
                "userId": order["user"],
                "items": order.get("items", []),
                "shippingInfo": order.get("shippingInfo", {}),
                "total": order.get("total", 0),
                "subtotal": order.get("subtotal", 0),
                "shippingCost": order.get("shippingCost", 0),
                "status": order.get("status", "pending"),
                "paymentInfo": order.get("paymentInfo", {}),
                "shippingMethod": order.get("shippingMethod", "standard"),
                "createdAt": order.get("createdAt", datetime.utcnow()).isoformat(),
                "updatedAt": order.get("updatedAt", datetime.utcnow()).isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur récupération commande: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PATCH - METTRE À JOUR LE STATUT D'UNE COMMANDE (ADMIN)
# ============================================

@router.patch("/{order_id}")
async def update_order_status(
        order_id: str,
        status: str,
        current_user: dict = Depends(get_current_user)
):
    """
    Mettre à jour le statut d'une commande (Admin uniquement)
    """
    db = get_database()

    # Vérifier que c'est un admin
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")

    try:
        # Validation de l'ID et du statut
        try:
            obj_id = ObjectId(order_id)
        except:
            raise HTTPException(status_code=400, detail="ID de commande invalide")

        if status not in ["pending", "processing", "shipped", "delivered", "cancelled"]:
            raise HTTPException(status_code=400, detail="Statut invalide")

        # Mettre à jour
        result = await db.orders.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "status": status,
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Commande non trouvée")

        return {
            "success": True,
            "message": f"Statut mis à jour: {status}"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur mise à jour statut: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))