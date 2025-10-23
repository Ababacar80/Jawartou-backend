"""
app/api/dashboard.py - Endpoint pour le dashboard admin
"""

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.security import get_current_admin
from app.core.database import get_database

router = APIRouter()


@router.get("")
async def get_dashboard(current_user: dict = Depends(get_current_admin)):
    """
    Récupère les statistiques du dashboard admin
    Requiert les droits d'administrateur
    """
    db = get_database()

    try:
        # Compter les produits actifs
        total_products = await db.products.count_documents({"active": True})

        # Compter les utilisateurs
        total_users = await db.users.count_documents({})

        # Compter les commandes
        total_orders = await db.orders.count_documents({})

        # Calculer le revenu total (somme des montants de toutes les commandes)
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$totalAmount"}
                }
            }
        ]

        revenue_result = await db.orders.aggregate(pipeline).to_list(1)
        total_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0

        return {
            "success": True,
            "data": {
                "totalProducts": total_products,
                "totalUsers": total_users,
                "totalOrders": total_orders,
                "totalRevenue": total_revenue
            }
        }

    except Exception as e:
        print(f"❌ Erreur dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/products")
async def get_products_stats(current_user: dict = Depends(get_current_admin)):
    """Récupère les statistiques des produits"""
    db = get_database()

    try:
        # Produits par catégorie
        pipeline = [
            {"$match": {"active": True}},
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"}
                }
            }
        ]

        categories = await db.products.aggregate(pipeline).to_list(None)

        # Stock total et produits en rupture
        total_stock = await db.products.aggregate([
            {"$match": {"active": True}},
            {"$group": {"_id": None, "total": {"$sum": "$stockTotal"}}}
        ]).to_list(1)

        out_of_stock = await db.products.count_documents({
            "active": True,
            "stockTotal": 0
        })

        return {
            "success": True,
            "data": {
                "byCategory": categories,
                "totalStock": total_stock[0]["total"] if total_stock else 0,
                "outOfStock": out_of_stock
            }
        }

    except Exception as e:
        print(f"❌ Erreur stats produits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/orders")
async def get_orders_stats(current_user: dict = Depends(get_current_admin)):
    """Récupère les statistiques des commandes"""
    db = get_database()

    try:
        # Commandes par statut
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_amount": {"$sum": "$totalAmount"}
                }
            }
        ]

        by_status = await db.orders.aggregate(pipeline).to_list(None)

        # Commandes ce mois-ci
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        current_month_orders = await db.orders.count_documents({
            "createdAt": {"$gte": start_of_month}
        })

        current_month_revenue = await db.orders.aggregate([
            {"$match": {"createdAt": {"$gte": start_of_month}}},
            {"$group": {"_id": None, "total": {"$sum": "$totalAmount"}}}
        ]).to_list(1)

        return {
            "success": True,
            "data": {
                "byStatus": by_status,
                "currentMonthOrders": current_month_orders,
                "currentMonthRevenue": current_month_revenue[0]["total"] if current_month_revenue else 0
            }
        }

    except Exception as e:
        print(f"❌ Erreur stats commandes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/users")
async def get_users_stats(current_user: dict = Depends(get_current_admin)):
    """Récupère les statistiques des utilisateurs"""
    db = get_database()

    try:
        # Utilisateurs par rôle
        pipeline = [
            {
                "$group": {
                    "_id": "$role",
                    "count": {"$sum": 1}
                }
            }
        ]

        by_role = await db.users.aggregate(pipeline).to_list(None)

        # Utilisateurs cette semaine
        week_ago = datetime.utcnow() - timedelta(days=7)

        new_users_week = await db.users.count_documents({
            "createdAt": {"$gte": week_ago}
        })

        # Commandes par utilisateur (top 5)
        top_customers = await db.orders.aggregate([
            {
                "$group": {
                    "_id": "$userId",
                    "orders": {"$sum": 1},
                    "total_spent": {"$sum": "$totalAmount"}
                }
            },
            {"$sort": {"total_spent": -1}},
            {"$limit": 5}
        ]).to_list(5)

        return {
            "success": True,
            "data": {
                "byRole": by_role,
                "newUsersThisWeek": new_users_week,
                "topCustomers": top_customers
            }
        }

    except Exception as e:
        print(f"❌ Erreur stats utilisateurs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))