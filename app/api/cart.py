from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from app.core.database import get_database
from app.core.security import get_current_user
from app.models.schemas import CartAdd, CartUpdate

router = APIRouter()


@router.get("")
async def get_cart(current_user: dict = Depends(get_current_user)):
    """Récupérer le panier de l'utilisateur"""
    db = get_database()
    user_id = str(current_user["_id"])

    cart = await db.carts.find_one({"userId": user_id})

    if not cart:
        # Créer un panier vide
        result = await db.carts.insert_one({
            "userId": user_id,
            "items": [],
            "total": 0,
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        })
        cart = await db.carts.find_one({"_id": result.inserted_id})

    cart["id"] = str(cart.pop("_id"))

    return {
        "success": True,
        "data": cart
    }


@router.post("/add")
async def add_to_cart(
        data: CartAdd,
        current_user: dict = Depends(get_current_user)
):
    """Ajouter un produit au panier"""
    db = get_database()
    user_id = str(current_user["_id"])

    # Vérifier que le produit existe
    if not ObjectId.is_valid(data.productId):
        raise HTTPException(status_code=400, detail="ID produit invalide")

    product = await db.products.find_one({"_id": ObjectId(data.productId)})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    # Récupérer ou créer le panier
    cart = await db.carts.find_one({"userId": user_id})
    if not cart:
        cart = {
            "userId": user_id,
            "items": [],
            "total": 0,
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }
        await db.carts.insert_one(cart)

    # Ajouter l'item
    item = {
        "productId": data.productId,
        "name": product["name"],
        "price": product["price"],
        "quantity": data.quantity,
        "size": data.size,
        "color": data.color
    }

    # Vérifier si le produit existe déjà dans le panier
    existing_item = next(
        (i for i in cart["items"]
         if i["productId"] == data.productId
         and i["size"] == data.size
         and i["color"] == data.color),
        None
    )

    if existing_item:
        existing_item["quantity"] += data.quantity
    else:
        cart["items"].append(item)

    # Recalculer le total
    cart["total"] = sum(i["price"] * i["quantity"] for i in cart["items"])
    cart["updatedAt"] = datetime.now()

    await db.carts.update_one(
        {"userId": user_id},
        {"$set": cart}
    )

    return {
        "success": True,
        "message": "Produit ajouté au panier",
        "data": cart
    }


@router.put("")
async def update_cart(
        data: CartUpdate,
        current_user: dict = Depends(get_current_user)
):
    """Mettre à jour le panier"""
    db = get_database()
    user_id = str(current_user["_id"])

    # Recalculer le total
    total = sum(item.price * item.quantity for item in data.items)

    cart_update = {
        "items": [item.dict() for item in data.items],
        "total": total,
        "updatedAt": datetime.now()
    }

    await db.carts.update_one(
        {"userId": user_id},
        {"$set": cart_update},
        upsert=True
    )

    return {
        "success": True,
        "message": "Panier mis à jour"
    }


@router.delete("")
async def clear_cart(current_user: dict = Depends(get_current_user)):
    """Vider le panier"""
    db = get_database()
    user_id = str(current_user["_id"])

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
        "message": "Panier vidé"
    }