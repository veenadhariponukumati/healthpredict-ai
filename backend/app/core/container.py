"""Dependency injection container.

Wires all implementations to protocol interfaces at startup.
This is the only file that knows about concrete vendor implementations.
"""

from __future__ import annotations

from app.core.config import settings


class ServiceContainer:
    """Application service container.

    Wires interface implementations based on configuration.
    Business logic never imports vendor SDKs directly — only through protocols
    wired here. In development/staging, stubs can be used; in production,
    real adapters are wired.
    """

    def __init__(self, config=None) -> None:
        self._config = config or settings
        self._initialized = False

        # Protocol slots — initialized in init()
        self.feature_store = None
        self.model_registry = None
        self.llm_provider = None
        self.message_queue = None
        self.notification_provider = None
        self.object_storage = None

    async def init(self) -> None:
        """Initialize all services.

        Call once at application startup before handling requests.
        """
        if self._initialized:
            return

        self._wire_feature_store()
        self._wire_model_registry()
        self._wire_llm_provider()
        self._wire_message_queue()
        self._wire_notification_provider()
        self._wire_object_storage()

        self._initialized = True

    async def shutdown(self) -> None:
        """Gracefully shut down all services."""
        self._initialized = False

    def _wire_feature_store(self) -> None:
        """Wire PostgreSQL feature store."""
        try:
            from app.adapters.feature_store import PostgreSQLFeatureStore
            self.feature_store = PostgreSQLFeatureStore()
        except ImportError:
            self.feature_store = None

    def _wire_model_registry(self) -> None:
        """Wire MLflow model registry."""
        try:
            from app.adapters.mlflow_registry import MLflowRegistry
            registry = MLflowRegistry(
                tracking_uri=getattr(self._config, 'MLFLOW_TRACKING_URI', 'http://mlflow:5000'),
            )
            self.model_registry = registry
        except ImportError:
            self.model_registry = None

    def _wire_llm_provider(self) -> None:
        """Wire LLM provider with circuit breaker fallback."""
        # The LLM service handles its own Azure OpenAI + template fallback
        # This slot is for when LLM is called directly from the API gateway
        self.llm_provider = None

    def _wire_message_queue(self) -> None:
        """Wire message queue (Redis pub/sub)."""
        import json
        import logging
        logger = logging.getLogger(__name__)
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                getattr(self._config, 'REDIS_URL', 'redis://localhost:6379/0'),
                decode_responses=True,
            )
            # Simple message queue using Redis pub/sub
            class RedisMessageQueue:
                def __init__(self, redis):
                    self._redis = redis
                async def publish(self, topic, payload):
                    await self._redis.publish(topic, json.dumps(payload))
                async def subscribe(self, topic, handler):
                    pubsub = self._redis.pubsub()
                    await pubsub.subscribe(topic)
                    async for msg in pubsub.listen():
                        if msg['type'] == 'message':
                            await handler(json.loads(msg['data']))
                async def acknowledge(self, message_id):
                    pass
                async def dead_letter(self, message_id, reason):
                    logger.warning("dead_letter", message_id=message_id, reason=reason)
                async def health(self):
                    try:
                        await self._redis.ping()
                        return True
                    except Exception:
                        return False
            self.message_queue = RedisMessageQueue(self._redis)
        except ImportError:
            self.message_queue = None

    def _wire_notification_provider(self) -> None:
        """Wire notification provider."""
        self.notification_provider = None

    def _wire_object_storage(self) -> None:
        """Wire object storage."""
        self.object_storage = None


# Global container instance — used by FastAPI dependency injection
container = ServiceContainer()