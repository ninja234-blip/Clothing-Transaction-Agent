"""PayPal client. Uses a mock unless PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are set,
in which case it talks to the PayPal *Sandbox* REST API (no real money)."""
import base64
import json
import os
import urllib.request
import uuid

SANDBOX = "https://api-m.sandbox.paypal.com"


class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.live = bool(self.client_id and self.secret)
        self._mock_orders = {}

    # -- public API ---------------------------------------------------------
    def create_order(self, amount, description="Clothing order", currency="USD"):
        if not self.live:
            oid = "MOCK-" + uuid.uuid4().hex[:10].upper()
            self._mock_orders[oid] = "CREATED"
            return {"id": oid, "status": "CREATED", "mock": True,
                    "approve_url": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}"}
        body = {"intent": "CAPTURE", "purchase_units": [
            {"description": description, "amount": {"currency_code": currency, "value": f"{amount:.2f}"}}]}
        data = self._request("POST", "/v2/checkout/orders", body)
        link = next((l["href"] for l in data.get("links", []) if l["rel"] in ("approve", "payer-action")), "")
        return {"id": data["id"], "status": data["status"], "approve_url": link, "mock": False}

    def capture_order(self, order_id):
        if not self.live:
            self._mock_orders[order_id] = "COMPLETED"
            return {"id": order_id, "status": "COMPLETED", "mock": True}
        data = self._request("POST", f"/v2/checkout/orders/{order_id}/capture", {})
        return {"id": order_id, "status": data.get("status"), "mock": False}

    # -- internals ----------------------------------------------------------
    def _token(self):
        creds = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode()
        req = urllib.request.Request(SANDBOX + "/v1/oauth2/token", data=b"grant_type=client_credentials",
                                     headers={"Authorization": f"Basic {creds}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)["access_token"]

    def _request(self, method, path, body):
        req = urllib.request.Request(
            SANDBOX + path, data=json.dumps(body).encode(), method=method,
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json",
                     "PayPal-Request-Id": uuid.uuid4().hex})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
