"""LLM Service — Azure OpenAI integration for clinician-friendly explanations.

Standalone FastAPI service (port 8003).
Decision-support only — NEVER predicts readmission.
"""

from __future__ import annotations

import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger, setup_logging
from app.interfaces.llm_provider import ExplanationContext, ExplanationResult

logger = get_logger(__name__)

# Provider state
llm_provider = None
fallback_provider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_provider, fallback_provider
    setup_logging()
    logger.info("llm_service_started")
    yield
    logger.info("llm_service_shutdown")


app = FastAPI(title="LLM Service", version="1.0.0", lifespan=lifespan)


# ── Schemas ──────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    model_name: str = "readmission-predictor"
    model_version: str = "1.0.0"
    risk_score: float
    risk_level: str
    threshold: float = 0.35
    features: dict[str, float]
    shap_values: dict[str, float]
    base_value: float
    top_features: list[dict]
    patient_age: int | None = None
    previous_admissions: int | None = None
    primary_diagnosis: str | None = None


class ExplainResponse(BaseModel):
    summary: str
    contributing_factors: list[dict[str, str]]
    monitoring_suggestions: list[str]
    disclaimer: str
    provider: str = "template_fallback"
    latency_ms: int


# ── Template Fallback ───────────────────────────────────────────────

TEMPLATE_DISCLAIMER = (
    "This analysis is AI-generated decision support only. It does not "
    "constitute a clinical diagnosis, medical advice, or a substitute "
    "for professional clinical judgment. All AI-generated outputs must "
    "be reviewed by a qualified healthcare professional before any "
    "clinical action is taken."
)


def generate_template_explanation(ctx: ExplanationContext) -> ExplanationResult:
    """Generate a rule-based explanation from SHAP values when LLM is unavailable."""
    top = ctx.top_features[:3] if ctx.top_features else []

    # Build summary
    if ctx.risk_level == "HIGH" or ctx.risk_level == "CRITICAL":
        summary = (
            f"This patient has a {ctx.risk_level.lower()} readmission risk "
            f"(score: {ctx.risk_score:.2f}). "
        )
    elif ctx.risk_level == "MODERATE":
        summary = (
            f"This patient has a moderately elevated readmission risk "
            f"(score: {ctx.risk_score:.2f}). "
        )
    else:
        summary = (
            f"This patient has a low readmission risk "
            f"(score: {ctx.risk_score:.2f}). "
        )

    if top:
        factors_str = "The primary contributing factors are: "
        for i, f in enumerate(top):
            direction = "increases" if f.get("shap_value", 0) > 0 else "decreases"
            factors_str += f"{f.get('feature', 'unknown')} ({direction} risk)"
            if i < len(top) - 1:
                factors_str += ", "
        summary += factors_str + "."

    # Build contributing factors
    factors = []
    for f in top[:3]:
        direction = "increases" if f.get("shap_value", 0) > 0 else "decreases"
        factors.append({
            "factor": f.get("feature", "unknown"),
            "explanation": (
                f"{f.get('feature', 'unknown')} {direction} "
                f"readmission risk (SHAP value: {f.get('shap_value', 0):.3f})"
            ),
        })

    # Monitoring suggestions based on risk level
    if ctx.risk_level == "HIGH" or ctx.risk_level == "CRITICAL":
        suggestions = [
            "Schedule follow-up appointment within 48 hours",
            "Review discharge medications for adherence",
            "Confirm home health services are in place",
            "Monitor for condition-specific warning signs",
        ]
    elif ctx.risk_level == "MODERATE":
        suggestions = [
            "Schedule follow-up within 7 days",
            "Provide enhanced discharge instructions",
            "Coordinate with primary care provider",
        ]
    else:
        suggestions = [
            "Standard discharge follow-up within 30 days",
            "Provide standard discharge instructions",
        ]

    return ExplanationResult(
        summary=summary,
        contributing_factors=factors,
        monitoring_suggestions=suggestions,
        disclaimer=TEMPLATE_DISCLAIMER,
        provider="template_fallback",
        latency_ms=5,
    )


# ── Azure OpenAI Provider ───────────────────────────────────────────


class AzureOpenAIProvider:
    """Azure OpenAI implementation of LLMProviderProtocol."""

    SYSTEM_PROMPT = (
        "You are a clinical decision support assistant. You receive structured model output "
        "and explain it in clinician-friendly language. You NEVER diagnose, NEVER recommend "
        "specific treatments, and NEVER override the risk score. You always include the "
        "disclaimer that this is AI-generated decision support only.\n\n"
        "Output valid JSON with these fields:\n"
        '{"summary": "...", "contributing_factors": [{"factor": "...", "explanation": "..."}], '
        '"monitoring_suggestions": ["..."], "disclaimer": "..."}'
    )

    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    async def generate_explanation(self, ctx: ExplanationContext) -> ExplanationResult:
        import json
        from openai import AsyncAzureOpenAI

        client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=self.endpoint,
        )

        user_prompt = (
            f"Context:\n"
            f"- Model: {ctx.model_name} v{ctx.model_version}\n"
            f"- Risk score: {ctx.risk_score:.2f} ({ctx.risk_level})\n"
            f"- Threshold: {ctx.threshold}\n\n"
            f"Top contributing factors:\n"
        )
        for f in ctx.top_features[:5]:
            user_prompt += (
                f"- {f.get('feature', 'unknown')}: "
                f"SHAP value = {f.get('shap_value', 0):.3f}\n"
            )

        user_prompt += (
            f"\nPatient: Age {ctx.patient_age or 'unknown'}, "
            f"Diagnosis: {ctx.primary_diagnosis or 'unknown'}\n\n"
            f"Generate a clinical decision support explanation in JSON format."
        )

        response = await client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return ExplanationResult(
            summary=result.get("summary", ""),
            contributing_factors=result.get("contributing_factors", []),
            monitoring_suggestions=result.get("monitoring_suggestions", []),
            disclaimer=result.get("disclaimer", TEMPLATE_DISCLAIMER),
            provider="azure_openai",
            latency_ms=0,
        )

    async def health(self) -> bool:
        return bool(self.endpoint and self.api_key)


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/explain", response_model=ExplainResponse)
async def explain(request: ExplainRequest):
    """Generate a clinician-friendly explanation from model outputs.

    This endpoint NEVER predicts readmission risk.
    It only translates ML model outputs into natural language.
    """
    start = time.time()

    ctx = ExplanationContext(
        model_name=request.model_name,
        model_version=request.model_version,
        risk_score=request.risk_score,
        risk_level=request.risk_level,
        threshold=request.threshold,
        features=request.features,
        shap_values=request.shap_values,
        base_value=request.base_value,
        top_features=request.top_features,
        patient_age=request.patient_age,
        previous_admissions=request.previous_admissions,
        primary_diagnosis=request.primary_diagnosis,
    )

    # Try Azure OpenAI if configured, fall back to template
    azure = AzureOpenAIProvider()
    if await azure.health():
        try:
            result = await azure.generate_explanation(ctx)
            provider = "azure_openai"
        except Exception as e:
            logger.warning("azure_openai_failed", error=str(e))
            result = generate_template_explanation(ctx)
            provider = "template_fallback"
    else:
        result = generate_template_explanation(ctx)
        provider = "template_fallback"

    latency_ms = int((time.time() - start) * 1000)

    return ExplainResponse(
        summary=result.summary,
        contributing_factors=result.contributing_factors,
        monitoring_suggestions=result.monitoring_suggestions,
        disclaimer=TEMPLATE_DISCLAIMER,
        provider=provider,
        latency_ms=latency_ms,
    )