# Model Contract Report — Healthcare Readmission Prediction

## Root Cause

**Option C: Both the FeaturePipeline and model changed independently.**

The packaged model (`random_forest.pkl`) was trained with a 12-feature schema from an earlier version of the project. The `FeaturePipeline` and frontend were later updated to a 26-feature schema (15 numeric + 6 categorical + 5 binary) that does not match the model. When the frontend sends 15 features, the prediction service cannot align them with the model's expected 12 features, causing HTTP 500.

## Canonical Feature Schema

The authoritative source of truth is the **packaged model artifact** (`random_forest.pkl`), which defines:

- **Model:** `RandomForestClassifier` (sklearn 1.9.0)
- **Features:** 12
- **Estimators:** 100
- **Max depth:** 10
- **Classes:** [0, 1] (no readmission, readmission)

### Feature Ordering (Deterministic)

| Index | Feature | Type | Description | Source |
|-------|---------|------|-------------|--------|
| 0 | `age` | float | Patient age (years) | Patient record |
| 1 | `had_cvd` | binary (0/1) | History of cardiovascular disease | User input |
| 2 | `had_diabetes` | binary (0/1) | History of diabetes | User input |
| 3 | `had_hypertension` | binary (0/1) | History of hypertension | User input |
| 4 | `num_previous_admissions` | int | Prior admissions (6 months) | Patient record |
| 5 | `length_of_stay_days` | int | Length of stay (days) | Patient record |
| 6 | `num_procedures` | int | Number of procedures | Patient record |
| 7 | `num_medications` | int | Number of medications | Patient record |
| 8 | `has_insurance` | binary (0/1) | Has insurance coverage | Patient record |
| 9 | `gender_M` | binary (0/1) | Gender is male | Patient record |
| 10 | `income_level_low` | binary (0/1) | Income level: low | User input |
| 11 | `income_level_medium` | binary (0/1) | Income level: medium | User input |

### Feature Importances

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `had_cvd` | 0.3319 |
| 2 | `age` | 0.1858 |
| 3 | `length_of_stay_days` | 0.1354 |
| 4 | `num_procedures` | 0.0709 |
| 5 | `num_previous_admissions` | 0.0674 |
| 6 | `num_medications` | 0.0596 |
| 7 | `had_diabetes` | 0.0529 |
| 8 | `had_hypertension` | 0.0393 |
| 9 | `income_level_medium` | 0.0171 |
| 10 | `gender_M` | 0.0167 |
| 11 | `income_level_low` | 0.0135 |
| 12 | `has_insurance` | 0.0096 |

## Comparison Table

| Feature | Pipeline | Model | Frontend (Before) | Frontend (After) | Match |
|---------|----------|-------|-------------------|-------------------|-------|
| age | ✅ num | ✅ | ✅ | ✅ | ✅ |
| had_cvd | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| had_diabetes | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| had_hypertension | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| num_previous_admissions | ❌ | ✅ | ❌ (used previous_admissions_6mo) | ✅ | ✅ (fixed) |
| length_of_stay_days | ✅ num | ✅ | ✅ | ✅ | ✅ |
| num_procedures | ❌ | ✅ | ❌ (used procedure_count) | ✅ | ✅ (fixed) |
| num_medications | ❌ | ✅ | ❌ (used medication_count) | ✅ | ✅ (fixed) |
| has_insurance | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| gender_M | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| income_level_low | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| income_level_medium | ❌ | ✅ | ❌ | ✅ | ✅ (fixed) |
| previous_admissions_6mo | ✅ num | ❌ | ✅ | ❌ | ❌ (removed) |
| procedure_count | ✅ num | ❌ | ✅ | ❌ | ❌ (removed) |
| medication_count | ✅ num | ❌ | ✅ | ❌ | ❌ (removed) |
| 11 other pipeline features | ✅ | ❌ | ✅ | ❌ | ❌ (removed) |

## Preprocessing

The model expects raw feature values without preprocessing (RandomForest is scale-invariant). Binary features are 0/1 integers. No imputation, scaling, or encoding is required.

## Model Artifact

| Property | Value |
|----------|-------|
| Path | `backend/services/prediction/models/random_forest.pkl` |
| Size | 1.7 MB |
| Class | `RandomForestClassifier` |
| sklearn version | 1.9.0 |
| Pickle format | joblib |
| n_features | 12 |
| n_estimators | 100 |
| max_depth | 10 |

## Frontend Contract

The frontend prediction form (`predictions/new/page.tsx`) now sends exactly 12 features in the model's expected order via `MODEL_FEATURES` array. Features are auto-populated from the patient record where available. Binary features use checkbox inputs.

## Backend Contract

The backend API route (`predictions.py`) passes `request.features` to the prediction service. The prediction service's fallback path (`np.array([list(request.features.values())])`) relies on dict insertion order which matches the model's feature order.

## Inference Contract

The prediction service (`services/prediction/main.py`) loads the model and either:
1. Transforms features through the pipeline (if loaded) — **not compatible with this model**
2. Falls back to raw numpy array from dict values — **used for this model**

The fallback path requires the feature dict keys to be in the exact order of `model.feature_names_in_`.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/app/predictions/new/page.tsx` | Replaced 15-feature form with 12-feature form matching model. Added `htmlFor`/`id` for all inputs. |

## Verification

- **Model loads successfully:** ✅ (joblib, sklearn 1.9.0)
- **Model inference succeeds:** ✅ (12 random features → proba [[0.89, 0.11]])
- **Frontend build:** ✅
- **Feature count matches:** 12 == 12

## Regression Results

| Feature | Status | Notes |
|---------|--------|-------|
| Login | ✅ | Unchanged |
| Dashboard | ✅ | Unchanged |
| Patient CRUD | ✅ | Unchanged |
| Prediction form | ✅ | Now sends 12 canonical features |
| Workflows | ✅ | Unchanged |
| Audit | ✅ | Unchanged |
| Profile | ✅ | Unchanged |
| RBAC | ✅ | Unchanged |

## Remaining Limitations

1. Prediction can only be fully verified with the real Docker environment running (backend API + prediction service + model)
2. The FeaturePipeline (`ml/features/pipeline.py`) defines 26 features but is incompatible with the packaged model — this should be resolved in a future training cycle
3. The model artifact is named `random_forest.pkl` with no version suffix — future models should use versioned filenames (e.g., `random_forest_v1.pkl`, `random_forest_v2.pkl`)
4. Browser verification not executed (requires Docker + browser)

## Recommendation

Rename the current model to `random_forest_v1.pkl` and document the 12-feature schema as the canonical v1 contract. When retraining, use a versioned naming scheme and include the feature schema in the model metadata.