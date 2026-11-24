"""Shared tools. The SAME functions are used by the built-in demo agents, the Google ADK
agents, and the MCP server, so behavior is identical everywhere."""
from . import catalog
from .paypal_client import PayPalClient

TAX_RATE = 0.0825          # Texas-ish sales tax
SHIPPING = 5.99
FREE_SHIPPING_OVER = 75.0
CONFIRM_ABOVE = 200.0      # needs explicit user confirmation
BLOCK_ABOVE = 1000.0       # hard block
MAX_QTY_PER_ITEM = 5

CARTS: dict = {}
ORDERS: dict = {}
PROFILES = {"demo": {"categories": ["hoodies", "sneakers"], "colors": ["black", "gray"], "budget": 120}}
_paypal = None


def _client():
    global _paypal
    if _paypal is None:
        _paypal = PayPalClient()
    return _paypal


def reset_state():
    CARTS.clear()
    ORDERS.clear()


def _lines(user_id):
    out = []
    for it in CARTS.get(user_id, []):
        p = catalog.get(it["product_id"])
        out.append({**it, "name": p["name"], "unit_price": p["price"],
                    "line_total": round(p["price"] * it["qty"], 2)})
    return out


def _totals(lines):
    sub = round(sum(l["line_total"] for l in lines), 2)
    ship = 0.0 if (sub == 0 or sub >= FREE_SHIPPING_OVER) else SHIPPING
    tax = round(sub * TAX_RATE, 2)
    return {"subtotal": sub, "shipping": ship, "tax": tax, "total": round(sub + ship + tax, 2)}


# ---------------------------------------------------------------- catalog tools
def search_products(query: str = "", category: str = "", max_price: float = 0,
                    size: str = "", color: str = "") -> dict:
    """Search the clothing catalog. Filter by category (hoodies, tees, jeans, jackets, sneakers,
    dresses, shorts), max_price in USD, size (S/M/L/XL or shoe size) and color. Use 0 or empty to skip a filter."""
    res = catalog.search(query, category, max_price, size, color)
    return {"status": "success", "count": len(res),
            "products": [{"id": p["id"], "name": p["name"], "category": p["category"], "color": p["color"],
                          "price": p["price"], "sizes": [s for s, n in p["stock"].items() if n > 0]} for p in res]}


def get_recommendations(user_id: str = "demo", limit: int = 3) -> dict:
    """Personalized picks based on the shopper's saved category/color/budget preferences."""
    prof = PROFILES.get(user_id, {})
    scored = []
    for p in catalog.PRODUCTS:
        if not any(p["stock"].values()):
            continue
        score = (2 if p["category"] in prof.get("categories", []) else 0) \
            + (1 if p["color"] in prof.get("colors", []) else 0) \
            + (1 if p["price"] <= prof.get("budget", 1e9) else 0)
        scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1]["price"]))
    return {"status": "success", "products": [
        {"id": p["id"], "name": p["name"], "color": p["color"], "price": p["price"]} for _, p in scored[:limit]]}


# ---------------------------------------------------------------- cart tools
def add_to_cart(user_id: str = "demo", product_id: str = "", size: str = "M", qty: int = 1) -> dict:
    """Add a product (by id like P001) in a given size to the shopper's cart."""
    p = catalog.get(product_id)
    if not p:
        return {"status": "error", "error": f"Unknown product '{product_id}'."}
    size = size.upper()
    if p["stock"].get(size, 0) < qty:
        avail = [s for s, n in p["stock"].items() if n > 0]
        return {"status": "error", "error": f"{p['name']} not available in size {size}. Available: {avail or 'none'}."}
    cart = CARTS.setdefault(user_id, [])
    for it in cart:
        if it["product_id"] == p["id"] and it["size"] == size:
            it["qty"] += qty
            break
    else:
        cart.append({"product_id": p["id"], "size": size, "qty": qty})
    return {"status": "success", "message": f"Added {qty} x {p['name']} ({size})."}


def view_cart(user_id: str = "demo") -> dict:
    """Show cart contents with subtotal, shipping, tax and total."""
    lines = _lines(user_id)
    return {"status": "success", "items": lines, "totals": _totals(lines)}


# ---------------------------------------------------------------- safety + checkout
def check_transaction_safety(user_id: str = "demo") -> dict:
    """Run transaction-safety rules on the cart. Returns decision: approved, needs_confirmation, or blocked."""
    lines = _lines(user_id)
    totals = _totals(lines)
    reasons = []
    if not lines:
        return {"status": "success", "decision": "blocked", "reasons": ["Cart is empty."], "totals": totals}
    decision = "approved"
    for l in lines:
        p = catalog.get(l["product_id"])
        if p["stock"].get(l["size"], 0) < l["qty"]:
            decision = "blocked"; reasons.append(f"{l['name']} ({l['size']}) is no longer in stock.")
        if l["qty"] > MAX_QTY_PER_ITEM:
            decision = "blocked"; reasons.append(f"Quantity of {l['name']} exceeds the limit of {MAX_QTY_PER_ITEM}.")
    if totals["total"] > BLOCK_ABOVE:
        decision = "blocked"; reasons.append(f"Total ${totals['total']:.2f} exceeds the ${BLOCK_ABOVE:.0f} limit.")
    elif decision == "approved" and totals["total"] > CONFIRM_ABOVE:
        decision = "needs_confirmation"
        reasons.append(f"Total ${totals['total']:.2f} is over ${CONFIRM_ABOVE:.0f}; explicit confirmation required.")
    return {"status": "success", "decision": decision, "reasons": reasons, "totals": totals}


def create_checkout(user_id: str = "demo", confirm: bool = False) -> dict:
    """Create a PayPal order for the cart after re-running safety checks. Set confirm=True only if the
    user explicitly agreed to a large purchase."""
    safety = check_transaction_safety(user_id)
    if safety["decision"] == "blocked":
        return {"status": "blocked", "reasons": safety["reasons"]}
    if safety["decision"] == "needs_confirmation" and not confirm:
        return {"status": "needs_confirmation", "reasons": safety["reasons"], "totals": safety["totals"]}
    total = safety["totals"]["total"]
    try:
        order = _client().create_order(total, description=f"Clothing order for {user_id}")
    except Exception as e:  # network / auth errors from PayPal
        return {"status": "error", "error": f"PayPal error: {e}"}
    ORDERS[order["id"]] = {"user_id": user_id, "total": total, "lines": _lines(user_id)}
    return {"status": "success", "order_id": order["id"], "approve_url": order["approve_url"],
            "total": total, "mock": order["mock"]}


def confirm_payment(order_id: str) -> dict:
    """Capture the PayPal payment for an order the buyer has approved, then clear the cart."""
    order = ORDERS.get(order_id)
    if not order:
        return {"status": "error", "error": f"Unknown order '{order_id}'."}
    try:
        res = _client().capture_order(order_id)
    except Exception as e:
        return {"status": "error", "error": f"Capture failed (has the buyer approved the order yet?): {e}"}
    if res["status"] != "COMPLETED":
        return {"status": "error", "error": f"Payment status: {res['status']}"}
    for l in order["lines"]:
        catalog.decrement(l["product_id"], l["size"], l["qty"])
    CARTS[order["user_id"]] = []
    return {"status": "success", "order_id": order_id, "paid": order["total"], "mock": res["mock"]}
