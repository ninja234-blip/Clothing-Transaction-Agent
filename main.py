"""Clothing Transaction Agent - run this file (VS Code: press the ▶ button).

    python main.py           interactive chat
    python main.py --demo    scripted walkthrough
    python main.py --quiet   hide the agent-to-agent message trace
"""
import sys
from clothing_agent.agents import build_system

DEMO = ["show me black hoodies under $60", "recommend", "add P001 size M", "add P012 size 10 x2",
        "cart", "checkout", "checkout confirm", "pay"]


def main():
    shopper, bus = build_system(verbose="--quiet" not in sys.argv)
    print("Clothing Transaction Agent  |  agents:", ", ".join(c.name for c in bus.discover()))
    print("Type 'help' for examples, 'quit' to exit.\n")
    if "--demo" in sys.argv:
        for line in DEMO:
            print(f"you> {line}")
            print(shopper.chat(line), "\n")
        return
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("quit", "exit"):
            break
        if line:
            print(shopper.chat(line), "\n")


if __name__ == "__main__":
    main()
