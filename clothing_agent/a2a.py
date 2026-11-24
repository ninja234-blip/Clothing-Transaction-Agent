"""Lightweight, in-process agent-to-agent (A2A-style) messaging.
Agents publish an AgentCard (discovery) and exchange task messages through a bus.
This mirrors the ideas of Google's A2A protocol (agent cards, tasks, messages) without HTTP."""
import uuid
from dataclasses import dataclass, field


@dataclass
class AgentCard:
    name: str
    description: str
    skills: list


@dataclass
class A2AMessage:
    sender: str
    recipient: str
    task: str
    payload: dict
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class BaseAgent:
    card: AgentCard

    def __init__(self, bus):
        self.bus = bus
        bus.register(self)

    def handle(self, msg: A2AMessage) -> dict:
        raise NotImplementedError


class A2ABus:
    def __init__(self, verbose=True):
        self.agents, self.verbose, self.log = {}, verbose, []

    def register(self, agent):
        self.agents[agent.card.name] = agent

    def discover(self):
        return [a.card for a in self.agents.values()]

    def send(self, sender, recipient, task, payload):
        msg = A2AMessage(sender, recipient, task, payload)
        self._log(f"[A2A {msg.id}] {sender} -> {recipient}: {task}")
        reply = self.agents[recipient].handle(msg)
        self._log(f"[A2A {msg.id}] {recipient} -> {sender}: {reply.get('status')}")
        return reply

    def _log(self, line):
        self.log.append(line)
        if self.verbose:
            print(f"\033[2m  {line}\033[0m")
