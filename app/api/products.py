# app/api/products.py - Version complète avec corrections promoPrice

from datetime import datetime
from typing import Optional, Dict, Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from slugify import slugify

from app.core.database import get_database
from app.core.security import get_current_admin
from app.core.utils import serialize_product
from app.models.schemas import ProductCreate, ProductUpdate

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
            print(f"   📦 {p['name']}: prix={p['price']}F, promo={p.get('promoPrice')}, stock={p['stockTotal']}")

        # ✅ Retourner un dict simple (FastAPI le sérialise automatiquement)
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
        import traceback
        traceback.print_exc()
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
    print(f"   Prix: {serialized_product['price']}F | PromoPrice: {serialized_product.get('promoPrice')} | Stock: {serialized_product['stockTotal']}")

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

        print(f"🔍 DEBUG CREATE - Payload reçu: {product_dict}")

        product_dict["slug"] = slugify(data.name)
        product_dict["createdAt"] = datetime.now()
        product_dict["updatedAt"] = datetime.now()
        product_dict["active"] = True

        # ✅ FIX: Gérer promoPrice correctement
        # Si onPromotion = False, s'assurer que promoPrice = None
        if not product_dict.get("onPromotion", False):
            print("⚠️ Produit créé sans promo → promoPrice = None")
            product_dict["promoPrice"] = None
        else:
            # Si onPromotion = True, vérifier qu'on a un prix promo
            if not product_dict.get("promoPrice"):
                print("⚠️ ATTENTION: Promo activée mais pas de prix promo!")
                product_dict["promoPrice"] = None

        # Initialiser le stock vide si pas fourni
        if "stock" not in product_dict:
            product_dict["stock"] = {}

        print(f"📝 Création produit: {product_dict['name']}")
        print(f"   promoPrice: {product_dict.get('promoPrice')}")
        print(f"   onPromotion: {product_dict.get('onPromotion')}")

        # ✅ Insertion en DB
        result = await db.products.insert_one(product_dict)

        # 🔍 Vérifier ce qui a été créé
        new_product = await db.products.find_one({"_id": result.inserted_id})
        print(f"✅ Produit créé avec succès")
        print(f"   promoPrice en DB: {new_product.get('promoPrice')}")

        serialized_product = serialize_product(new_product)

        return {
            "success": True,
            "data": serialized_product,
            "message": "Produit créé avec succès"
        }

    except Exception as e:
        print(f"❌ Erreur création: {str(e)}")
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

        print(f"🔍 DEBUG UPDATE - Payload reçu: {data.dict()}")

        # Construire update_data - garder SEULEMENT les valeurs non-None
        update_data = {}
        for key, value in data.dict().items():
            if value is not None:
                update_data[key] = value

        print(f"   Avant traitement promo: {update_data}")
        print(f"   promoPrice dans payload: {update_data.get('promoPrice')}")
        print(f"   onPromotion dans payload: {update_data.get('onPromotion')}")

        # ✅ IMPORTANT: Gérer la relation onPromotion ↔ promoPrice
        if "onPromotion" in update_data:
            if update_data["onPromotion"] is True:
                # Si on active la promo, s'assurer qu'il y a un prix promo
                if "promoPrice" not in update_data or update_data["promoPrice"] is None:
                    print("⚠️ Promo activée mais pas de prix promo → garder l'ancien")
                else:
                    print(f"✅ Promo activée avec promoPrice: {update_data['promoPrice']}")
            else:
                # Si on désactive la promo, forcer promoPrice = None
                print("🔥 Promo désactivée → forcer promoPrice à None")
                update_data["promoPrice"] = None
        elif "promoPrice" in update_data:
            # Si on modifie promoPrice SANS modifier onPromotion
            print(f"📝 PromoPrice modifié à {update_data['promoPrice']} sans changer onPromotion")

        update_data["updatedAt"] = datetime.now()

        if "name" in update_data:
            update_data["slug"] = slugify(update_data["name"])

        print(f"✏️  Mise à jour: {list(update_data.keys())}")
        print(f"   promoPrice final: {update_data.get('promoPrice')}")
        print(f"   onPromotion final: {update_data.get('onPromotion')}")

        result = await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produit non trouvé")

        updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
        serialized_product = serialize_product(updated_product)

        print(f"✅ Produit mis à jour")
        print(f"   promoPrice en DB: {updated_product.get('promoPrice')}")
        print(f"   onPromotion en DB: {updated_product.get('onPromotion')}")
        print(f"   promoPrice sérialisé: {serialized_product.get('promoPrice')}")

        response_data = {
            "success": True,
            "data": serialized_product,
            "message": "Produit mis à jour avec succès"
        }

        # ✅ Utiliser jsonable_encoder pour convertir datetime → string
        return JSONResponse(
            content=jsonable_encoder(response_data),
            status_code=200
        )

    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PUT - METTRE À JOUR LE STOCK
# ============================================

@router.put("/{product_id}/stock")
async def update_product_stock(
        product_id: str,
        stock: Dict[str, Any],
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