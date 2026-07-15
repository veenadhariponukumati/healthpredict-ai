"""Notification Provider Protocol interface.

Abstraction over multi-channel notification delivery.
Implementations: SMTPEmailProvider, TwilioSMSProvider, SendGridProvider,
SlackWebhookProvider, ConsoleNotificationProvider.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class NotificationResult(BaseModel):
    """Result from sending a notification."""

    success: bool
    notification_id: str
    channel: str
    recipient: str
    provider: str
    status: str
    sent_at: str


class NotificationProviderProtocol(Protocol):
    """Multi-channel notification delivery.

    n8n workflows call this interface through the Workflow Service's
    n8n webhook proxy, decoupling notification logic from workflow tooling.
    """

    async def send(
        self,
        recipient: str,
        template_name: str,
        context: dict[str, Any],
        channel: str,
    ) -> NotificationResult:
        """Send a notification via the specified channel.

        Args:
            recipient: Email address, phone number, or webhook URL.
            template_name: Named template (e.g., 'high_risk_alert_physician').
            context: Template variable bindings.
            channel: 'email' | 'sms' | 'slack'.

        Returns:
            NotificationResult with delivery status.
        """
        ...

    async def get_delivery_status(self, notification_id: str) -> str:
        """Check delivery status of a previously sent notification."""
        ...