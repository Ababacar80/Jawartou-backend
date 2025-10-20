from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from app.core.database import get_database
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from datetime import datetime
import re

router = APIRouter()


class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    phone: str
    password: str

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        # Nettoyer le numéro
        cleaned = re.sub(r'[^\d+]', '', v)

        # Accepter: 77XXXXXXXX (9 chiffres) ou +22177XXXXXXXX
        if not re.match(r'^(\+221)?77[0-9]{7}$', cleaned):
            raise ValueError('Numéro invalide (format: 77XXXXXXXX)')
        return cleaned


class LoginRequest(BaseModel):
    phone: str
    password: str

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        cleaned = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^(\+221)?77[0-9]{7}$', cleaned):
            raise ValueError('Numéro invalide (format: 77XXXXXXXX)')
        return cleaned


@router.post("/register")
async def register(data: RegisterRequest):
    """Inscription d'un nouvel utilisateur"""
    try:
        db = get_database()

        # Vérifier si le numéro existe déjà
        if await db.users.find_one({"phone": data.phone}):
            raise HTTPException(status_code=400, detail="Ce numéro est déjà utilisé")

        user_data = {
            "firstName": data.firstName,
            "lastName": data.lastName,
            "phone": data.phone,
            "email": f"{data.phone}@example.com",
            "password": hash_password(data.password),
            "role": "user",
            "country": "Senegal",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }

        # Insertion dans la DB
        result = await db.users.insert_one(user_data)
        token = create_access_token({"id": str(result.inserted_id)})

        return {
            "success": True,
            "token": token,
            "user": {
                "id": str(result.inserted_id),
                "firstName": data.firstName,
                "lastName": data.lastName,
                "phone": data.phone,
                "role": "user"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'inscription: {str(e)}")


@router.post("/login")
async def login(data: LoginRequest):
    """Connexion d'un utilisateur"""
    try:
        db = get_database()

        # Normaliser le numéro pour recherche
        phone_cleaned = re.sub(r'[^\d+]', '', data.phone)

        # Préparer les variantes: +221 ou sans
        if phone_cleaned.startswith("+221"):
            phone_variants = [phone_cleaned, phone_cleaned[4:]]
        else:
            phone_variants = [phone_cleaned, f"+221{phone_cleaned}"]

        # Chercher l'utilisateur
        user = await db.users.find_one({"phone": {"$in": phone_variants}})

        if not user or not verify_password(data.password, user.get("password", "")):
            raise HTTPException(status_code=401, detail="Numéro ou mot de passe incorrect")

        # Créer le token
        token = create_access_token({"id": str(user["_id"])})

        return {
            "success": True,
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "firstName": user["firstName"],
                "lastName": user["lastName"],
                "phone": user["phone"],
                "role": user.get("role", "user")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion: {str(e)}")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
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


@router.get("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """Valider le token"""
    return {"success": True, "valid": True}