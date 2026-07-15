"""Feature engineering pipeline.

Encapsulates the entire feature transformation pipeline as a versioned artifact.
Training and inference share the same pipeline to guarantee training/serving parity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

from app.core.logging import get_logger

logger = get_logger(__name__)

# Feature group definitions
NUMERIC_FEATURES = [
    "age",
    "previous_admissions_6mo",
    "length_of_stay_days",
    "icu_days",
    "procedure_count",
    "medication_count",
    "comorbidity_score",
    "discharge_bp_systolic",
    "discharge_hr",
    "discharge_spo2",
    "hemoglobin",
    "creatinine",
    "bnp",
    "sodium",
    "lab_abnormal_count",
]

CATEGORICAL_FEATURES = [
    "gender",
    "primary_diagnosis_group",
    "discharge_disposition",
    "insurance_type",
    "recent_surgery_flag",
    "high_risk_med_flag",
]

BINARY_FEATURES = [
    "has_heart_failure",
    "has_diabetes",
    "has_copd",
    "has_renal_disease",
    "has_cancer",
]


class FeaturePipeline:
    """Versioned feature engineering pipeline.

    Fitted during training, serialized with joblib, and loaded by the
    prediction service at startup. Versioned independently from the model.
    """

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version
        self._pipeline: Pipeline | None = None
        self._feature_names: list[str] = []
        self._fitted = False

    def build_pipeline(self) -> Pipeline:
        """Build the scikit-learn feature engineering pipeline."""
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", RobustScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
            ]
        )

        binary_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, NUMERIC_FEATURES),
                ("cat", categorical_transformer, CATEGORICAL_FEATURES),
                ("bin", binary_transformer, BINARY_FEATURES),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )

        return Pipeline(
            steps=[
                ("preprocessor", preprocessor),
            ]
        )

    def fit(self, df: pd.DataFrame) -> "FeaturePipeline":
        """Fit the pipeline on training data."""
        logger.info(
            "fitting_feature_pipeline",
            version=self.version,
            n_samples=len(df),
            n_features_raw=len(df.columns),
        )

        self._pipeline = self.build_pipeline()
        self._pipeline.fit(df)

        # Get output feature names
        self._feature_names = list(
            self._pipeline.named_steps["preprocessor"].get_feature_names_out()
        )
        self._fitted = True

        logger.info(
            "feature_pipeline_fitted",
            version=self.version,
            n_features_out=len(self._feature_names),
        )

        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform data using the fitted pipeline."""
        if not self._fitted or self._pipeline is None:
            raise RuntimeError("Pipeline must be fitted before transform")

        return self._pipeline.transform(df)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(df)
        return self.transform(df)

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    @property
    def n_features(self) -> int:
        return len(self._feature_names)

    def compute_dataset_hash(self, df: pd.DataFrame) -> str:
        """Compute SHA-256 hash of the dataset for reproducibility."""
        hash_str = df.to_json().encode()
        return hashlib.sha256(hash_str).hexdigest()

    def save(self, path: Path) -> None:
        """Serialize the pipeline to disk."""
        import joblib

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self._pipeline,
                "version": self.version,
                "feature_names": self._feature_names,
                "fitted": self._fitted,
            },
            path,
        )
        logger.info("feature_pipeline_saved", path=str(path), version=self.version)

    @classmethod
    def load(cls, path: Path) -> "FeaturePipeline":
        """Load a serialized pipeline from disk."""
        import joblib

        data = joblib.load(path)
        instance = cls(version=data["version"])
        instance._pipeline = data["pipeline"]
        instance._feature_names = data["feature_names"]
        instance._fitted = data["fitted"]
        logger.info("feature_pipeline_loaded", path=str(path), version=data["version"])
        return instance

    def get_feature_metadata(self) -> dict[str, Any]:
        """Return metadata about the pipeline for MLflow logging."""
        return {
            "pipeline_version": self.version,
            "n_features": self.n_features,
            "feature_names": self.feature_names,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "binary_features": BINARY_FEATURES,
        }


def generate_sample_patients(
    n_samples: int = 1000, seed: int = 42
) -> pd.DataFrame:
    """Generate synthetic patient data for development and testing.

    Uses realistic distributions based on MIMIC-derived statistics.
    """
    np.random.seed(seed)

    data = {
        "age": np.random.normal(62, 17, n_samples).clip(18, 95),
        "previous_admissions_6mo": np.random.poisson(1.5, n_samples).clip(0, 20),
        "length_of_stay_days": np.random.exponential(7, n_samples).clip(0, 120).astype(int),
        "icu_days": np.where(
            np.random.random(n_samples) < 0.3,
            np.random.exponential(3, n_samples).clip(0, 60).astype(int),
            0,
        ),
        "procedure_count": np.random.poisson(2, n_samples).clip(0, 15),
        "medication_count": np.random.poisson(5, n_samples).clip(0, 25),
        "comorbidity_score": np.random.gamma(4, 1.5, n_samples).clip(0, 40),
        "discharge_bp_systolic": np.random.normal(130, 18, n_samples).clip(80, 220),
        "discharge_hr": np.random.normal(78, 14, n_samples).clip(40, 140),
        "discharge_spo2": np.random.normal(96, 3, n_samples).clip(80, 100),
        "hemoglobin": np.random.normal(12.5, 2.5, n_samples).clip(6, 18),
        "creatinine": np.random.lognormal(0.2, 0.5, n_samples).clip(0.3, 10),
        "bnp": np.random.lognormal(5.5, 1.2, n_samples).clip(10, 5000),
        "sodium": np.random.normal(138, 4, n_samples).clip(120, 155),
        "lab_abnormal_count": np.random.poisson(1, n_samples).clip(0, 15),
        "gender": np.random.choice(["M", "F"], n_samples),
        "primary_diagnosis_group": np.random.choice(
            ["Cardiovascular", "Respiratory", "Endocrine", "Neurological",
             "Gastrointestinal", "Renal", "Oncological", "Orthopedic",
             "Infectious", "Other"],
            n_samples,
        ),
        "discharge_disposition": np.random.choice(
            ["Home", "Home_Health", "SNF", "Rehab", "Hospice", "AMA"],
            n_samples,
            p=[0.45, 0.20, 0.15, 0.10, 0.05, 0.05],
        ),
        "insurance_type": np.random.choice(
            ["Medicare", "Medicaid", "Private", "Self_Pay", "Other"],
            n_samples,
            p=[0.45, 0.20, 0.25, 0.05, 0.05],
        ),
        "recent_surgery_flag": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        "high_risk_med_flag": np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        "has_heart_failure": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "has_diabetes": np.random.choice([0, 1], n_samples, p=[0.75, 0.25]),
        "has_copd": np.random.choice([0, 1], n_samples, p=[0.85, 0.15]),
        "has_renal_disease": np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
        "has_cancer": np.random.choice([0, 1], n_samples, p=[0.92, 0.08]),
    }

    df = pd.DataFrame(data)

    # Generate target: readmission within 30 days (~21% positive rate)
    log_odds = (
        -3.5
        + 0.03 * df["age"]
        + 0.25 * np.log1p(df["previous_admissions_6mo"])
        + 0.04 * df["length_of_stay_days"]
        + 0.15 * df["comorbidity_score"]
        + 0.05 * df["lab_abnormal_count"]
        + 0.02 * df["medication_count"]
        + 0.5 * df["has_heart_failure"]
        + 0.3 * df["has_diabetes"]
        + 0.4 * df["high_risk_med_flag"]
        - 0.5 * (df["discharge_disposition"] == "Home").astype(int)
    )
    prob = 1 / (1 + np.exp(-log_odds))
    df["readmitted_30day"] = (np.random.random(n_samples) < prob).astype(int)

    # Add missing values (~5% rate)
    for col in NUMERIC_FEATURES[:5]:
        mask = np.random.random(n_samples) < 0.05
        df.loc[mask, col] = np.nan

    logger.info(
        "generated_sample_data",
        n_samples=n_samples,
        positive_rate=df["readmitted_30day"].mean(),
        n_features=len(df.columns) - 1,
    )

    return df