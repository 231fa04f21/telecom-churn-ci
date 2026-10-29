from pathlib import Path
import json
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIFT_DIR = PROJECT_ROOT / "drift"

CANDIDATE = DRIFT_DIR / "telecom_churn_model_candidate.pkl"
METRICS = DRIFT_DIR / "retraining_metrics.json"
APPROVED = PROJECT_ROOT / "telecom_churn_model.pkl"

MIN_ACCURACY = 0.50

with open(METRICS, encoding="utf-8") as f:
    metrics = json.load(f)

accuracy = metrics["candidate_accuracy"]
print("Candidate accuracy:", accuracy)
print("Required accuracy :", MIN_ACCURACY)

if accuracy < MIN_ACCURACY:
    print("QUALITY GATE: FAIL")
    print("Current approved model is unchanged.")
    raise SystemExit(1)

shutil.copy2(CANDIDATE, APPROVED)
print("QUALITY GATE: PASS")
print("Candidate promoted to:", APPROVED)

