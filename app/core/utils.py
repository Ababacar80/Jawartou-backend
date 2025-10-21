# app/core/utils.py
from bson import ObjectId
from datetime import datetime
from typing import Any


def serialize_doc(doc: Any) -> Any:
    """
    Convertit récursivement tous les ObjectId et datetime en strings/ISO
    Cela permet de sérialiser les documents MongoDB en JSON valide
    """
    if isinstance(doc, dict):
        return {key: serialize_doc(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc