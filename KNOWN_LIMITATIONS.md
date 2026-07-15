# Known Limitations

This list contains only limitations that have been directly observed and verified during local testing and clean-room installation validation. It does not speculate about issues that have not been reproduced.

## Installation / Documentation

1. **`backend/scripts/verify-local.sh` fails on machines without a native `pg_isready` binary.** Its first check runs `pg_isready` against the host rather than against the `postgres` Docker container, so it fails immediately on a fresh machine even when Postgres is running correctly inside Docker. This script is a convenience tool, not a required install step - the platform installs and runs correctly without it. Workaround: check container health directly instead, e.g. `docker compose -f backend/docker-compose.local.yml ps` or `docker exec <postgres-container> pg_isready`.

2. **`frontend/.env.local` is not included in the packaged release.** Only `NEXT_PUBLIC_API_URL` is needed, and `frontend/src/services/api.ts` falls back to `http://localhost:8000` if the file is absent, so this has no functional impact when running the backend locally on the default port. Create the file yourself (see `frontend/INTEGRATION_README.md`) only if you need to point the frontend at a non-default API URL.

## Application Behavior

3. **n8n workflow actions are simulated, not real integrations.** Temporal genuinely orchestrates the care-coordination workflow (real state machine, real durability/retries), and n8n genuinely receives and processes each webhook call over HTTP - that part is real. But the final action each n8n workflow performs (`patient-reminder`, `care-team-notification`, `notify-care-team`, `create-appointment`, `follow-up-appointment-request`) returns a hardcoded mock response - a fake phone number (`+1-555-0000`), a fake care-team email, or a fake scheduled appointment/department - instead of actually sending an SMS/email or booking a real appointment through a scheduling system. No real notification or appointment booking happens today. Verified by inspecting all 6 files in `backend/n8n/workflows/*.json` - no Twilio/SMS-provider node, no email-provider node, and no outbound HTTP call to any real external messaging/scheduling API exists in any workflow definition.

4. **Workflow triggering has no UI entry point.** The prediction detail page does not expose a "Trigger Workflow" action - `POST /api/v1/workflows/trigger` is reachable only via direct API call today.

5. **`n8n` and `temporal-worker` Docker healthchecks are cosmetically wrong.** Both containers report "unhealthy" in `docker ps` despite functioning correctly; this is a healthcheck configuration issue, not a functional defect.

6. **Auth rate limiting (10 requests/minute) can affect rapid repeated test runs.** The Playwright suite uses 4 real logins per run (well under the limit), but running the suite back-to-back multiple times within the same minute can still trip the limit.

7. **Prediction detail page shows raw patient UUIDs rather than patient names** in some list views - a cosmetic gap, not a functional defect.

## Deployment

8. **The Azure deployment path described in `docs/DEPLOYMENT_GUIDE.md` is a design document, not working infrastructure.** There is no `.github/workflows/` directory, no `.bicep`/`.terraform` files, and no frontend `Dockerfile` anywhere in this repository - the Bicep/GitHub Actions snippets in that guide are illustrative code blocks only. The only deployment path that has actually been built and verified is local Docker Compose (backend) + `npm run dev`/`npm run build` (frontend).

9. **MLflow, the LLM Service (Azure OpenAI), the Training Service, and Redis are designed and scaffolded in code but are not part of the verified local stack.** `backend/docker-compose.local.yml` - the compose file that has actually been built and clean-room validated - runs exactly 8 containers (`postgres`, `api`, `prediction`, `workflow`, `n8n`, `temporal`, `temporal-ui`, `temporal-worker`) and includes none of these four. There is no `MLFLOW_TRACKING_URI` or `AZURE_OPENAI_*` configuration anywhere in `backend/.env.example`. Concretely: the prediction service loads its model from a bundled file rather than an MLflow model registry (see item below), and the rate-limiting middleware is an in-memory implementation (`backend/app/middleware/rate_limit.py`) rather than Redis-backed, even though `REDIS_URL`/`REDIS_ENABLED` exist as config values. A second, unused compose file (`backend/docker-compose.yml`) does define `mlflow`, `training-service`, `llm-service`, and `redis` services, but it is not referenced by any of the documented startup scripts and has not been verified to work.

## Not a Limitation (for clarity)

- The prediction model's fallback loading (bundled model file, reported as `model_version: "bundled-dev"` when no MLflow-provisioned model is present) is intentional graceful-degradation behavior, not a bug.
- Automatic Alembic migrations, demo-user seeding, and n8n workflow import/activation all happen automatically via container entrypoints on first boot - no manual steps are required.
