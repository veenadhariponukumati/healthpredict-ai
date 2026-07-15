"""Message Queue Protocol interface.

Abstraction over async event publishing and consumption.
Implementations: RedisPubSubQueue, RabbitMQQueue, GooglePubSubQueue, SQSBatchQueue.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol


class MessageQueueProtocol(Protocol):
    """Async message broker for event-driven communication.

    Used for async events such as "prediction_completed" -> trigger workflow.
    """

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an event to a topic/exchange."""
        ...

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """Register a handler for messages on a topic."""
        ...

    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge successful processing of a message."""
        ...

    async def dead_letter(self, message_id: str, reason: str) -> None:
        """Move a failed message to the dead-letter queue."""
        ...

    async def health(self) -> bool:
        """Check queue availability."""
        ...