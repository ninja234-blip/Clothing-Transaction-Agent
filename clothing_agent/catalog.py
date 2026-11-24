"""In-memory fake clothing catalog."""
import re

STOP = {"a", "an", "the", "me", "show", "find", "i", "want", "need", "some", "for", "to", "in",
        "looking", "search", "get", "under", "below", "size", "and", "with", "of"}


def _p(pid, name, category, color, price, tags, sizes, stock=5):
    return {"id": pid, "name": name, "category": category, "color": color, "price": price,
            "tags": tags, "stock": {s: stock for s in sizes}}


_CLOTHES = ["S", "M", "L", "XL"]
_SHOES = ["8", "9", "10", "11"]

PRODUCTS = [
    _p("P001", "Classic Pullover Hoodie", "hoodies", "black", 54.00, ["casual", "warm"], _CLOTHES),
    _p("P002", "Oversized Zip Hoodie", "hoodies", "gray", 62.00, ["streetwear", "warm"], _CLOTHES),
    _p("P003", "Fleece Hoodie", "hoodies", "blue", 48.50, ["cozy", "warm"], _CLOTHES),
    _p("P004", "Essential Cotton Tee", "tees", "white", 19.99, ["basic", "summer"], _CLOTHES),
    _p("P005", "Graphic Tee", "tees", "black", 27.00, ["streetwear", "summer"], _CLOTHES),
    _p("P006", "Pocket Tee", "tees", "green", 22.00, ["basic", "casual"], _CLOTHES),
    _p("P007", "Slim Fit Jeans", "jeans", "blue", 69.00, ["denim", "casual"], ["S", "M", "L"]),
    _p("P008", "Relaxed Fit Jeans", "jeans", "black", 74.00, ["denim", "relaxed"], ["M", "L", "XL"]),
    _p("P009", "Denim Jacket", "jackets", "blue", 89.00, ["denim", "layer"], _CLOTHES),
    _p("P010", "Puffer Jacket", "jackets", "black", 139.00, ["winter", "warm"], _CLOTHES),
    _p("P011", "Rain Shell Jacket", "jackets", "green", 99.00, ["waterproof", "layer"], _CLOTHES),
    _p("P012", "Everyday Sneakers", "sneakers", "white", 85.00, ["casual", "comfort"], _SHOES),
    _p("P013", "Runner Sneakers", "sneakers", "gray", 110.00, ["running", "comfort"], _SHOES),
    _p("P014", "High-Top Sneakers", "sneakers", "black", 95.00, ["streetwear"], _SHOES),
    _p("P015", "Summer Midi Dress", "dresses", "red", 58.00, ["summer", "formal"], ["S", "M", "L"]),
    _p("P016", "Linen Shorts", "shorts", "beige", 36.00, ["summer", "casual"], _CLOTHES),
    _p("P017", "Out-of-Stock Cargo Pants", "pants", "green", 65.00, ["utility"], _CLOTHES, stock=0),
]

CATEGORIES = sorted({p["category"] for p in PRODUCTS})
COLORS = sorted({p["color"] for p in PRODUCTS})


def get(product_id):
    for p in PRODUCTS:
        if p["id"].lower() == str(product_id).lower():
            return p
    return None


def search(query="", category="", max_price=0, size="", color=""):
    tokens = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOP]
    out = []
    for p in PRODUCTS:
        if category and p["category"] != category.lower():
            continue
        if color and p["color"] != color.lower():
            continue
        if max_price and p["price"] > float(max_price):
            continue
        if size and p["stock"].get(size.upper(), 0) <= 0:
            continue
        if not any(p["stock"].values()):
            continue  # fully out of stock
        if tokens:
            hay = " ".join([p["name"], p["category"], p["color"], *p["tags"]]).lower()
            if not any(t in hay for t in tokens):
                continue
        out.append(p)
    return out


def decrement(product_id, size, qty):
    p = get(product_id)
    p["stock"][size] = max(0, p["stock"][size] - qty)
