from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from passlib.context import CryptContext
from datetime import timedelta
from app.core.database import get_database
from app.core.security import create_access_token, get_current_user
from app.models.schemas import UserRegister, UserLogin, UserResponse

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hasher un mot de passe"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/register")
async def register(data: UserRegister):
    """Inscription d'un nouvel utilisateur"""
    db = get_database()

    # Vérifier si l'utilisateur existe déjà
    existing_user = await db.users.find_one({"phone": data.phone})
    if existing_user:
        raise HTTPException(status_code=400, detail="Cet utilisateur existe déjà")

    # Créer l'utilisateur
    user_doc = {
        "firstName": data.firstName,
        "lastName": data.lastName,
        "phone": data.phone,
        "password": hash_password(data.password),
        "role": "user",
        "createdAt": __import__("datetime").datetime.now(),
        "updatedAt": __import__("datetime").datetime.now()
    }

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Créer le token
    token = create_access_token(user_id)

    return {
        "success": True,
        "message": "Utilisateur créé avec succès",
        "user": {
            "id": user_id,
            "firstName": data.firstName,
            "lastName": data.lastName,
            "phone": data.phone,
            "role": "user"
        },
        "token": token
    }


@router.post("/login")
async def login(data: UserLogin):
    """Connexion d'un utilisateur"""
    db = get_database()

    # Chercher l'utilisateur
    user = await db.users.find_one({"phone": data.phone})
    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    # Créer le token
    user_id = str(user["_id"])
    token = create_access_token(user_id)

    return {
        "success": True,
        "message": "Connexion réussie",
        "user": {
            "id": user_id,
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "phone": user["phone"],
            "role": user.get("role", "user")
        },
        "token": token
    }


@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Récupérer le profil de l'utilisateur connecté"""
    return {
        "success": True,
        "data": {
            "id": str(current_user["_id"]),
            "firstName": current_user["firstName"],
            "lastName": current_user["lastName"],
            "phone": current_user["phone"],
            "role": current_user.get("role", "user")
        }
    }