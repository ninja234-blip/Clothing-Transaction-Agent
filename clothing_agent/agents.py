"""Built-in multi-agent system (no API key needed): a shopper/orchestrator agent that delegates
to catalog, safety and checkout agents over the A2A bus."""
import re
from . import catalog, tools
from .a2a import A2ABus, AgentCard, BaseAgent


class CatalogAgent(BaseAgent):
    card = AgentCard("catalog_agent", "Searches, filters and recommends clothing", ["search", "recommend"])

    def handle(self, msg):
        if msg.task == "search":
            return tools.search_products(**msg.payload)
        if msg.task == "recommend":
            return tools.get_recommendations(**msg.payload)
        return {"status": "error", "error": f"unknown task {msg.task}"}


class SafetyAgent(BaseAgent):
    card = AgentCard("safety_agent", "Validates carts before any money moves", ["validate_cart"])

    def handle(self, msg):
        if msg.task == "validate_cart":
            return tools.check_transaction_safety(**msg.payload)
        return {"status": "error", "error": f"unknown task {msg.task}"}


class CheckoutAgent(BaseAgent):
    card = AgentCard("checkout_agent", "Creates and captures PayPal payments", ["checkout", "capture"])

    def handle(self, msg):
        if msg.task == "checkout":
            verdict = self.bus.send("checkout_agent", "safety_agent", "validate_cart",
                                    {"user_id": msg.payload["user_id"]})
            if verdict["decision"] == "blocked":
                return {"status": "blocked", "reasons": verdict["reasons"]}
            return tools.create_checkout(**msg.payload)
        if msg.task == "capture":
            return tools.confirm_payment(**msg.payload)
        return {"status": "error", "error": f"unknown task {msg.task}"}


_CATEGORY_WORDS = {"hoodie": "hoodies", "tee": "tees", "t-shirt": "tees", "shirt": "tees", "jean": "jeans",
                   "jacket": "jackets", "coat": "jackets", "sneaker": "sneakers", "shoe": "sneakers",
                   "dress": "dresses", "short": "shorts"}

HELP = """Try things like:
  show me black hoodies under $60      find sneakers size 10
  recommend                            add P001 size M   (or: add P001 size L x2)
  cart                                 checkout   (then: pay)
  help | quit"""


class ShopperAgent(BaseAgent):
    """Orchestrator: understands the user's text and delegates work to specialist agents."""
    card = AgentCard("shopper_agent", "Talks to the user and coordinates the other agents", ["chat"])

    def __init__(self, bus, user_id="demo"):
        super().__init__(bus)
        self.user_id, self.last_order = user_id, None

    def ask(self, agent, task, payload):
        return self.bus.send("shopper_agent", agent, task, payload)

    def chat(self, text: str) -> str:
        t = text.lower().strip()
        if t in ("help", "?"):
            return HELP
        if t.startswith("recommend") or "for me" in t:
            return self._fmt_products(self.ask("catalog_agent", "recommend", {"user_id": self.user_id}), "Picks for you")
        if t.startswith("add"):
            return self._add(text)
        if t in ("cart", "show cart", "my cart"):
            return self._cart()
        if t.startswith("checkout"):
            return self._checkout(confirm="confirm" in t)
        if t in ("pay", "confirm payment", "paid", "i approved it"):
            return self._pay()
        return self._search(t)

    # -- handlers ---------------------------------------------------------
    def _search(self, t):
        args = {"query": "", "category": "", "max_price": 0, "size": "", "color": ""}
        m = re.search(r"(?:under|below|less than|<)\s*\$?(\d+)", t)
        if m:
            args["max_price"] = float(m.group(1))
        m = re.search(r"\bsize\s+(xs|s|m|l|xl|xxl|\d{1,2})\b", t)
        if m:
            args["size"] = m.group(1).upper()
        for stem, cat in _CATEGORY_WORDS.items():
            if re.search(rf"\b{re.escape(stem)}(?:s|es)?\b", t):
                args["category"] = cat
        args["color"] = next((c for c in catalog.COLORS if re.search(rf"\b{c}\b", t)), "")
        if not (args["category"] or args["color"] or args["max_price"] or args["size"]):
            args["query"] = t
        return self._fmt_products(self.ask("catalog_agent", "search", args), "Results")

    def _add(self, text):
        m = re.search(r"\b(p\d{3})\b", text, re.I)
        if not m:
            return "Tell me which product, e.g. 'add P001 size M'."
        p = catalog.get(m.group(1))
        if not p:
            return f"I don't know product {m.group(1).upper()}."
        sm = re.search(r"\bsize\s+(\w+)", text, re.I)
        qm = re.search(r"\bx\s*(\d+)\b", text, re.I)
        size = sm.group(1) if sm else ("M" if "M" in p["stock"] else next(iter(p["stock"])))
        qty = int(qm.group(1)) if qm else 1
        r = tools.add_to_cart(self.user_id, p["id"], size, qty)
        return r.get("message") or r["error"]

    def _cart(self):
        c = tools.view_cart(self.user_id)
        if not c["items"]:
            return "Your cart is empty."
        rows = [f"  {l['qty']} x {l['name']} ({l['size']}) - ${l['line_total']:.2f}" for l in c["items"]]
        t = c["totals"]
        rows.append(f"  Subtotal ${t['subtotal']:.2f} | Shipping ${t['shipping']:.2f} | Tax ${t['tax']:.2f} | TOTAL ${t['total']:.2f}")
        return "Your cart:\n" + "\n".join(rows)

    def _checkout(self, confirm):
        r = self.ask("checkout_agent", "checkout", {"user_id": self.user_id, "confirm": confirm})
        if r["status"] == "blocked":
            return "Checkout blocked by the safety agent:\n  - " + "\n  - ".join(r["reasons"])
        if r["status"] == "needs_confirmation":
            return "Safety agent: " + " ".join(r["reasons"]) + "\n  Type 'checkout confirm' to proceed."
        if r["status"] != "success":
            return f"Checkout failed: {r.get('error')}"
        self.last_order = r["order_id"]
        mode = "MOCK" if r["mock"] else "PayPal Sandbox"
        return (f"Order {r['order_id']} created ({mode}), total ${r['total']:.2f}.\n"
                f"  Approve it here: {r['approve_url']}\n  Then type 'pay' to capture the payment.")

    def _pay(self):
        if not self.last_order:
            return "There's no pending order. Type 'checkout' first."
        r = self.ask("checkout_agent", "capture", {"order_id": self.last_order})
        if r["status"] != "success":
            return f"Payment not completed: {r.get('error')}"
        self.last_order = None
        return f"Payment complete! Paid ${r['paid']:.2f}. Thanks for shopping."

    @staticmethod
    def _fmt_products(r, title):
        if not r["products"]:
            return "No matching items found."
        rows = [f"  {p['id']}  {p['name']:<26} {p['color']:<6} ${p['price']:>6.2f}" for p in r["products"]]
        return f"{title}:\n" + "\n".join(rows)


def build_system(verbose=True, user_id="demo"):
    bus = A2ABus(verbose=verbose)
    CatalogAgent(bus); SafetyAgent(bus); CheckoutAgent(bus)
    return ShopperAgent(bus, user_id), bus
