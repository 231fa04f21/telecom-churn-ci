from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIFT_DIR = PROJECT_ROOT / "drift"

HISTORICAL = PROJECT_ROOT / "telecom_churn.csv"
RECENT = DRIFT_DIR / "current_labeled_data.csv"
DRIFT_REPORT = DRIFT_DIR / "drift_report.json"
CANDIDATE_MODEL = DRIFT_DIR / "telecom_churn_model_candidate.pkl"
METRICS_FILE = DRIFT_DIR / "retraining_metrics.json"

FEATURES = [
    "age",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used",
]
TARGET = "churn"

with open(DRIFT_REPORT, encoding="utf-8") as f:
    drift_report = json.load(f)

if not drift_report["overall_drift"]:
    print("No overall drift detected.")
    print("Retraining skipped.")
    raise SystemExit(0)

if not RECENT.exists():
    raise FileNotFoundError(
        "Drift was detected, but current_labeled_data.csv is not available."
    )

historical = pd.read_csv(HISTORICAL)
recent = pd.read_csv(RECENT)

required = FEATURES + [TARGET]
for name, frame in [("historical", historical), ("recent", recent)]:
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"{name} data missing columns: {missing}")

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
accuracy = accuracy_score(y_test, predictions)

joblib.dump(candidate, CANDIDATE_MODEL)

metrics = {
    "candidate_accuracy": round(float(accuracy), 6),
    "training_rows": int(len(X_train)),
    "test_rows": int(len(X_test)),
    "historical_rows": int(len(historical)),
    "recent_labeled_rows": int(len(recent)),
}

with open(METRICS_FILE, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
print("Candidate model:", CANDIDATE_MODEL)

