from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def connect_to_mongo():
    """Connexion à MongoDB"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    print("✅ Connecté à MongoDB")


async def close_mongo_connection():
    """Déconnexion de MongoDB"""
    if db.client:
        db.client.close()
        print("❌ Déconnecté de MongoDB")


def get_database():
    """Retourner l'instance de la base de données"""
    return db.client[settings.DATABASE_NAME]