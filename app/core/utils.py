

def serialize_product(product):
    """Sérialise un produit pour l'API"""
    if not product:
        return None

    doc_copy = product.copy() if isinstance(product, dict) else product

    # Convertir l'ID
    if "_id" in doc_copy:
        doc_copy["id"] = str(doc_copy["_id"])
        del doc_copy["_id"]

    # ✅ Les prix restent TELS QUELS (pas de division)
    # 6990 = 6990 F CFA
    # Pas de division par 100

    # ✅ Calculer le stock total
    total_stock = calculate_total_stock(doc_copy.get("stock", {}))
    doc_copy["stockTotal"] = total_stock
    doc_copy["inStock"] = total_stock > 0

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
