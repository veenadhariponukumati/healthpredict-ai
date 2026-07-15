"""Interface definitions for infrastructure abstraction (protocols).

All third-party dependencies are hidden behind Python Protocols.
Business logic imports only these interfaces — never vendor SDKs directly.
"""

from app.interfaces.feature_store import FeatureStoreProtocol
from app.interfaces.model_registry import ModelRegistryProtocol
from app.interfaces.llm_provider import LLMProviderProtocol
from app.interfaces.message_queue import MessageQueueProtocol
from app.interfaces.notification_provider import NotificationProviderProtocol
from app.interfaces.object_storage import ObjectStorageProtocol

__all__ = [
    "FeatureStoreProtocol",
    "ModelRegistryProtocol",
    "LLMProviderProtocol",
    "MessageQueueProtocol",
    "NotificationProviderProtocol",
    "ObjectStorageProtocol",
]