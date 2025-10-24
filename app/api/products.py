# app/api/products.py - Version complète avec corrections

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, List
from bson import ObjectId
from bson.errors import InvalidId
from slugify import slugify
from app.core.database import get_database
from app.core.security import get_current_admin
from app.core.utils import serialize_product, calculate_total_stock
from app.models.schemas import ProductCreate, ProductUpdate
from datetime import datetime
from typing import Dict, Any


router = APIRouter()

# ============================================
# GET - RÉCUPÉRER LES PRODUITS
# ============================================

@router.get("")
async def get_products(
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        search: Optional[str] = None,
        featured: Optional[bool] = None,
        promotion: Optional[bool] = None,
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=2000)
):
    """
    Récupère la liste des produits avec filtres

    Paramètres:
    - category: Filtre par catégorie (ex: "parfum", "vetement")
    - subcategory: Filtre par sous-catégorie (ex: "50ml", "M")
    - search: Recherche par nom ou description
    - featured: Produits en vedette (true/false)
    - promotion: Produits en promotion (true/false)
    - page: Numéro de page (défaut: 1)
    - limit: Nombre de résultats par page (défaut: 50, max: 2000)
    """
    db = get_database()
    query = {"active": True}

    # ✅ Ajouter les filtres seulement s'ils sont fournis
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"shortDescription": {"$regex": search, "$options": "i"}}
        ]
    if featured is not None:
        query["featured"] = featured
    if promotion is not None:
        query["onPromotion"] = promotion

    skip = (page - 1) * limit

    print(f"🔍 Query MongoDB: {query}")
    print(f"📄 Pagination: page={page}, limit={limit}, skip={skip}")

    try:
        cursor = db.products.find(query).sort("createdAt", -1).skip(skip).limit(limit)
        products = await cursor.to_list(length=limit)
        total = await db.products.count_documents(query)

        print(f"✅ Trouvé {len(products)} produits (total: {total})")

        # ✅ Sérialiser chaque produit
        serialized_products = [serialize_product(p) for p in products]

        # 🔍 Debug: afficher les 2 premiers
        for p in serialized_products[:2]:
            print(f"   📦 {p['name']}: prix={p['price']}F, stock={p['stockTotal']}, inStock={p['inStock']}")

        return {
            "success": True,
            "data": serialized_products,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Récupère un produit par son ID"""
    db = get_database()

    try:
        # Valider l'ObjectId
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID produit invalide")

        product = await db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID produit invalide")

    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    # ✅ Sérialiser le produit
    serialized_product = serialize_product(product)

    print(f"✅ Produit trouvé: {serialized_product['name']}")
    print(
        f"   Prix: {serialized_product['price']}F | Stock: {serialized_product['stockTotal']} | En stock: {serialized_product['inStock']}")

    return {
        "success": True,
        "data": serialized_product
    }


@router.get("/category/{category}")
async def get_products_by_category(
        category: str,
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=2000)
):
    """Récupère les produits d'une catégorie"""
    db = get_database()

    query = {"active": True, "category": category}
    skip = (page - 1) * limit

    try:
        cursor = db.products.find(query).sort("createdAt", -1).skip(skip).limit(limit)
        products = await cursor.to_list(length=limit)
        total = await db.products.count_documents(query)

        # ✅ Sérialiser chaque produit
        serialized_products = [serialize_product(p) for p in products]

        return {
            "success": True,
            "data": serialized_products,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST - CRÉER UN PRODUIT
# ============================================


@router.post("")
async def create_product(
        data: ProductCreate,
        admin=Depends(get_current_admin)
):
    """Crée un nouveau produit (Admin uniquement)"""
    db = get_database()

    try:
        product_dict = data.dict()

        # 🔍 DEBUG: Voir exactement ce qui arrive
        print(f"🔍 DEBUG CREATE - data.dict(): {product_dict}")
        print(f"🔍 DEBUG - Images dans data: {product_dict.get('images')}")

        product_dict["slug"] = slugify(data.name)
        product_dict["createdAt"] = datetime.now()
        product_dict["updatedAt"] = datetime.now()
        product_dict["active"] = True

        # ... reste du stock code ...

        print(f"📝 Création produit: {product_dict['name']}")
        print(f"   Images à sauvegarder: {product_dict.get('images')}")
        print(f"   product_dict complet: {product_dict}")

        result = await db.products.insert_one(product_dict)

        # Vérifier ce qui a été sauvegardé
        new_product = await db.products.find_one({"_id": result.inserted_id})
        print(f"✅ Produit créé, images en DB: {new_product.get('images')}")

        serialized_product = serialize_product(new_product)

        return {
            "success": True,
            "data": serialized_product,
            "message": "Produit créé avec succès"
        }
    except Exception as e:
        print(f"❌ Erreur création produit: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PUT - METTRE À JOUR UN PRODUIT
# ============================================


@router.put("/{product_id}")
async def update_product(
        product_id: str,
        data: ProductUpdate,
        admin=Depends(get_current_admin)
):
    """Met à jour un produit (Admin uniquement)"""
    db = get_database()

    try:
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID produit invalide")

        existing_product = await db.products.find_one({"_id": ObjectId(product_id)})
        if not existing_product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        # 🔍 DEBUG: Voir ce qui arrive en PUT
        print(f"🔍 DEBUG UPDATE - data.dict(): {data.dict()}")
        print(f"🔍 DEBUG - Images dans data: {data.dict().get('images')}")

        update_data = {k: v for k, v in data.dict().items() if v is not None}

        print(f"🔍 DEBUG - update_data après filtre: {update_data}")
        print(f"🔍 DEBUG - Images après filtre: {update_data.get('images')}")

        update_data["updatedAt"] = datetime.now()

        if "name" in update_data and "slug" not in update_data:
            update_data["slug"] = slugify(update_data["name"])

        print(f"✏️  Mise à jour produit {product_id}")
        print(f"   update_data: {update_data}")

        result = await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )

        # Vérifier ce qui a été sauvegardé
        updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
        print(f"✅ Produit mis à jour, images en DB: {updated_product.get('images')}")

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        serialized_product = serialize_product(updated_product)

        return {
            "success": True,
            "data": serialized_product,
            "message": "Produit mis à jour avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur mise à jour: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# PUT - METTRE À JOUR LE STOCK
# ============================================

@router.put("/{product_id}/stock")
async def update_product_stock(
        product_id: str,
        stock: Dict[str, Any],  # ← Accepte tous les formats
        admin=Depends(get_current_admin)
):
    """
    Met à jour le stock d'un produit (Admin uniquement)

    Exemples:

    Simple (Parfum/Bien-être/Informatique):
    {
        "total": 50
    }

    Couleur + quantité (Accessoires):
    {
        "Noir": {"total": 25},
        "Argent": {"total": 18}
    }

    Couleur + taille + quantité (Vêtements):
    {
        "Noir": {"S": 10, "M": 15, "L": 8},
        "Blanc": {"S": 5, "M": 12, "L": 7}
    }
    """
    db = get_database()

    try:
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID produit invalide")

        # Vérifier que le produit existe
        product = await db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        print(f"📦 Mise à jour stock pour {product['name']}")
        print(f"   Nouveau stock: {stock}")

        # Mettre à jour le stock
        result = await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"stock": stock, "updatedAt": datetime.now()}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        # Récupérer le produit mis à jour
        updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
        serialized_product = serialize_product(updated_product)

        print(f"✅ Stock mis à jour")
        print(f"   Stock total: {serialized_product['stockTotal']} | En stock: {serialized_product['inStock']}")

        return {
            "success": True,
            "data": serialized_product,
            "message": "Stock mis à jour avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur mise à jour stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DELETE - SUPPRIMER UN PRODUIT
# ============================================

@router.delete("/{product_id}")
async def delete_product(
        product_id: str,
        admin=Depends(get_current_admin)
):
    """Supprime un produit (Admin uniquement) - Soft delete"""
    db = get_database()

    try:
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID produit invalide")

        print(f"🗑️  Suppression produit {product_id}")

        result = await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"active": False, "updatedAt": datetime.now()}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        print(f"✅ Produit supprimé (soft delete)")

        return {
            "success": True,
            "message": "Produit supprimé avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur suppression: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS BONUS
# ============================================

@router.get("/featured/list")
async def get_featured_products(limit: int = Query(20, ge=1, le=500)):
    """Récupère les produits en vedette"""
    db = get_database()

    try:
        query = {"active": True, "featured": True}
        cursor = db.products.find(query).sort("createdAt", -1).limit(limit)
        products = await cursor.to_list(length=limit)

        serialized_products = [serialize_product(p) for p in products]

        return {
            "success": True,
            "data": serialized_products,
            "total": len(serialized_products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/promotion/list")
async def get_promotion_products(limit: int = Query(20, ge=1, le=500)):
    """Récupère les produits en promotion"""
    db = get_database()

    try:
        query = {"active": True, "onPromotion": True}
        cursor = db.products.find(query).sort("createdAt", -1).limit(limit)
        products = await cursor.to_list(length=limit)

        serialized_products = [serialize_product(p) for p in products]

        return {
            "success": True,
            "data": serialized_products,
            "total": len(serialized_products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_products(
        query_text: str = Query(..., min_length=1),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=500)
):
    """Recherche en texte complet"""
    db = get_database()

    try:
        skip = (page - 1) * limit

        search_query = {
            "active": True,
            "$or": [
                {"name": {"$regex": query_text, "$options": "i"}},
                {"description": {"$regex": query_text, "$options": "i"}},
                {"shortDescription": {"$regex": query_text, "$options": "i"}},
                {"category": {"$regex": query_text, "$options": "i"}}
            ]
        }

        cursor = db.products.find(search_query).sort("_id", -1).skip(skip).limit(limit)
        products = await cursor.to_list(length=limit)
        total = await db.products.count_documents(search_query)

        serialized_products = [serialize_product(p) for p in products]

        return {
            "success": True,
            "data": serialized_products,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))