"""Mock product catalogue — stands in for Channel3 product data until
a Channel3 key is actually wired. Clearly MOCK, do not present as live data.
"""
PRODUCTS = [
    {"id": "p1", "name": "Wireless Earbuds Pro", "price_usd": 49.99, "merchant": "AudioHub (established)", "is_new_merchant": False, "prior_orders": 12},
    {"id": "p2", "name": "Wireless Earbuds Ultra", "price_usd": 299.00, "merchant": "BrandNewStore99 (NEW)", "is_new_merchant": True, "prior_orders": 0},
    {"id": "p3", "name": "Wireless Earbuds Lite", "price_usd": 29.99, "merchant": "AudioHub (established)", "is_new_merchant": False, "prior_orders": 12},
    {"id": "p4", "name": "Wireless Headphones Max", "price_usd": 89.00, "merchant": "AudioHub (established)", "is_new_merchant": False, "prior_orders": 12},
    {"id": "p5", "name": "Wireless Headphones Ultra Pro", "price_usd": 349.00, "merchant": "BrandNewStore99 (NEW)", "is_new_merchant": True, "prior_orders": 0},
]


def search(query):
    q = (query or "").strip().lower()
    if not q:
        return list(PRODUCTS)
    return [p for p in PRODUCTS if q in p["name"].lower() or q in p["merchant"].lower()]
