from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from typing import Optional
from app.core.database import get_database
from app.core.security import get_current_admin
from app.models.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()


@router.get("")
async def get_products(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
):
    """Récupérer tous les produits avec filtrage optionnel"""
    db = get_database()

    query = {"active": True}
    if category:
        query["category"] = category

    cursor = db.products.find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)

    for product in products:
        product["id"] = str(product.pop("_id"))

    return {
        "success": True,
        "count": len(products),
        "data": products
    }


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Récupérer un produit par ID"""
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    product = await db.products.find_one({"_id": ObjectId(product_id)})

    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    product["id"] = str(product.pop("_id"))

    return {
        "success": True,
        "data": product
    }


@router.post("")
async def create_product(
        data: ProductCreate,
        current_admin: dict = Depends(get_current_admin)
):
    """Créer un nouveau produit (Admin uniquement)"""
    db = get_database()

    product_doc = {
        **data.dict(),
        "active": True,
        "createdAt": __import__("datetime").datetime.now(),
        "updatedAt": __import__("datetime").datetime.now()
    }

    result = await db.products.insert_one(product_doc)

    return {
        "success": True,
        "message": "Produit créé avec succès",
        "id": str(result.inserted_id)
    }


@router.put("/{product_id}")
async def update_product(
        product_id: str,
        data: ProductUpdate,
        current_admin: dict = Depends(get_current_admin)
):
    """Mettre à jour un produit (Admin uniquement)"""
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    update_data = data.dict(exclude_unset=True)
    update_data["updatedAt"] = __import__("datetime").datetime.now()

    result = await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    return {
        "success": True,
        "message": "Produit mis à jour"
    }


@router.delete("/{product_id}")
async def delete_product(
        product_id: str,
        current_admin: dict = Depends(get_current_admin)
):
    """Supprimer un produit (Admin uniquement)"""
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="ID invalide")

    result = await db.products.delete_one({"_id": ObjectId(product_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    return {
        "success": True,
        "message": "Produit supprimé"
    }