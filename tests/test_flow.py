import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clothing_agent import tools  # noqa: E402
from clothing_agent.agents import build_system  # noqa: E402


class FlowTests(unittest.TestCase):
    def setUp(self):
        tools.reset_state()
        self.shopper, _ = build_system(verbose=False)

    def test_search_filters(self):
        r = tools.search_products(category="hoodies", max_price=55, color="black")
        self.assertEqual([p["id"] for p in r["products"]], ["P001"])

    def test_out_of_stock_hidden(self):
        self.assertNotIn("P017", [p["id"] for p in tools.search_products()["products"]])

    def test_empty_cart_blocked(self):
        self.assertEqual(tools.check_transaction_safety()["decision"], "blocked")

    def test_large_cart_needs_confirmation(self):
        tools.add_to_cart("demo", "P010", "M", 2)
        self.assertEqual(tools.create_checkout()["status"], "needs_confirmation")
        self.assertEqual(tools.create_checkout(confirm=True)["status"], "success")

    def test_over_limit_blocked(self):
        tools.add_to_cart("demo", "P010", "M", 5)
        tools.add_to_cart("demo", "P010", "L", 5)
        self.assertEqual(tools.create_checkout(confirm=True)["status"], "blocked")

    def test_full_conversation(self):
        self.shopper.chat("add P001 size M")
        self.assertIn("created", self.shopper.chat("checkout"))
        self.assertIn("Payment complete", self.shopper.chat("pay"))
        self.assertIn("empty", self.shopper.chat("cart"))


if __name__ == "__main__":
    unittest.main()
