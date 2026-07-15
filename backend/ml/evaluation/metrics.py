"""Model evaluation metrics and comparison framework."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    auc,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute the complete set of evaluation metrics.

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted class labels (after threshold).
        y_prob: Predicted probabilities for positive class.
        threshold: Classification threshold used.

    Returns:
        Dictionary with all metrics.
    """
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "threshold": threshold,
        "n_samples": int(len(y_true)),
        "n_positive": int(y_true.sum()),
        "n_negative": int((1 - y_true).sum()),
    }

    # PR-AUC
    precision_vals, recall_vals, _ = precision_recall_curve(y_true, y_prob)
    metrics["pr_auc"] = float(auc(recall_vals, precision_vals))

    return metrics


def compute_confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, int]:
    """Compute confusion matrix values."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def compute_calibration(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> dict[str, Any]:
    """Compute calibration curve and ECE."""
    prob_true, prob_pred = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="uniform"
    )

    ece = float(np.mean(np.abs(prob_true - prob_pred)))
    max_calibration_error = float(np.max(np.abs(prob_true - prob_pred)))

    return {
        "expected_calibration_error": ece,
        "max_calibration_error": max_calibration_error,
        "bins": [
            {
                "bin_pred": float(prob_pred[i]),
                "bin_true": float(prob_true[i]),
            }
            for i in range(len(prob_pred))
        ],
    }


def find_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_recall: float = 0.85,
) -> dict[str, Any]:
    """Find the optimal classification threshold.

    Maximizes F1 while maintaining a minimum recall constraint.

    Args:
        y_true: Ground truth labels.
        y_prob: Predicted probabilities.
        min_recall: Minimum acceptable recall.

    Returns:
        Dict with threshold and metrics at that threshold.
    """
    thresholds = np.linspace(0.05, 0.95, 91)
    best_f1 = 0.0
    best_threshold = 0.35
    best_metrics: dict[str, float] = {}

    for threshold in thresholds:
        y_pred = (y_prob >= threshold).astype(int)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        if recall >= min_recall and f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = {
                "threshold": float(threshold),
                "f1": float(f1),
                "recall": float(recall),
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            }

    logger.info(
        "optimal_threshold_found",
        threshold=best_threshold,
        f1=best_f1,
    )

    return {
        "optimal_threshold": float(best_threshold),
        "best_f1": float(best_f1),
        "metrics_at_threshold": best_metrics,
    }


def compute_weighted_score(metrics: dict[str, float]) -> float:
    """Compute the weighted model comparison score.

    Formula (from the architecture ADR):
        0.35 * normalized(F1)
        + 0.25 * normalized(ROC-AUC)
        + 0.15 * normalized(PR-AUC)
        - 0.10 * normalized(Brier)
        - 0.10 * normalized(latency)
        - 0.05 * normalized(model_size_mb)
    """
    # Normalize to 0-1 range (approximate)
    f1_score_val = metrics["f1_score"]
    roc_auc = metrics["roc_auc"]
    pr_auc = metrics.get("pr_auc", 0.7)
    brier = 1.0 - metrics.get("brier_score", 0.15)  # Invert so lower is better
    latency = 1.0 - min(
        metrics.get("inference_latency_ms", 50) / 200, 1.0
    )
    model_size = 1.0 - min(
        metrics.get("model_size_mb", 20) / 100, 1.0
    )

    score = (
        0.35 * f1_score_val
        + 0.25 * roc_auc
        + 0.15 * pr_auc
        + 0.10 * brier
        + 0.10 * latency
        + 0.05 * model_size
    )

    return float(score)


def compare_models(
    model_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare multiple models and select the best one.

    Args:
        model_results: List of dicts, each with model_name, metrics, latency, size.

    Returns:
        Dict with comparison results and best model selection.
    """
    for result in model_results:
        result["weighted_score"] = compute_weighted_score(result["metrics"])

    # Sort by weighted score descending
    model_results.sort(key=lambda x: x["weighted_score"], reverse=True)

    best = model_results[0]

    logger.info(
        "model_comparison_complete",
        best_model=best["model_name"],
        best_score=best["weighted_score"],
        scores={
            r["model_name"]: r["weighted_score"]
            for r in model_results
        },
    )

    return {
        "best_model": best["model_name"],
        "best_model_type": best["model_type"],
        "best_weighted_score": best["weighted_score"],
        "comparison": [
            {
                "model_name": r["model_name"],
                "model_type": r["model_type"],
                "weighted_score": r["weighted_score"],
                "metrics": r["metrics"],
                "inference_latency_ms": r.get("inference_latency_ms"),
                "model_size_mb": r.get("model_size_mb"),
            }
            for r in model_results
        ],
    }