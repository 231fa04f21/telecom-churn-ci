"""
Telecom Churn MLOps - Data Drift & Retraining Core Service
Encapsulates statistical drift testing, simulation, candidate retraining, and quality gate logic.
"""

from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIFT_DIR = PROJECT_ROOT / "drift"

SOURCE = PROJECT_ROOT / "telecom_churn.csv"
REFERENCE = DRIFT_DIR / "reference_data.csv"
CURRENT = DRIFT_DIR / "current_data.csv"
CURRENT_LABELED = DRIFT_DIR / "current_labeled_data.csv"
DRIFT_REPORT = DRIFT_DIR / "drift_report.json"
CANDIDATE_MODEL = DRIFT_DIR / "telecom_churn_model_candidate.pkl"
RETRAINING_METRICS = DRIFT_DIR / "retraining_metrics.json"
PROD_MODEL = PROJECT_ROOT / "telecom_churn_model.pkl"

FEATURES = [
    "age",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used",
]
TARGET = "churn"
P_VALUE_THRESHOLD = 0.05
MIN_DRIFTED_FEATURES = 2
MIN_ACCURACY = 0.50


def ensure_reference():
    """Generates the reference dataset if missing."""
    DRIFT_DIR.mkdir(parents=True, exist_ok=True)
    if not REFERENCE.exists():
        df = pd.read_csv(SOURCE)
        ref = df[FEATURES].dropna().copy()
        ref.to_csv(REFERENCE, index=False)
        return len(ref)
    return len(pd.read_csv(REFERENCE))


def simulate_data(mode="stable"):
    """Simulates recent unlabelled and labeled production data batches."""
    DRIFT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_reference()

    df = pd.read_csv(SOURCE)
    n = min(1000, len(df))
    sample = df.sample(n=n, replace=False, random_state=42).reset_index(drop=True)

    current_features = sample[FEATURES].copy()
    current_labeled = sample[FEATURES + [TARGET]].copy()

    if mode == "drift":
        # Simulate cohort shifts
        current_features["age"] = (current_features["age"] + 18).clip(18, 90)
        current_features["calls_made"] = (current_features["calls_made"] * 0.4).round().astype(int)
        current_features["data_used"] = (current_features["data_used"] * 1.8).round(2)
        current_features["estimated_salary"] = (current_features["estimated_salary"] * 0.7).round(2)

        current_labeled["age"] = (current_labeled["age"] + 18).clip(18, 90)
        current_labeled["calls_made"] = (current_labeled["calls_made"] * 0.4).round().astype(int)
        current_labeled["data_used"] = (current_labeled["data_used"] * 1.8).round(2)
        current_labeled["estimated_salary"] = (current_labeled["estimated_salary"] * 0.7).round(2)
        current_labeled[TARGET] = np.where(
            (current_labeled["age"] > 55) | (current_labeled["calls_made"] < 20),
            1,
            sample[TARGET],
        )

    current_features.to_csv(CURRENT, index=False)
    current_labeled.to_csv(CURRENT_LABELED, index=False)

    return {
        "mode": mode,
        "rows": len(current_features),
        "features_path": str(CURRENT),
        "labeled_path": str(CURRENT_LABELED),
    }


def detect_drift():
    """Runs two-sample KS hypothesis test and saves drift_report.json."""
    ensure_reference()
    if not CURRENT.exists():
        simulate_data(mode="stable")

    reference = pd.read_csv(REFERENCE)
    current = pd.read_csv(CURRENT)

    results = {}
    drifted_features = []

    for feature in FEATURES:
        ref_values = reference[feature].dropna()
        cur_values = current[feature].dropna()
        statistic, p_value = ks_2samp(ref_values, cur_values)
        drift_detected = bool(p_value < P_VALUE_THRESHOLD)

        results[feature] = {
            "ks_statistic": round(float(statistic), 6),
            "p_value": round(float(p_value), 6),
            "drift_detected": drift_detected,
            "reference_mean": round(float(ref_values.mean()), 4),
            "current_mean": round(float(cur_values.mean()), 4),
        }

        if drift_detected:
            drifted_features.append(feature)

    overall_drift = bool(len(drifted_features) >= MIN_DRIFTED_FEATURES)

    report = {
        "method": "two-sample KS test",
        "p_value_threshold": P_VALUE_THRESHOLD,
        "min_drifted_features": MIN_DRIFTED_FEATURES,
        "drifted_feature_count": len(drifted_features),
        "drifted_features": drifted_features,
        "overall_drift": overall_drift,
        "features": results,
    }

    with open(DRIFT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def retrain_candidate():
    """Retrains candidate model if overall drift is detected and labeled data exists."""
    if not DRIFT_REPORT.exists():
        detect_drift()

    with open(DRIFT_REPORT, encoding="utf-8") as f:
        drift_report = json.load(f)

    if not drift_report.get("overall_drift", False):
        return {
            "status": "skipped",
            "message": "No overall drift detected. Retraining skipped.",
            "overall_drift": False,
        }

    if not CURRENT_LABELED.exists():
        raise FileNotFoundError(
            "Drift detected, but current_labeled_data.csv is missing."
        )

    historical = pd.read_csv(SOURCE)
    recent = pd.read_csv(CURRENT_LABELED)

    required = FEATURES + [TARGET]
    combined = pd.concat(
        [historical[required], recent[required]],
        ignore_index=True,
    ).dropna(subset=[TARGET])

    X = combined[FEATURES]
    y = combined[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    candidate = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
    ])

    candidate.fit(X_train, y_train)
    predictions = candidate.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))

    joblib.dump(candidate, CANDIDATE_MODEL)

    metrics = {
        "status": "trained",
        "candidate_accuracy": round(accuracy, 6),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "historical_rows": int(len(historical)),
        "recent_labeled_rows": int(len(recent)),
        "candidate_model_path": str(CANDIDATE_MODEL),
    }

    with open(RETRAINING_METRICS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


def approve_candidate(min_accuracy=MIN_ACCURACY):
    """Applies quality gate to candidate model and promotes to production if passed."""
    if not RETRAINING_METRICS.exists() or not CANDIDATE_MODEL.exists():
        return {
            "status": "failed",
            "message": "No candidate model or metrics found. Run retrain first.",
            "promoted": False,
        }

    with open(RETRAINING_METRICS, encoding="utf-8") as f:
        metrics = json.load(f)

    accuracy = metrics.get("candidate_accuracy", 0.0)
    passed = bool(accuracy >= min_accuracy)

    if not passed:
        return {
            "status": "quality_gate_failed",
            "candidate_accuracy": accuracy,
            "required_accuracy": min_accuracy,
            "message": f"Candidate accuracy {accuracy} is below threshold {min_accuracy}. Current model unchanged.",
            "promoted": False,
        }

    shutil.copy2(CANDIDATE_MODEL, PROD_MODEL)

    return {
        "status": "quality_gate_passed",
        "candidate_accuracy": accuracy,
        "required_accuracy": min_accuracy,
        "message": f"Quality Gate PASSED. Candidate promoted to {PROD_MODEL.name}.",
        "promoted": True,
    }
