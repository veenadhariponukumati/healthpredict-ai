# Experiment Tracking Design

## MLflow Configuration

### MLflow Server

```yaml
# mlflow/docker-compose.mlflow.yml
version: '3.9'
services:
  mlflow:
    build:
      context: .
      dockerfile: Dockerfile
    ports: ["5000:5000"]
    environment:
      MLFLOW_TRACKING_URI: postgresql://app:dev_password@postgres:5432/readmission
      MLFLOW_ARTIFACT_ROOT: /mlflow/artifacts
      MLFLOW_S3_ENDPOINT_URL: ""  # Use Azure Blob in production
    volumes:
      - mlflow_artifacts:/mlflow/artifacts
    command: >
      mlflow server
      --backend-store-uri postgresql://app:dev_password@postgres:5432/readmission
      --default-artifact-root /mlflow/artifacts
      --host 0.0.0.0
      --port 5000
```

### MLflow Dockerfile

```dockerfile
FROM python:3.12-slim

RUN pip install mlflow==2.13.0 psycopg2-binary boto3 azure-storage-blob

EXPOSE 5000

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
```

## Experiment Structure

### Experiment Naming Convention

```
readmission-{model_type}-v{major_version}
```

Examples:
- `readmission-logistic_regression-v1`
- `readmission-random_forest-v2`
- `readmission-xgboost-v3`
- `readmission-pytorch_nn-v3`

### Experiment Tags

```python
mlflow.set_experiment_tag("project", "clinical-readmission")
mlflow.set_experiment_tag("team", "ml-engineering")
mlflow.set_experiment_tag("dataset_version", "v2.3")
mlflow.set_experiment_tag("pipeline_version", "v1.2")
mlflow.set_experiment_tag("target", "readmission_30day")
mlflow.set_experiment_tag("environment", "development")  # development | staging | production
```

## Run Structure

### Parameters Logged

```python
# All hyperparameters
mlflow.log_params({
    "model_type": "xgboost",
    "learning_rate": 0.05,
    "max_depth": 6,
    "n_estimators": 300,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "gamma": 0.1,
    "reg_alpha": 0.01,
    "reg_lambda": 1.0,
    "min_child_weight": 1,
    "scale_pos_weight": 2.5,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "random_state": 42,
    "cross_validation_folds": 5,
    "test_split": 0.15,
    "train_samples": 29400,
    "val_samples": 6300,
    "test_samples": 6300,
    "n_features": 44,
    "pipeline_version": "2.3.1",
    "dataset_hash": "sha256:a1b2c3d4..."
})
```

### Metrics Logged

```python
# Primary metrics
mlflow.log_metrics({
    "accuracy": 0.87,
    "precision": 0.82,
    "recall": 0.88,
    "f1_score": 0.845,
    "roc_auc": 0.912,
    "pr_auc": 0.785,
    "brier_score": 0.112,
    "log_loss": 0.315,
    "cross_val_mean_f1": 0.838,
    "cross_val_std_f1": 0.012,
    "training_duration_seconds": 845,
    "inference_latency_ms": 42,
    "model_size_mb": 18.5
})

# Per-class metrics
mlflow.log_metrics({
    "positive_class_f1": 0.82,
    "negative_class_f1": 0.91,
    "macro_f1": 0.865,
    "weighted_f1": 0.845
})

# Threshold metrics
for threshold in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
    mlflow.log_metrics({
        f"precision_at_{threshold}": precision_values[threshold],
        f"recall_at_{threshold}": recall_values[threshold],
        f"f1_at_{threshold}": f1_values[threshold]
    })
```

### Artifacts Logged

```python
# Model artifacts
mlflow.log_artifact("models/xgboost_model.pkl", artifact_path="model")
mlflow.log_artifact("models/preprocessor.pkl", artifact_path="pipeline")
mlflow.log_artifact("models/feature_names.json", artifact_path="metadata")

# Evaluation artifacts
mlflow.log_artifact("evaluation/confusion_matrix.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/roc_curve.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/pr_curve.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/calibration_curve.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/learning_curves.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/validation_curves.png", artifact_path="evaluation")
mlflow.log_artifact("evaluation/classification_report.json", artifact_path="evaluation")

# SHAP artifacts
mlflow.log_artifact("explainability/shap_summary_plot.png", artifact_path="explainability")
mlflow.log_artifact("explainability/shap_feature_importance.csv", artifact_path="explainability")
mlflow.log_artifact("explainability/shap_base_value.json", artifact_path="explainability")

# Data artifacts
mlflow.log_artifact("data/train_indices.npy", artifact_path="data")
mlflow.log_artifact("data/val_indices.npy", artifact_path="data")
mlflow.log_artifact("data/test_indices.npy", artifact_path="data")
mlflow.log_artifact("data/dataset_metadata.json", artifact_path="data")
```

## Dataset Tracking

```python
from mlflow.data.pandas_dataset import PandasDataset

# Create dataset object
dataset = mlflow.data.from_pandas(
    df=features_df,
    source="synthetic_mimic_v2.3",
    name="readmission_dataset_v2.3",
    targets="readmitted_30day"
)

# Log dataset
mlflow.log_input(dataset, context="training")

# In the run context
dataset_hash = hashlib.sha256(
    features_df.to_json().encode()
).hexdigest()
mlflow.log_param("dataset_hash", dataset_hash)
```

## Model Registry

### Registration

```python
# Register model after training
mlflow.register_model(
    model_uri=f"runs:/{run.info.run_id}/model",
    name="readmission-predictor"
)

# Or with sklearn flavor
mlflow.sklearn.log_model(
    sk_model=best_model,
    artifact_path="model",
    registered_model_name="readmission-predictor",
    signature=infer_signature(X_train, y_train),
    input_example=X_train[:5],
    code_paths=["src/"]
)
```

### Model Version Tags

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Tag model version
client.set_model_version_tag(
    name="readmission-predictor",
    version="3.2.1",
    key="validation_status",
    value="passed"
)

client.set_model_version_tag(
    name="readmission-predictor",
    version="3.2.1",
    key="f1_score",
    value="0.845"
)

client.set_model_version_tag(
    name="readmission-predictor",
    version="3.2.1",
    key="approved_by",
    value="ml-engineering-team"
)
```

### Stage Transitions

```python
# Transition to Staging (automatic after training)
client.transition_model_version_stage(
    name="readmission-predictor",
    version="3.2.1",
    stage="Staging"
)

# Transition to Production (after manual review)
client.transition_model_version_stage(
    name="readmission-predictor",
    version="3.2.1",
    stage="Production"
)

# Archive previous production model
client.transition_model_version_stage(
    name="readmission-predictor",
    version="3.1.0",
    stage="Archived"
)
```

### Production Alias

```python
# Set production alias for easy reference
client.set_registered_model_alias(
    name="readmission-predictor",
    alias="production",
    version="3.2.1"
)

# Load by alias
model = mlflow.pyfunc.load_model(
    model_uri="models:/readmission-predictor@production"
)
```

## Model Comparison (within a run)

```python
# Track all models in a single comparison run
with mlflow.start_run(run_name="model_comparison_v3"):
    models = {
        "logistic_regression": {"f1": 0.742, "roc_auc": 0.821, "latency_ms": 2},
        "random_forest": {"f1": 0.811, "roc_auc": 0.889, "latency_ms": 65},
        "xgboost": {"f1": 0.845, "roc_auc": 0.912, "latency_ms": 42},
        "pytorch_nn": {"f1": 0.802, "roc_auc": 0.876, "latency_ms": 38}
    }

    for model_name, metrics in models.items():
        for metric_name, value in metrics.items():
            mlflow.log_metric(f"{model_name}_{metric_name}", value)

    # Log comparison artifact
    mlflow.log_artifact("evaluation/model_comparison_table.csv")
    mlflow.log_artifact("evaluation/model_comparison_radar.png")
    mlflow.log_artifact("evaluation/model_comparison_parallel_coords.png")
```

## Reproducibility

### Seed Management

```python
import random
import numpy as np
import torch

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

# XGBoost seed
params = {
    "random_state": SEED,
    "seed": SEED,
}

# MLflow tracks the seed
mlflow.log_param("random_seed", SEED)
```

### Environment Capture

```python
# Log environment info
mlflow.log_param("python_version", sys.version)
mlflow.log_param("mlflow_version", mlflow.__version__)
mlflow.log_param("pytorch_version", torch.__version__)
mlflow.log_param("sklearn_version", sklearn.__version__)
mlflow.log_param("xgboost_version", xgboost.__version__)

# Log pip requirements
mlflow.log_artifact("requirements.txt")
```

## Querying Experiments

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Search for best model
best_runs = client.search_runs(
    experiment_ids=["42"],
    filter_string="metrics.f1_score > 0.80",
    order_by=["metrics.f1_score DESC"],
    max_results=5
)

# Compare runs
runs = client.search_runs(
    experiment_ids=["42"],
    order_by=["metrics.roc_auc DESC"]
)

for run in runs:
    print(f"Run {run.info.run_id}: F1={run.data.metrics['f1_score']:.3f}, "
          f"ROC-AUC={run.data.metrics['roc_auc']:.3f}")
```