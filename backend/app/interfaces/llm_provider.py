"""LLM Provider Protocol interface.

Abstraction over natural language explanation generation.
Implementations: AzureOpenAIProvider, OpenAIProvider, AnthropicProvider,
TemplateFallbackProvider.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from pydantic import BaseModel


class ExplanationContext(BaseModel):
    """Structured context for LLM explanation generation.

    All fields have been PHI-stripped before reaching this interface.
    """

    model_name: str
    model_version: str
    risk_score: float
    risk_level: str
    threshold: float
    features: dict[str, float]
    shap_values: dict[str, float]
    base_value: float
    top_features: list[dict[str, Any]]
    patient_age: Optional[int] = None
    previous_admissions: Optional[int] = None
    primary_diagnosis: Optional[str] = None


class ExplanationResult(BaseModel):
    """Result from an LLM explanation provider."""

    summary: str
    contributing_factors: list[dict[str, str]]
    monitoring_suggestions: list[str]
    disclaimer: str
    provider: str
    latency_ms: int


class LLMProviderProtocol(Protocol):
    """Interface for generating clinician-friendly explanations.

    The LLM NEVER predicts readmission risk. It only translates model outputs
    into natural language. The primary implementation is Azure OpenAI; a template
    fallback is used when the LLM is unavailable.
    """

    async def generate_explanation(
        self, context: ExplanationContext
    ) -> ExplanationResult:
        """Generate a clinician-friendly explanation from model outputs.

        Args:
            context: Structured data that has already been PHI-stripped.

        Returns:
            ExplanationResult with summary, factors, disclaimer.
        """
        ...

    async def health(self) -> bool:
        """Check provider availability."""
        ...