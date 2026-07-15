# Frontend Integration Package

## Location
`frontend/` inside the project root:
```
release_v2_extracted/healthcare-platform-release/frontend/
```

## Required Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

Only one variable is needed. Already created as `.env.local`.

## Startup Commands

### 1. Start Backend (Docker)
```bash
cd backend
docker compose -f docker-compose.local.yml up -d --build
```
This starts: postgres (5432), API (8000), prediction service, workflow service, Temporal (7233), n8n (5678).

### 2. Seed Database (auto on startup)
Default users are created automatically:
- `admin@test.com` / `Test123!` (role: admin)
- `clinician@test.com` / `Test123!` (role: clinician)
- `viewer@test.com` / `Test123!` (role: viewer)

### 3. Start Frontend
```bash
cd frontend
npm install    # if not already done
npm run dev    # http://localhost:3000
```

### 4. Run E2E Tests
```bash
cd frontend
npx playwright install chromium
npx playwright test
```

## Docker Instructions
The frontend is NOT added to docker-compose.local.yml — it runs standalone on port 3000. To add it:
1. Add a `frontend` service in docker-compose.local.yml
2. The existing `api` service on port 8000 serves as the backend

## Playwright Test Location
`frontend/e2e/healthcare.spec.ts`

## Files Added or Modified

### Modified (API contract fixes):
- `frontend/src/types/api.ts` — Updated `DashboardSummary`, `WorkflowStats`, `PredictionDetail` to match real backend
- `frontend/src/services/api.ts` — Rewritten with correct types; `getStats` now returns `WorkflowStats`, `getDashboard` now returns `DashboardSummary`
- `frontend/src/app/dashboard/page.tsx` — Removed obsolete fields (`total_patients`, `high_risk_count`, `active_workflows`, `completed_workflows`, `failed_workflows`, `low_risk_count`, `workflow_completion_rate`). Uses actual backend fields: `total_predictions`, `high_risk`, `critical`, `moderate`, `mean_risk_score`, `current_model`, `current_model_version`
- `frontend/src/app/predictions/[id]/page.tsx` — Replaced `shap_explanation.top_features` with `shap_values` (sorted by absolute value, top 10). Raw SHAP values grid reads directly from `shap_values` dict
- `frontend/src/app/workflows/page.tsx` — Replaced `stats.active` with `stats.running`. Added `retrying` and `escalated` to chart. `completion_rate` now computed as ratio of completed/total

### Added:
- `frontend/.env.local` — `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `frontend/e2e/healthcare.spec.ts` — 11 Playwright E2E tests
- `frontend/INTEGRATION_README.md` — This file

## Known Limitations

1. **No E2E browser execution yet**
   Playwright tests are defined but NOT executed — requires both backend Docker and frontend running simultaneously, plus a browser environment.

2. **Tests are not yet installed**
   Playwright and its dependencies need to be installed:
   ```bash
   cd frontend
   npm install -D @playwright/test
   npx playwright install chromium
   ```

3. **Dashboard Risk Distribution PieChart** uses a simplified label (name + count) instead of percentage because the Recharts `PieLabel` type does not guarantee `percent` is defined on the label render props.

## Future Improvements

1. Add a docker-compose service for the frontend
2. Run Playwright tests against real backend
3. Add console-error detection in E2E tests (no console errors, no hydration warnings)
4. Add authentication redirect regression test (no infinite redirect loops)
5. Add test for token expiry → auto-refresh flow

## Verification Status

| Check | Status |
|-------|--------|
| Build compiles | ✅ |
| TypeScript errors | ✅ 0 errors |
| API client matches backend | ✅ Types updated |
| ENV variables documented | ✅ 1 variable |
| Frontend port | 3000 |
| Backend port | 8000 |
| Playwright tests created | ✅ 11 tests |
| Playwright tests executed | ❌ NOT VERIFIED |
| Browser quality check | ❌ NOT VERIFIED |
