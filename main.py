from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import auth, products, cart, orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management: connexion/déconnexion DB"""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="E-Commerce API",
    description="Backend API avec FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# Routes avec /api prefix
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])


@app.get("/")
async def root():
    return {
        "message": "E-Commerce API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ✅ ROUTE DIRECTE - Retourne les catégories organisées
@app.get("/api/categories")
async def get_categories():
    """Retourne les catégories et sous-catégories"""
    from app.core.database import get_database

    db = get_database()

    # Agrégation pour obtenir les catégories distinctes
    pipeline = [
        {"$match": {"active": True}},
        {"$group": {
            "_id": {
                "category": "$category",
                "subcategory": "$subcategory"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.category": 1, "_id.subcategory": 1}}
    ]

    results = await db.products.aggregate(pipeline).to_list(length=None)

    # Organiser par catégorie
    categories_map = {}
    for item in results:
        category = item["_id"]["category"]
        subcategory = item["_id"]["subcategory"]

        if category not in categories_map:
            categories_map[category] = {
                "name": category,
                "subcategories": []
            }

        if subcategory:
            categories_map[category]["subcategories"].append({
                "name": subcategory,
                "productCount": item["count"]
            })

    return {
        "success": True,
        "categories": list(categories_map.values())
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )