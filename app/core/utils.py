from datetime import datetime
import json

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse


# ✅ Custom JSON Encoder pour gérer les datetime et ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def api_response(success: bool, data=None, message: str = "", **kwargs):
    """
    Crée une réponse API standardisée avec sérialisation correcte

    Exemple:
    - api_response(True, data=product, message="OK")
    - api_response(True, data=products, total=100, page=1)
    - api_response(False, message="Erreur")
    """
    response = {
        "success": success,
        **({"data": data} if data is not None else {}),
        **({"message": message} if message else {}),
        **kwargs
    }

    # ✅ jsonable_encoder convertit datetime → isoformat, ObjectId → str, etc.
    return JSONResponse(
        content=jsonable_encoder(response),
        status_code=200 if success else 400
    )

def serialize_product(product):
    """
    Sérialise un produit pour l'API
    ✅ Assure que TOUS les champs sont présents (y compris promoPrice)
    """
    if not product:
        return None

    doc_copy = product.copy() if isinstance(product, dict) else product

    # Convertir l'ID MongoDB
    if "_id" in doc_copy:
        doc_copy["id"] = str(doc_copy["_id"])
        del doc_copy["_id"]

    # ✅ Convertir les datetime en ISO strings
    if "createdAt" in doc_copy and isinstance(doc_copy["createdAt"], datetime):
        doc_copy["createdAt"] = doc_copy["createdAt"].isoformat()

    if "updatedAt" in doc_copy and isinstance(doc_copy["updatedAt"], datetime):
        doc_copy["updatedAt"] = doc_copy["updatedAt"].isoformat()

    # ✅ FIX: S'assurer que promoPrice est présent
    if "promoPrice" not in doc_copy:
        doc_copy["promoPrice"] = None

    # ✅ S'assurer que onPromotion existe
    if "onPromotion" not in doc_copy:
        doc_copy["onPromotion"] = False

    # ✅ Calculer le stock total
    total_stock = calculate_total_stock(doc_copy.get("stock", {}))
    doc_copy["stockTotal"] = total_stock
    doc_copy["inStock"] = total_stock > 0

    # 🔍 DEBUG
    print(f"✅ Sérialisation: {doc_copy.get('name')}")
    print(f"   promoPrice: {doc_copy.get('promoPrice')}")
    print(f"   onPromotion: {doc_copy.get('onPromotion')}")
    print(f"   createdAt type: {type(doc_copy.get('createdAt'))}")

    return doc_copy


def calculate_total_stock(stock):
    """
    Calcule le stock total depuis la structure stock

    Exemples:
    - {"50ml": 10} → 10
    - {"Noir": {"S": 5, "M": 10}, "Blanc": {"S": 3}} → 18
    """
    if not stock or not isinstance(stock, dict):
        return 0

    total = 0

    for key, value in stock.items():
        if isinstance(value, int):
            # Cas direct: {"50ml": 10}
            total += value
        elif isinstance(value, dict):
            # Cas imbriqué: {"Noir": {"S": 5, "M": 10}}
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, int):
                    total += sub_value

    return total