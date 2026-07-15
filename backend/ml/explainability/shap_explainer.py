"""SHAP explainability module for model interpretation."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class ShapExplainer:
    """SHAP-based model explainer.

    Provides local and global feature importance explanations.
    Wraps the SHAP library behind an interface that's consistent
    across all 4 model types.
    """

    def __init__(self, model: Any, feature_names: list[str]) -> None:
        self.model = model
        self.feature_names = feature_names
        self._explainer: Any = None
        self._global_shap_values: Any = None

    def _get_explainer(self, background_data: np.ndarray | None = None) -> Any:
        """Create the appropriate SHAP explainer for the model type."""
        import shap

        model_type = type(self.model).__module__

        if "xgboost" in model_type or "sklearn" in model_type:
            # TreeExplainer for tree-based models (XGBoost, Random Forest)
            try:
                return shap.TreeExplainer(self.model)
            except Exception as exc:
                logger.warning("tree_explainer_failed", error=str(exc))
                # Fall through to KernelSHAP below

        # KernelSHAP as fallback for any model type
        return shap.KernelExplainer(
            self.model.predict_proba,
            background_data or np.random.randn(100, len(self.feature_names)),
        )

    def compute_global(
        self, X: np.ndarray, n_samples: int = 500
    ) -> dict[str, Any]:
        """Compute global SHAP values across a dataset.

        Args:
            X: Feature matrix.
            n_samples: Number of samples to use (subsampled for speed).

        Returns:
            Dict with mean_abs_shap values per feature, ranked.
        """
        import shap

        if len(X) > n_samples:
            idx = np.random.choice(len(X), n_samples, replace=False)
            X_sample = X[idx]
        else:
            X_sample = X

        self._explainer = self._get_explainer(X_sample)

        logger.info("computing_global_shap", n_samples=X_sample.shape[0])
        self._global_shap_values = self._explainer.shap_values(X_sample)

        # Handle 3D array (sklearn returns [n_samples, n_features, n_classes])
        if isinstance(self._global_shap_values, list):
            shap_vals = self._global_shap_values[1]  # Positive class
        elif self._global_shap_values.ndim == 3:
            shap_vals = self._global_shap_values[:, :, 1]
        else:
            shap_vals = self._global_shap_values

        mean_abs_shap = np.abs(shap_vals).mean(axis=0)

        # Rank features by importance
        feature_importance = {}
        for i, name in enumerate(self.feature_names):
            if i < len(mean_abs_shap):
                feature_importance[name] = float(mean_abs_shap[i])

        ranked = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        logger.info("global_shap_computed", n_features=len(ranked))

        return {
            "feature_importance": dict(ranked),
            "top_features": [
                {"feature": name, "shap_value": value}
                for name, value in ranked[:10]
            ],
            "base_value": float(
                self._explainer.expected_value
                if isinstance(self._explainer.expected_value, (int, float))
                else self._explainer.expected_value[1]
            ),
        }

    def compute_local(
        self, X_row: np.ndarray, feature_names: list[str] | None = None
    ) -> dict[str, Any]:
        """Compute local SHAP values for a single prediction.

        Args:
            X_row: Single feature vector (1D or 2D array).
            feature_names: Optional feature names (overrides instance names).

        Returns:
            Dict with per-feature SHAP values, base value, and top features.
        """
        import shap

        names = feature_names or self.feature_names

        if X_row.ndim == 1:
            X_row = X_row.reshape(1, -1)

        if self._explainer is None:
            self._explainer = self._get_explainer()

        shap_values = self._explainer.shap_values(X_row)

        # Handle different output shapes
        if isinstance(shap_values, list):
            vals = shap_values[1][0]
        elif shap_values.ndim == 3:
            vals = shap_values[0, :, 1]
        else:
            vals = shap_values[0]

        # Build per-feature explanations
        features = {}
        for i, name in enumerate(names):
            if i < len(vals):
                features[name] = {
                    "value": float(X_row[0, i]) if X_row.shape[1] > i else 0.0,
                    "shap_value": float(vals[i]),
                    "contribution": (
                        "increases_risk" if vals[i] > 0 else "decreases_risk"
                    ),
                }

        # Get base value
        expected = self._explainer.expected_value
        base_value = float(
            expected if isinstance(expected, (int, float)) else expected[1]
        )

        # Rank by absolute SHAP value
        ranked = sorted(
            features.items(),
            key=lambda x: abs(x[1]["shap_value"]),
            reverse=True,
        )

        return {
            "shap_values": {name: vals["shap_value"] for name, vals in features.items()},
            "features": features,
            "base_value": base_value,
            "top_features": [
                {
                    "feature": name,
                    "value": vals["value"],
                    "shap_value": vals["shap_value"],
                    "contribution": vals["contribution"],
                }
                for name, vals in ranked[:5]
            ],
            "computation_time_ms": 0,  # Set by caller
        }