from dataclasses import dataclass
from typing import Any

MESSAGE_TYPES = {
    "ASSIGNMENT",
    "STATUS_UPDATE",
    "ROUTE_BLOCKED",
    "ZONE_REPORT",
    "TASK_COMPLETE",
    "REQUEST_HELP",
}


@dataclass
class Message:
    type: str
    sender: str
    tick: int
    payload: dict[str, Any]
    recipient: str | None = None

    def __post_init__(self) -> None:
        if self.type not in MESSAGE_TYPES:
            raise ValueError(f"unknown message type: {self.type!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "tick": self.tick,
            "payload": dict(self.payload),
        }


class MessageBus:
    def __init__(self) -> None:
        self._inboxes: dict[str, list[Message]] = {}
        self._log: list[Message] = []

    def register(self, agent_id: str) -> None:
        self._inboxes.setdefault(agent_id, [])

    def send(self, message: Message) -> None:
        self._log.append(message)
        if message.recipient is None:
            for agent_id, inbox in self._inboxes.items():
                if agent_id != message.sender:
                    inbox.append(message)
            return
        if message.recipient not in self._inboxes:
            raise ValueError(f"unknown recipient: {message.recipient!r}")
        self._inboxes[message.recipient].append(message)

    def drain(self, agent_id: str) -> list[Message]:
        inbox = self._inboxes.setdefault(agent_id, [])
        messages = list(inbox)
        inbox.clear()
        return messages

    @property
    def log(self) -> list[Message]:
        return list(self._log)

    def log_for_tick(self, tick: int) -> list[Message]:
        return [m for m in self._log if m.tick == tick]
