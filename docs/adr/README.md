# Architecture Decision Records

## ADR-001: Service-Oriented Architecture over Monolith

**Status:** Accepted
**Date:** 2026-06-01

### Context
The platform requires independent scalability of ML inference, training, workflow orchestration, and LLM explanation services. A monolith would couple these concerns and prevent independent deployment and scaling.

### Decision
Adopt a service-oriented architecture with independently deployable services communicating via REST/gRPC. Each service owns its data domain and can be scaled independently.

### Consequences
- **Positive:** Independent scaling, deployment, and failure isolation
- **Positive:** Each service can use the most appropriate tech stack
- **Negative:** Increased operational complexity (N services to monitor)
- **Negative:** Network latency between services

### Mitigation
- Internal services communicate over Docker overlay network (near-zero latency)
- Circuit breaker pattern prevents cascading failures
- Structured logging with correlation IDs across services

---

## ADR-002: FastAPI over Django REST Framework

**Status:** Accepted
**Date:** 2026-06-01

### Context
The API gateway and all services need async support, high throughput, automatic OpenAPI documentation, and Pydantic validation.

### Decision
Use FastAPI for all Python services. FastAPI provides native async support, automatic OpenAPI generation, Pydantic v2 integration for request/response validation, and excellent performance (on par with Node.js/Go for typical API workloads).

### Consequences
- **Positive:** Automatic OpenAPI documentation at `/docs` and `/redoc`
- **Positive:** Top-tier performance with async I/O
- **Positive:** Pydantic v2 provides validation, serialization, and schema generation
- **Negative:** Smaller ecosystem than Django (but sufficient for API services)

---

## ADR-003: MLflow for Model Registry and Experiment Tracking

**Status:** Accepted
**Date:** 2026-06-01

### Context
The platform needs a single source of truth for all ML experiments, model versions, artifacts, and promotion workflows. Multiple off-the-shelf and built solutions exist.

### Decision
Use MLflow as the central ML lifecycle platform. MLflow Tracking records all experiment parameters, metrics, and artifacts. MLflow Model Registry manages model versioning, stage transitions (Staging → Production → Archived), and aliases. Artifact store backed by Azure Blob Storage.

### Consequences
- **Positive:** Industry-standard ML lifecycle tool with broad community support
- **Positive:** Model Registry API for programmatic promotion and rollback
- **Positive:** Native integration with PyTorch, Scikit-learn, XGBoost
- **Negative:** Additional infrastructure to manage (MLflow server, artifact store)

---

## ADR-004: Temporal + n8n Dual Orchestration

**Status:** Accepted
**Date:** 2026-06-01

### Context
The platform requires both durable, long-running ML workflows (retraining, data refresh) and rapid, automation-oriented care coordination workflows (notifications, appointment scheduling).

### Decision
Use two orchestration engines:
1. **Temporal** for long-running, stateful workflows that require durability, retries, and compensation (model retraining, monitoring adherence workflows that run for 30 days)
2. **n8n** for rapid, event-driven automations that involve external integrations (email, SMS, calendar) where a visual editor improves maintainability

### Consequences
- **Positive:** Temporal provides unlimited durability and exactly-once execution guarantees
- **Positive:** n8n provides 300+ native connectors and a visual workflow editor
- **Positive:** Clear separation of concerns (durable vs. automation)
- **Negative:** Operational complexity of two orchestration systems
- **Negative:** Integration layer needed to bridge Temporal and n8n

---

## ADR-005: SHAP for Model Explainability over LIME

**Status:** Accepted
**Date:** 2026-06-01

### Context
The platform must provide clinically meaningful explanations for every prediction. LIME, SHAP, and permutation importance were evaluated.

### Decision
Use SHAP (SHapley Additive exPlanations) for all model explainability. SHAP provides:
- Game-theoretic foundation with guaranteed properties (consistency, local accuracy)
- Model-agnostic, works with all four model types
- Global and local explanations
- Rich visualization capabilities (waterfall, summary, force plots)

### Consequences
- **Positive:** Mathematically rigorous explanations with convergence guarantees
- **Positive:** Consistent across model types, enabling fair comparison
- **Positive:** Rich visualization library with D3/React integration
- **Negative:** SHAP computation is O(2^N) for exact solution (KernelSHAP approximation used)
- **Negative:** ~200ms overhead per prediction for TreeSHAP

---

## ADR-006: LLM as Strict Decision Support Layer

**Status:** Accepted
**Date:** 2026-06-01

### Context
Large Language Models can generate convincing but incorrect medical statements. Using an LLM to predict readmission risk would introduce hallucination risk, regulatory liability, and opacity.

### Decision
Azure OpenAI is used **exclusively** for translating structured model outputs into clinician-friendly natural language explanations. The LLM:
- Never receives raw patient data without PHI stripping
- Never generates a risk score
- Never provides a diagnosis
- Always includes the regulatory disclaimer
- Output is validated post-generation for safety constraints

### Consequences
- **Positive:** LLM capabilities augment, not replace, the ML model
- **Positive:** Clear regulatory boundary (decision support, not clinical decision making)
- **Positive:** Output validation prevents hallucination propagation
- **Negative:** Additional latency (~1-3s per explanation)
- **Negative:** Azure OpenAI cost per explanation (~$0.001-0.003)

---

## ADR-007: Feature Pipeline as Versioned Artifact

**Status:** Accepted
**Date:** 2026-06-01

### Context
Training and inference must use identical feature transformations. Feature drift between training and inference is a common source of ML production failures.

### Decision
Encapsulate the entire feature engineering pipeline as a single versioned `sklearn.Pipeline` object. The pipeline is:
1. Fitted during training
2. Serialized with `joblib`
3. Registered as an MLflow artifact under `artifacts/pipeline-v{version}.pkl`
4. Loaded by the prediction service at startup
5. Versioned independently from the model (enables feature changes without retraining)

### Consequences
- **Positive:** Training/inference parity guaranteed by design
- **Positive:** Pipeline versioning decouples feature changes from model changes
- **Positive:** Simple rollback (revert pipeline + model together)
- **Negative:** Pipeline size (~500KB) loaded into memory

---

## ADR-008: PostgreSQL over Specialized Feature Store

**Status:** Accepted
**Date:** 2026-06-01

### Context
Feature stores like Feast or Tecton add operational complexity. For the current scale (~100K patients), a shared PostgreSQL schema with materialized views is sufficient.

### Decision
Use PostgreSQL for both the OLTP database and a lightweight feature store. Features are precomputed via materialized views refreshed on data ingestion. If scale exceeds PostgreSQL capabilities, migrate to Azure Cosmos DB for PostgreSQL (Citus) with horizontal sharding.

### Consequences
- **Positive:** Single database technology reduces operational burden
- **Positive:** ACID transactions for consistency between features and labels
- **Positive:** PostgreSQL materialized views for efficient feature computation
- **Negative:** Not optimized for ML feature serving at very large scale (>10M patients)

---

## ADR-009: Docker Compose for Local Development

**Status:** Accepted
**Date:** 2026-06-01

### Context
Developers need a consistent local environment that mirrors production. Configuration drift is a common source of "works on my machine" bugs.

### Decision
Use Docker Compose to orchestrate all services locally. Each service runs in its own container. `docker-compose.yml` defines all services, networks, volumes, and dependencies. Health checks ensure correct startup order. Production uses Azure Container Apps with a similar topology.

### Consequences
- **Positive:** Identical environment for all developers
- **Positive:** CI/CD pipeline uses same Docker images
- **Positive:** Easy onboarding (one command to start all services)
- **Negative:** Resource-intensive on developer machines (8GB+ RAM recommended)

---

## ADR-010: GitHub Actions for CI/CD

**Status:** Accepted
**Date:** 2026-06-01

### Context
The platform requires automated testing, linting, and deployment for every commit. Self-hosted runners add maintenance overhead.

### Decision
Use GitHub Actions for the entire CI/CD pipeline:
- **CI:** Triggered on every PR: lint, type-check, unit tests, integration tests, build, container image
- **CD:** Triggered on merge to main: deploy staging, run smoke tests, promote to production on approval
- **Scheduled:** Weekly re-training pipeline, monthly vulnerability scan

### Consequences
- **Positive:** Tight GitHub integration with PR status checks
- **Positive:** Free for public repositories, generous minutes for private
- **Positive:** Matrix builds for parallel testing (Python 3.11, 3.12)
- **Negative:** 6-hour execution limit per workflow
- **Negative:** Self-hosted runner needed if GPU training is required in CI

---

## ADR-011: JWT with RS256 over Session-Based Auth

**Status:** Accepted
**Date:** 2026-06-01

### Context
Stateless authentication is required for horizontally scaled services. Any instance must be able to validate a token without shared session storage.

### Decision
Use JWT with RS256 (RSA signature) asymmetric signing. The private key signs tokens (auth service only), and the public key is distributed to all services for verification. Access tokens expire in 15 minutes; refresh tokens (HTTP-only secure cookies) expire in 7 days.

### Consequences
- **Positive:** Stateless — any service instance can verify tokens without DB lookup
- **Positive:** Asymmetric keys — public key can be safely distributed
- **Positive:** Standard library support (PyJWT, jose)
- **Negative:** Token revocation requires a blacklist (Redis set of revoked JWT IDs)
- **Negative:** Larger token size than session cookies (~1KB)

---

## ADR-012: Partitioned Audit Logs and Predictions

**Status:** Accepted
**Date:** 2026-06-01

### Context
Audit logs and prediction records grow rapidly (estimated 50M and 10M rows/year respectively). Query performance degrades without a strategy.

### Decision
Range-partition both tables by month on their timestamp columns. Use PostgreSQL native partitioning (declarative partitioning). Partition pruning ensures queries with time-range filters scan only relevant partitions. Old partitions are archived to cold storage after 12 months.

### Consequences
- **Positive:** Query performance remains constant as data grows (for time-bound queries)
- **Positive:** Efficient data archival and purging (drop entire partitions)
- **Positive:** Parallel partition scans for analytics queries
- **Negative:** Schema migration complexity (partition maintenance)
- **Negative:** Cross-partition queries slower than unpartitioned tables

---

## ADR-013: Dependency Inversion for All Third-Party Integrations

**Status:** Accepted
**Date:** 2026-07-20
**Supersedes:** ADR-003 (MLflow abstraction), ADR-005 (SHAP wrapper), ADR-006 (LLM provider), ADR-008 (Feature Store)

### Context
The architecture directly depends on vendor-specific SDKs (MLflow, Azure OpenAI, etc.), creating vendor lock-in. Replacing any vendor requires changes across multiple services. Testing requires vendor SDK mocking, which couples tests to vendor behavior.

### Decision
Every third-party integration is hidden behind a Python `Protocol` (interface) defined in a shared `interfaces` module. Business logic imports only the protocol. Implementation classes live in `adapters/` subdirectories. Dependency injection in each service's `container.py` wires implementations at startup based on configuration.

**Interfaces defined:**
- `FeatureStoreProtocol` — Feature storage/retrieval (implementations: PostgreSQL, Feast, Redis)
- `ModelRegistryProtocol` — Model versioning and promotion (implementations: MLflow, S3, GCS)
- `LLMProviderProtocol` — Natural language explanation generation (implementations: Azure OpenAI, OpenAI, Anthropic, TemplateFallback)
- `MessageQueueProtocol` — Async event publishing (implementations: Redis PubSub, RabbitMQ, SQS)
- `NotificationProviderProtocol` — Multi-channel notification delivery (implementations: SMTP, Twilio, SendGrid, Slack)
- `ObjectStorageProtocol` — Blob storage for artifacts (implementations: Azure Blob, S3, GCS)

### Consequences
- **Positive:** Any vendor can be replaced by implementing the protocol — zero business logic changes
- **Positive:** Testing: mock protocols directly without vendor SDKs
- **Positive:** Multiple implementations can coexist (primary + fallback + circuit breaker)
- **Positive:** Circuit breaker pattern wraps any provider protocol automatically
- **Negative:** One extra abstraction layer per integration
- **Negative:** Interface design must be right the first time (costly to change protocols consumers depend on)

### Updated ADR Status
- ADR-003 (MLflow) → MLflow implements `ModelRegistryProtocol`
- ADR-005 (SHAP) → SHAP wrapped in `ShapExplainer` implementing `ExplainerProtocol`
- ADR-006 (Azure OpenAI) → Azure OpenAI is one implementation of `LLMProviderProtocol`
- ADR-008 (PostgreSQL Feature Store) → PostgreSQL is one implementation of `FeatureStoreProtocol`

---

## ADR-014: Formal Model Promotion Gate

**Status:** Accepted
**Date:** 2026-07-20

### Context
Previously, model promotion from staging to production was a single-step manual or automatic operation. This lacks governance: no enforcement of fairness checks, data validation, regression testing, or manual approval as prerequisites for production deployment.

### Decision
Implement a formal 12-condition promotion gate that a model version must pass before it can be promoted to production. The gate is enforced at the API and CI levels. Promotion is rejected unless ALL conditions pass.

**Mandatory Conditions:**
1. F1 Score ≥ 0.80
2. ROC-AUC ≥ 0.85
3. PR-AUC ≥ 0.70
4. Brier Score ≤ 0.15
5. Calibration error < 0.05
6. Fairness: ΔF1 across subgroups ≤ 0.03
7. No data leakage (temporal holdout matches random split within 0.03)
8. Feature importance stability (Jaccard similarity ≥ 0.6 with production)
9. Regression tests pass (CI green)
10. Data validation passes (Great Expectations)
11. Inference latency acceptable (≤ 2× current production)
12. Manual approval recorded (audit log entry)

After conditions pass, the model enters a 7-day shadow run. Only after the shadow run confirms performance matching production is the model promoted.

### Consequences
- **Positive:** Governed, auditable promotion process with clear criteria
- **Positive:** Prevents underperforming, biased, or unvalidated models from reaching production
- **Positive:** Shadow run provides real-world validation before cutover
- **Negative:** Promotion delay (~7 days for shadow run)
- **Negative:** More complex promotion pipeline (CI + manual step)

---

## ADR-015: Batch and Dual-Path Inference

**Status:** Accepted
**Date:** 2026-07-20

### Context
The architecture initially supported only real-time, per-patient prediction. Batch prediction for cohort scoring (e.g., daily risk assessment) requires a separate path with different performance characteristics and cost optimization.

### Decision
Support two distinct inference modes:
1. **Real-Time:** Triggered by clinician action. Single patient. Includes SHAP + LLM + workflow. Latency target: < 3s.
2. **Batch:** Scheduled (daily, 02:00 UTC). Cohort of 100-1000 patients. Precomputed features + vectorized SHAP. LLM and workflow only for high-risk patients. Results available via batch status API.

Both paths share the same model registry, feature pipeline, and evaluation infrastructure.

### Consequences
- **Positive:** Clinicians get instant results; population health gets daily cohort scoring
- **Positive:** Batch path amortizes compute (vectorized SHAP: 90% per-patient cost reduction)
- **Positive:** Shared infrastructure reduces maintenance burden
- **Negative:** Two code paths to maintain
- **Negative:** Batch results are stale by up to 24 hours

---

## ADR-016: Graceful Degradation and Fallback Architecture

**Status:** Accepted
**Date:** 2026-07-20

### Context
The platform depends on multiple external services (Azure OpenAI, MLflow, PostgreSQL, Redis, n8n, Temporal). Any single dependency failure could cascade into a full platform outage without fallback strategies.

### Decision
Every external dependency has a documented graceful degradation strategy with three tiers:
1. **Retry** — Transient failure recovery with exponential backoff
2. **Fallback** — Alternative code path when the primary is unavailable (e.g., template-based LLM, local model cache, local feature cache)
3. **Dead-Letter** — Structured failure handling when all retries and fallbacks are exhausted

Circuit breaker patterns wrap all external providers. Detection, fallback, recovery, alerting, and metrics are documented for every dependency in the Failure Handling Matrix (see `ENTERPRISE_REVIEW.md §6.1`).

### Consequences
- **Positive:** No single dependency failure causes a full platform outage
- **Positive:** Predictable degraded behavior (documented, tested)
- **Positive:** Circuit breakers prevent cascading failures
- **Negative:** Additional complexity in every service (fallback code paths)
- **Negative:** Stale data served during fallback mode (documented)