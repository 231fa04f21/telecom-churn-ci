from pathlib import Path
import argparse
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIFT_DIR = PROJECT_ROOT / "drift"
SOURCE = PROJECT_ROOT / "telecom_churn.csv"
REFERENCE = DRIFT_DIR / "reference_data.csv"
OUTPUT_CURRENT = DRIFT_DIR / "current_data.csv"
OUTPUT_LABELED = DRIFT_DIR / "current_labeled_data.csv"

FEATURES = [
    "age",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used",
]
TARGET = "churn"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode",
    choices=["stable", "drift"],
    default="stable",
)
args = parser.parse_args()

df = pd.read_csv(SOURCE)
n = min(1000, len(df))
sample = df.sample(n=n, replace=False, random_state=42).reset_index(drop=True)

current_features = sample[FEATURES].copy()
current_labeled = sample[FEATURES + [TARGET]].copy()

if args.mode == "drift":
    # Demographic & behavioral shifts in recent customer cohort:
    # Older age profile, reduced calls, increased data usage, lower estimated salary
    current_features["age"] = (current_features["age"] + 18).clip(18, 90)
    current_features["calls_made"] = (current_features["calls_made"] * 0.4).round().astype(int)
    current_features["data_used"] = (current_features["data_used"] * 1.8).round(2)
    current_features["estimated_salary"] = (current_features["estimated_salary"] * 0.7).round(2)

    current_labeled["age"] = (current_labeled["age"] + 18).clip(18, 90)
    current_labeled["calls_made"] = (current_labeled["calls_made"] * 0.4).round().astype(int)
    current_labeled["data_used"] = (current_labeled["data_used"] * 1.8).round(2)
    current_labeled["estimated_salary"] = (current_labeled["estimated_salary"] * 0.7).round(2)
    # Labeled batch reflects higher churn propensity among disengaged customers
    current_labeled[TARGET] = np.where(
        (current_labeled["age"] > 55) | (current_labeled["calls_made"] < 20),
        1,
        sample[TARGET],
    )

# Save unlabelled inputs for drift detection
current_features.to_csv(OUTPUT_CURRENT, index=False)
# Save labeled records for supervised retraining
current_labeled.to_csv(OUTPUT_LABELED, index=False)

print("Mode:", args.mode)
print("Rows:", len(current_features))
print("Current Data File   :", OUTPUT_CURRENT)
print("Current Labeled File:", OUTPUT_LABELED)
