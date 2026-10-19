"""Probability calibration for the career-group classifier."""
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CALIBRATION_METHOD = "temperature"
CALIBRATION_FOLDS = 5
CALIBRATION_RANDOM_STATE = 42


class TemperatureScaledClassifier(ClassifierMixin, BaseEstimator):
    """Scale classifier logits using a scalar learned from out-of-fold predictions."""

    def __init__(self, estimator, cv_folds=CALIBRATION_FOLDS, random_state=CALIBRATION_RANDOM_STATE):
        self.estimator = estimator
        self.cv_folds = cv_folds
        self.random_state = random_state

    @staticmethod
    def _decision_scores(estimator, X):
        decision_function = getattr(estimator, "decision_function", None)
        if callable(decision_function):
            scores = np.asarray(decision_function(X), dtype=float)
            if scores.ndim == 1:
                scores = np.column_stack((-scores, scores))
            return scores

        probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
        return np.log(np.clip(probabilities, 1e-12, 1.0))

    @staticmethod
    def _softmax(scores):
        shifted = scores - scores.max(axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        return exp_scores / exp_scores.sum(axis=1, keepdims=True)

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        cv = StratifiedKFold(
            n_splits=self.cv_folds,
            shuffle=True,
            random_state=self.random_state,
        )
        scores = cross_val_predict(
            clone(self.estimator), X, y, cv=cv, method="decision_function"
            if callable(getattr(self.estimator, "decision_function", None))
            else "predict_proba",
        )
        scores = np.asarray(scores, dtype=float)
        if scores.ndim == 1:
            scores = np.column_stack((-scores, scores))
        elif not callable(getattr(self.estimator, "decision_function", None)):
            scores = np.log(np.clip(scores, 1e-12, 1.0))

        target_indices = np.searchsorted(self.classes_, np.asarray(y))

        def objective(temperature):
            probabilities = self._softmax(scores / temperature)
            return log_loss(
                target_indices,
                probabilities,
                labels=np.arange(len(self.classes_)),
            )

        result = minimize_scalar(objective, bounds=(0.1, 5.0), method="bounded")
        if not result.success or not np.isfinite(result.x):
            raise RuntimeError("Không thể tối ưu nhiệt độ hiệu chuẩn xác suất.")
        self.temperature_ = float(result.x)
        self.estimator_ = clone(self.estimator).fit(X, y)
        self.classes_ = self.estimator_.classes_
        return self

    def predict_proba(self, X):
        scores = self._decision_scores(self.estimator_, X)
        return self._softmax(scores / self.temperature_)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def build_calibrated_pipeline(estimator) -> Pipeline:
    """Fit preprocessing inside each calibration fold to avoid feature leakage."""
    base_pipeline = Pipeline([
        ("preprocess", StandardScaler()),
        ("model", clone(estimator)),
    ])
    return Pipeline([("model", TemperatureScaledClassifier(base_pipeline))])


def get_base_estimator(pipeline):
    """Extract the underlying classifier from calibrated or legacy pipelines."""
    model = pipeline.named_steps["model"]
    if isinstance(model, TemperatureScaledClassifier):
        estimator = model.estimator
        if isinstance(estimator, Pipeline):
            return estimator.named_steps["model"]
        return estimator
    return model


def evaluate_probability_calibration(estimator, X, y, cv=None) -> dict:
    """Compare raw and calibrated out-of-fold probabilities against supplied labels."""
    if cv is None:
        cv = StratifiedKFold(
            n_splits=CALIBRATION_FOLDS,
            shuffle=True,
            random_state=CALIBRATION_RANDOM_STATE,
        )
    pipeline = build_calibrated_pipeline(estimator)
    probabilities = cross_val_predict(
        pipeline, X, y, cv=cv, method="predict_proba"
    )
    base_pipeline = Pipeline([
        ("preprocess", StandardScaler()),
        ("model", clone(estimator)),
    ])
    score_method = (
        "decision_function"
        if callable(getattr(estimator, "decision_function", None))
        else "predict_proba"
    )
    raw_scores = np.asarray(
        cross_val_predict(base_pipeline, X, y, cv=cv, method=score_method),
        dtype=float,
    )
    if score_method == "decision_function":
        if raw_scores.ndim == 1:
            raw_scores = np.column_stack((-raw_scores, raw_scores))
        raw_probabilities = TemperatureScaledClassifier._softmax(raw_scores)
    else:
        raw_probabilities = np.clip(raw_scores, 1e-12, 1.0)
        raw_probabilities /= raw_probabilities.sum(axis=1, keepdims=True)

    classes = np.unique(y)
    one_hot = (np.asarray(y)[:, None] == classes[None, :]).astype(float)

    def summarize(probabilities):
        predicted = classes[np.argmax(probabilities, axis=1)]
        correct = np.asarray(y) == predicted
        confidence = probabilities.max(axis=1)
        bin_edges = np.linspace(0.0, 1.0, 11)
        ece = 0.0
        for lower, upper in zip(bin_edges[:-1], bin_edges[1:]):
            in_bin = (confidence >= lower) & (
                (confidence <= upper) if upper == 1.0 else (confidence < upper)
            )
            if in_bin.any():
                ece += in_bin.mean() * abs(
                    correct[in_bin].mean() - confidence[in_bin].mean()
                )
        return {
            "brier_score": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
            "log_loss": float(log_loss(y, probabilities, labels=classes)),
            "expected_calibration_error": float(ece),
        }

    calibrated_metrics = summarize(probabilities)
    raw_metrics = summarize(raw_probabilities)
    return {
        "brier_score_cv": calibrated_metrics["brier_score"],
        "log_loss_cv": calibrated_metrics["log_loss"],
        "expected_calibration_error_cv": calibrated_metrics["expected_calibration_error"],
        "uncalibrated_brier_score_cv": raw_metrics["brier_score"],
        "uncalibrated_log_loss_cv": raw_metrics["log_loss"],
        "uncalibrated_expected_calibration_error_cv": raw_metrics["expected_calibration_error"],
        "calibration_target": "available_training_labels",
    }
