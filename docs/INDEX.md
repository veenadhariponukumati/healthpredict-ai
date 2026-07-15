# Clinical Readmission Prediction & AI Care Coordination Platform

## Complete Architecture Design Suite

This directory contains the full architecture, engineering design, and product specification for a production-grade AI/ML healthcare platform.

---

## Document Index

| # | Document | Size | Description |
|---|----------|------|-------------|
| 1 | [README.md](../README.md) | ~6.5K | Project overview, architecture diagram, technology stack, quick start |
| 2 | [docs/ARCHITECTURE.md](ARCHITECTURE.md) | ~33K | Complete system architecture: 7 service specs, 5 Mermaid diagrams, ML pipeline, observability, security, scalability |
| 3 | [docs/ENTERPRISE_REVIEW.md](ENTERPRISE_REVIEW.md) | ~58K | **Enterprise architecture review.** Technology abstraction (6 protocol interfaces), 12-condition promotion gate, rollback strategy, batch + real-time inference, continuous retraining, failure handling (7 dependency failure matrices), data governance, NFRs with measurable targets, cost optimization (7 strategies + $4K/month estimate), consistency review (15 findings resolved) |
| 4 | [docs/adr/README.md](adr/README.md) | ~17K | 16 Architecture Decision Records covering SOA, FastAPI, MLflow, Temporal+n8n, SHAP, LLM guardrails, dependency inversion, promotion gate, dual-path inference, graceful degradation |
| 5 | [docs/DATA_MODEL.md](DATA_MODEL.md) | ~15K | ER diagram, 8 full DDLs (users, patients, predictions, model_versions, experiments, workflow_events, audit_logs, feature_store), partitioning, indexing, data governance |
| 6 | [docs/API_SPECIFICATION.md](API_SPECIFICATION.md) | ~20K | 25+ endpoints across 8 groups, rate limits, error format, SDK generation |
| 7 | [docs/MODEL_CARD.md](MODEL_CARD.md) | ~10K | 4-model comparison, confusion matrix, threshold analysis, fairness, limitations |
| 8 | [docs/WORKFLOWS.md](WORKFLOWS.md) | ~12K | Temporal durable workflows, n8n automations, sequence diagrams, retry/escalation |
| 9 | [docs/DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | ~16K | Azure architecture, Docker Compose, CI/CD, Bicep, DR table, rollback procedures |
| 10 | [docs/EXPERIMENT_TRACKING.md](EXPERIMENT_TRACKING.md) | ~9K | MLflow config, run structure, registry transitions, reproducibility |
| 11 | [docs/TESTING_STRATEGY.md](TESTING_STRATEGY.md) | ~22K | 75/20/5 pyramid, unit/integration/ML/workflow/E2E tests, 90% coverage targets |
| 12 | [docs/DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) | ~12K | 6-step setup, project tree, key commands, troubleshooting |
| 13 | [docs/INDEX.md](INDEX.md) | ~6K | This index — document map, requirement coverage, architecture freeze |

---

## Enterprise Review Coverage

Every dimension from the review requirements is addressed:

| Dimension | Coverage Location | Key Artifacts |
|-----------|-------------------|---------------|
| **1. Technology Abstraction** | Review §1, ADR-013 | 6 Python Protocols, dependency injection container, adapter pattern |
| **2. Model Promotion Governance** | Review §2, ADR-014, Architecture §3.4 | 12 mandatory conditions, shadow run, audit trail, promotion API |
| **3. Rollback Strategy** | Review §3, Architecture §3.4 | 5 rollback triggers, automatic/ manual procedures, registry recovery, verification checklist |
| **4. Batch + Real-Time** | Review §4, ADR-015, API §3 | Dual flow diagrams, comparison table, batch API, 24h cohort scheduling |
| **5. Continuous Retraining** | Review §5, Architecture §1.3 | Automated lifecycle, scheduling, 6 approval checkpoints, rollback safety |
| **6. Failure Handling** | Review §6, ADR-016, Architecture §2.6 | 7 dependency failure matrices, circuit breaker config, retry policies, DLQ |
| **7. Data Governance** | Review §7, DATA_MODEL.md | Ownership, lineage, retention, deletion, access policies, compliance (HIPAA/GDPR/SOC2) |
| **8. Non-Functional Requirements** | Review §8, Architecture §7 | API latency breakdown, inference stage latency, workflow completion, availability SLA, RTO/RPO, scalability, storage projections |
| **9. Cost Optimization** | Review §9, Architecture §9 | Caching, batching, token monitoring, lifecycle policies, scaling, $4K/month estimate |
| **10. Consistency Review** | Review §10 | 15 cross-document conflicts resolved, diagram audit (16 verified/expanded), terminology standardization, 10 architectural invariants |

---

## Requirement Coverage

| Requirement | Documentation |
|-------------|---------------|
| Python 3.12 | All services |
| PyTorch | Training service, PyTorch NN model |
| FastAPI | API Gateway, all services |
| n8n | Workflows doc, Temporal + n8n dual orchestration |
| Temporal | Workflows doc, durable execution workflows |
| MLflow | Experiment tracking doc, model registry ADR, protocol abstraction |
| Docker / Docker Compose | Deployment guide, docker-compose.yml |
| PostgreSQL | Data model, 8 tables, partitioning, indexes |
| Azure OpenAI | LLM service, decision support only, protocol abstraction |
| Azure deployment | Deployment guide (Container Apps, Bicep, Key Vault) |
| GitHub Actions | CI/CD pipeline, test matrix, deployment automation |
| SHAP | Model card, explainability tests, SHAP explainer protocol |
| Pandas, NumPy, Scikit-learn | Feature engineering pipeline, all models |
| Logistic Regression, RF, XGBoost, PyTorch NN | All 4 trained and compared |
| Cross-val, HPO, early stopping | Training pipeline, Optuna, validation |
| Model comparison, auto-selection | Weighted scoring, comparison framework |
| RBAC, JWT, audit logs | Security architecture, audit_logs table |
| HIPAA-aware architecture | Encryption, RBAC, audit, synthetic data |
| 80%+ test coverage | Testing strategy (90% unit, 80% integration) |
| Mermaid diagrams | Architecture, sequence, ER, deployment, workflow, promotion |

---

## Architecture Freeze

As of **2026-07-20**, the architecture is **frozen**. All 16 ADRs, 13 documents, 10 enterprise review dimensions, and 15 consistency findings are resolved and documented.

**Total documentation:** ~241KB across 13 markdown files (272KB on disk including supporting files).

**Next phase:** Implementation — begin with protocol interface definitions, then adapter implementations, then business logic across all services.