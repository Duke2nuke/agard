"""PayPal sandbox client — Orders API via REST, using requests.

Sandbox base: https://api-m.sandbox.paypal.com
Credentials come ONLY from environment variables, never hardcoded.
If credentials are missing, the caller must stay in mock mode and say so.
"""
import base64
import os
import requests

BASE = "https://api-m.sandbox.paypal.com"


def has_credentials():
    return bool(os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_CLIENT_SECRET"))


def _token():
    cid = os.environ["PAYPAL_CLIENT_ID"]
    sec = os.environ["PAYPAL_CLIENT_SECRET"]
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    r = requests.post(
        f"{BASE}/v1/oauth2/token",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_order(amount_usd, description="Agard demo order"):
    """Create a sandbox order. Returns (order_id, approve_url_or_None)."""
    token = _token()
    r = requests.post(
        f"{BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"}, "description": description}],
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    approve = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
    return data["id"], approve


def capture_order(order_id):
    token = _token()
    r = requests.post(
        f"{BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()
