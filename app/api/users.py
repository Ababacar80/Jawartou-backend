"""
app/api/users.py - Endpoints pour gérer les utilisateurs (Admin uniquement)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from app.core.security import get_current_admin
from app.core.database import get_database

router = APIRouter()


def serialize_user(user: dict) -> dict:
    """Convertir un utilisateur MongoDB en JSON"""
    return {
        "_id": str(user.get("_id", "")),
        "firstName": user.get("firstName", ""),
        "lastName": user.get("lastName", ""),
        "phone": user.get("phone", ""),
        "role": user.get("role", "user"),
        "createdAt": user.get("createdAt", "").isoformat() if user.get("createdAt") else "",
        "updatedAt": user.get("updatedAt", "").isoformat() if user.get("updatedAt") else "",
        "active": user.get("active", True)
    }


# ============================================
# GET - RÉCUPÉRER TOUS LES UTILISATEURS
# ============================================

@router.get("")
async def get_all_users(
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=500),
        role: str = Query(None),
        admin=Depends(get_current_admin)
):
    """
    Récupère la liste de tous les utilisateurs (Admin uniquement)

    Paramètres:
    - page: Numéro de page
    - limit: Nombre d'utilisateurs par page
    - role: Filtrer par rôle (admin ou user)
    """
    db = get_database()

    try:
        # Construire le filtre
        query = {}
        if role:
            query["role"] = role

        # Pagination
        skip = (page - 1) * limit

        # Récupérer les utilisateurs
        cursor = db.users.find(query).sort("createdAt", -1).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)

        # Compter le total
        total = await db.users.count_documents(query)

        # Sérialiser
        serialized_users = [serialize_user(user) for user in users]

        return {
            "success": True,
            "data": serialized_users,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }

    except Exception as e:
        print(f"❌ Erreur récupération utilisateurs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET - RÉCUPÉRER UN UTILISATEUR PAR ID
# ============================================

@router.get("/{user_id}")
async def get_user(
        user_id: str,
        admin=Depends(get_current_admin)
):
    """Récupère les détails d'un utilisateur spécifique"""
    db = get_database()

    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="ID utilisateur invalide")

        user = await db.users.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        return {
            "success": True,
            "data": serialize_user(user)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur récupération utilisateur: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PUT - MODIFIER LE RÔLE D'UN UTILISATEUR
# ============================================

@router.put("/{user_id}/role")
async def update_user_role(
        user_id: str,
        new_role: str,
        admin=Depends(get_current_admin)
):
    """
    Change le rôle d'un utilisateur (Admin uniquement)

    Paramètres:
    - new_role: "admin" ou "user"
    """
    db = get_database()

    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="ID utilisateur invalide")

        if new_role not in ["admin", "user"]:
            raise HTTPException(status_code=400, detail="Rôle invalide (admin ou user)")

        # Vérifier que l'utilisateur existe
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Mettre à jour le rôle
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "role": new_role,
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Erreur lors de la mise à jour")

        return {
            "success": True,
            "message": f"Rôle changé en: {new_role}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur mise à jour rôle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DELETE - SUPPRIMER UN UTILISATEUR
# ============================================

@router.delete("/{user_id}")
async def delete_user(
        user_id: str,
        admin=Depends(get_current_admin)
):
    """
    Supprime un utilisateur (Admin uniquement)
    Attention: Suppression définitive!
    """
    db = get_database()

    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="ID utilisateur invalide")

        # Empêcher de se supprimer soi-même
        if str(admin.get("_id")) == user_id:
            raise HTTPException(status_code=403, detail="Impossible de se supprimer soi-même")

        # Supprimer l'utilisateur
        result = await db.users.delete_one({"_id": ObjectId(user_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        return {
            "success": True,
            "message": "Utilisateur supprimé"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur suppression utilisateur: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET - STATISTIQUES UTILISATEURS
# ============================================

@router.get("/stats/summary")
async def get_users_summary(admin=Depends(get_current_admin)):
    """Récupère un résumé des statistiques utilisateurs"""
    db = get_database()

    try:
        total_users = await db.users.count_documents({})
        total_admins = await db.users.count_documents({"role": "admin"})
        total_regular = await db.users.count_documents({"role": "user"})

        return {
            "success": True,
            "data": {
                "totalUsers": total_users,
                "totalAdmins": total_admins,
                "totalRegular": total_regular
            }
        }

    except Exception as e:
        print(f"❌ Erreur stats utilisateurs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))