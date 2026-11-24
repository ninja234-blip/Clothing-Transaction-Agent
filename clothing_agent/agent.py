"""Real Google ADK version of the same multi-agent system.

Needs:  pip install google-adk   and   GOOGLE_API_KEY in your environment (or .env).
Run:    adk web      (from the project root, then pick 'clothing_agent')   or   adk run clothing_agent
ADK's sub_agents delegation plays the role of A2A routing here.
"""
import os
from google.adk.agents import Agent
from . import tools

MODEL = os.getenv("ADK_MODEL", "gemini-2.0-flash")
USER = "Always use user_id 'demo' when a tool asks for one."

catalog_agent = Agent(
    name="catalog_agent", model=MODEL,
    description="Searches, filters and recommends clothing products.",
    instruction="Help the shopper find clothing. Use search_products and get_recommendations. " + USER,
    tools=[tools.search_products, tools.get_recommendations])

safety_agent = Agent(
    name="safety_agent", model=MODEL,
    description="Validates the cart for transaction safety before payment.",
    instruction="Run check_transaction_safety and explain the decision plainly. Never approve a 'blocked' cart. " + USER,
    tools=[tools.view_cart, tools.check_transaction_safety])

checkout_agent = Agent(
    name="checkout_agent", model=MODEL,
    description="Creates and captures PayPal payments.",
    instruction=("Only call create_checkout after safety_agent approved the cart. Set confirm=True ONLY if the user "
                 "explicitly agreed to a large purchase. Call confirm_payment only after the user says they approved "
                 "the PayPal order. " + USER),
    tools=[tools.create_checkout, tools.confirm_payment])

root_agent = Agent(
    name="shopping_orchestrator", model=MODEL,
    description="Clothing shopping assistant that coordinates specialist agents.",
    instruction=("You are a friendly clothing shopping assistant. Delegate: product questions -> catalog_agent, "
                 "pre-payment checks -> safety_agent, payment -> checkout_agent. Use add_to_cart/view_cart yourself. " + USER),
    tools=[tools.add_to_cart, tools.view_cart],
    sub_agents=[catalog_agent, safety_agent, checkout_agent])
