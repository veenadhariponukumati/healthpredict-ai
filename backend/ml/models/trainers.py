"""Model training implementations for all 4 candidate architectures.

Each model follows the same interface:
    - fit(X_train, y_train, X_val, y_val) -> self
    - predict(X) -> np.ndarray (class labels)
    - predict_proba(X) -> np.ndarray (probabilities)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import optuna
from optuna.trial import Trial
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score

from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseModel(ABC):
    """Abstract base for all model implementations."""

    def __init__(self, name: str, model_type: str) -> None:
        self.name = name
        self.model_type = model_type
        self._model: Any = None
        self._best_params: dict[str, Any] = {}
        self._feature_importance: dict[str, float] = {}

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs: Any,
    ) -> "BaseModel":
        """Train the model."""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        ...

    @abstractmethod
    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 30,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run hyperparameter optimization and return best params."""
        ...

    @property
    def model(self) -> Any:
        return self._model

    @property
    def best_params(self) -> dict[str, Any]:
        return self._best_params

    @property
    def feature_importance(self) -> dict[str, float]:
        return self._feature_importance

    def get_model_size_mb(self) -> float:
        """Estimate model size in memory."""
        import sys

        if self._model is None:
            return 0.0
        return sys.getsizeof(self._model) / (1024 * 1024)


class LogisticRegressionModel(BaseModel):
    """Logistic Regression with L2 regularization and Optuna HPO."""

    def __init__(self) -> None:
        super().__init__(
            name="logistic_regression",
            model_type="logistic_regression",
        )

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs: Any,
    ) -> "LogisticRegressionModel":
        params = kwargs.get("params", {})
        self._model = LogisticRegression(
            C=params.get("C", 1.0),
            penalty=params.get("penalty", "l2"),
            solver=params.get("solver", "lbfgs"),
            max_iter=params.get("max_iter", 1000),
            class_weight=params.get("class_weight", "balanced"),
            random_state=params.get("random_state", 42),
            n_jobs=-1,
        )
        self._model.fit(X_train, y_train)

        # Feature importance from coefficients
        if hasattr(self._model, "coef_"):
            coef = np.abs(self._model.coef_[0])
            self._feature_importance = {
                f"feature_{i}": float(coef[i])
                for i in range(len(coef))
            }

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict_proba(X)

    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 24,
        seed: int = 42,
    ) -> dict[str, Any]:
        def objective(trial: Trial) -> float:
            params = {
                "C": trial.suggest_float("C", 0.01, 10.0, log=True),
                "penalty": trial.suggest_categorical("penalty", ["l2"]),
                "solver": trial.suggest_categorical("solver", ["lbfgs", "saga"]),
                "max_iter": trial.suggest_int("max_iter", 500, 2000, step=500),
            }
            self.fit(X_train, y_train, params=params)
            y_pred = self.predict(X_val)
            return float(f1_score(y_val, y_pred))

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=seed),
        )
        study.optimize(objective, n_trials=n_trials)

        self._best_params = study.best_params
        logger.info(
            "lr_hpo_complete",
            best_f1=study.best_value,
            best_params=self._best_params,
        )
        return self._best_params


class RandomForestModel(BaseModel):
    """Random Forest with Optuna HPO."""

    def __init__(self) -> None:
        super().__init__(
            name="random_forest",
            model_type="random_forest",
        )

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs: Any,
    ) -> "RandomForestModel":
        params = kwargs.get("params", {})
        self._model = RandomForestClassifier(
            n_estimators=params.get("n_estimators", 200),
            max_depth=params.get("max_depth", 10),
            min_samples_split=params.get("min_samples_split", 2),
            min_samples_leaf=params.get("min_samples_leaf", 1),
            max_features=params.get("max_features", "sqrt"),
            class_weight=params.get("class_weight", "balanced"),
            random_state=params.get("random_state", 42),
            n_jobs=-1,
        )
        self._model.fit(X_train, y_train)

        # Feature importance
        if hasattr(self._model, "feature_importances_"):
            self._feature_importance = {
                f"feature_{i}": float(self._model.feature_importances_[i])
                for i in range(len(self._model.feature_importances_))
            }

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict_proba(X)

    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 50,
        seed: int = 42,
    ) -> dict[str, Any]:
        def objective(trial: Trial) -> float:
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
                "max_depth": trial.suggest_int("max_depth", 3, 20),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                "max_features": trial.suggest_categorical(
                    "max_features", ["sqrt", "log2", None]
                ),
            }
            self.fit(X_train, y_train, params=params)
            y_pred = self.predict(X_val)
            return float(f1_score(y_val, y_pred))

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=seed),
        )
        study.optimize(objective, n_trials=n_trials)

        self._best_params = study.best_params
        logger.info(
            "rf_hpo_complete",
            best_f1=study.best_value,
            best_params=self._best_params,
        )
        return self._best_params


class XGBoostModel(BaseModel):
    """XGBoost with Optuna HPO."""

    def __init__(self) -> None:
        super().__init__(
            name="xgboost",
            model_type="xgboost",
        )

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs: Any,
    ) -> "XGBoostModel":
        import xgboost as xgb

        params = kwargs.get("params", {})
        eval_set = None
        if X_val is not None and y_val is not None:
            eval_set = [(X_train, y_train), (X_val, y_val)]

        self._model = xgb.XGBClassifier(
            learning_rate=params.get("learning_rate", 0.05),
            max_depth=params.get("max_depth", 6),
            n_estimators=params.get("n_estimators", 300),
            subsample=params.get("subsample", 0.8),
            colsample_bytree=params.get("colsample_bytree", 0.7),
            gamma=params.get("gamma", 0.1),
            reg_alpha=params.get("reg_alpha", 0.01),
            reg_lambda=params.get("reg_lambda", 1.0),
            min_child_weight=params.get("min_child_weight", 1),
            scale_pos_weight=params.get("scale_pos_weight", 2.5),
            objective="binary:logistic",
            eval_metric="auc",
            early_stopping_rounds=params.get("early_stopping_rounds", 50),
            random_state=params.get("random_state", 42),
            n_jobs=-1,
            verbosity=0,
        )

        self._model.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            verbose=False,
        )

        # Feature importance
        if hasattr(self._model, "feature_importances_"):
            self._feature_importance = {
                f"feature_{i}": float(self._model.feature_importances_[i])
                for i in range(len(self._model.feature_importances_))
            }

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted")
        return self._model.predict_proba(X)

    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 80,
        seed: int = 42,
    ) -> dict[str, Any]:
        def objective(trial: Trial) -> float:
            params = {
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree", 0.5, 1.0
                ),
                "gamma": trial.suggest_float("gamma", 0.0, 5.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "early_stopping_rounds": 50,
            }
            self.fit(X_train, y_train, X_val, y_val, params=params)
            y_pred = self.predict(X_val)
            return float(f1_score(y_val, y_pred))

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=seed),
            pruner=optuna.pruners.MedianPruner(),
        )
        study.optimize(objective, n_trials=n_trials)

        self._best_params = study.best_params
        logger.info(
            "xgb_hpo_complete",
            best_f1=study.best_value,
            best_params=self._best_params,
        )
        return self._best_params


class PyTorchNNModel(BaseModel):
    """PyTorch Feedforward Neural Network with Optuna HPO."""

    def __init__(self) -> None:
        super().__init__(
            name="pytorch_nn",
            model_type="pytorch_nn",
        )
        self._input_dim: int = 0

    def _build_network(
        self, input_dim: int, hidden_dims: list[int], dropout: float
    ) -> Any:
        """Build a PyTorch feedforward network."""
        import torch.nn as nn

        layers: list[nn.Module] = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, 1))
        layers.append(nn.Sigmoid())

        return nn.Sequential(*layers)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs: Any,
    ) -> "PyTorchNNModel":
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, TensorDataset

        params = kwargs.get("params", {})

        # Set seed for reproducibility
        torch.manual_seed(params.get("random_state", 42))

        self._input_dim = X_train.shape[1]
        hidden_dims = params.get(
            "hidden_dims", [256, 128, 64]
        )
        dropout = params.get("dropout", 0.3)
        learning_rate = params.get("learning_rate", 0.001)
        batch_size = params.get("batch_size", 64)
        weight_decay = params.get("weight_decay", 1e-4)
        n_epochs = params.get("n_epochs", 100)
        patience = params.get("patience", 10)

        self._model = self._build_network(
            self._input_dim, hidden_dims, dropout
        )

        criterion = nn.BCELoss()
        optimizer = optim.Adam(
            self._model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )

        # Data loaders
        train_dataset = TensorDataset(
            torch.tensor(X_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32).view(-1, 1),
        )
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True
        )

        val_loader = None
        if X_val is not None and y_val is not None:
            val_dataset = TensorDataset(
                torch.tensor(X_val, dtype=torch.float32),
                torch.tensor(y_val, dtype=torch.float32).view(-1, 1),
            )
            val_loader = DataLoader(val_dataset, batch_size=batch_size)

        # Training loop with early stopping
        best_val_loss = float("inf")
        epochs_no_improve = 0
        best_state: Any = None

        for epoch in range(n_epochs):
            # Training
            self._model.train()
            train_loss = 0.0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                outputs = self._model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            # Validation
            if val_loader:
                self._model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for X_batch, y_batch in val_loader:
                        outputs = self._model(X_batch)
                        loss = criterion(outputs, y_batch)
                        val_loss += loss.item()

                scheduler.step(val_loss)

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    epochs_no_improve = 0
                    best_state = self._model.state_dict()
                else:
                    epochs_no_improve += 1

                if epochs_no_improve >= patience:
                    logger.info(
                        "pytorch_early_stopping",
                        epoch=epoch,
                        best_val_loss=best_val_loss,
                    )
                    break
            else:
                scheduler.step(train_loss)

        # Restore best state
        if best_state is not None:
            self._model.load_state_dict(best_state)

        # Feature importance approximation using weights
        if hasattr(self._model[0], "weight"):
            weights = self._model[0].weight.data.numpy()
            importance = np.abs(weights).mean(axis=0)
            self._feature_importance = {
                f"feature_{i}": float(importance[i])
                for i in range(len(importance))
            }

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        import torch

        if self._model is None:
            raise RuntimeError("Model not fitted")
        self._model.eval()
        with torch.no_grad():
            proba = self._model(torch.tensor(X, dtype=torch.float32)).numpy()
        return (proba >= 0.5).astype(int).flatten()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        import torch

        if self._model is None:
            raise RuntimeError("Model not fitted")
        self._model.eval()
        with torch.no_grad():
            proba = self._model(torch.tensor(X, dtype=torch.float32)).numpy()
        # Return [1-p, p] format consistent with sklearn
        return np.column_stack([1 - proba.flatten(), proba.flatten()])

    def optimize_hyperparameters(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 60,
        seed: int = 42,
    ) -> dict[str, Any]:
        def objective(trial: Trial) -> float:
            n_layers = trial.suggest_int("n_layers", 1, 4)
            hidden_dims = []
            prev_dim = X_train.shape[1]
            for i in range(n_layers):
                dim = trial.suggest_int(
                    f"hidden_dim_{i}", 32, 512, log=True
                )
                hidden_dims.append(dim)

            params = {
                "hidden_dims": hidden_dims,
                "dropout": trial.suggest_float("dropout", 0.1, 0.5),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 1e-5, 1e-2, log=True
                ),
                "batch_size": trial.suggest_categorical(
                    "batch_size", [32, 64, 128, 256]
                ),
                "weight_decay": trial.suggest_float(
                    "weight_decay", 1e-6, 1e-3, log=True
                ),
                "n_epochs": 100,
                "patience": 10,
                "random_state": seed,
            }
            self.fit(X_train, y_train, X_val, y_val, params=params)
            y_pred = self.predict(X_val)
            return float(f1_score(y_val, y_pred))

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=seed),
            pruner=optuna.pruners.MedianPruner(),
        )
        study.optimize(objective, n_trials=n_trials)

        self._best_params = study.best_params
        logger.info(
            "pytorch_hpo_complete",
            best_f1=study.best_value,
            best_params=self._best_params,
        )
        return self._best_params