"""
ML Quality Gate for Telecom Customer Churn Model
Practical 3 - Implementing an ML Quality Gate using GitHub Actions
"""

import json
import sys

# Minimum acceptable accuracy threshold for deployment consideration
MINIMUM_ACCURACY = 0.90

print("Reading model evaluation metrics...")

try:
    with open("metrics.json", "r") as file:
        metrics = json.load(file)
except FileNotFoundError:
    print("ERROR: metrics.json not found. Run train_model.py first.")
    sys.exit(1)

accuracy = metrics.get("accuracy", 0.0)

print(f"Model Accuracy   : {round(accuracy, 4)}")
print(f"Required Accuracy: {MINIMUM_ACCURACY}")

if accuracy < MINIMUM_ACCURACY:
    print("QUALITY GATE FAILED")
    print("Model performance is below the required threshold.")
    sys.exit(1)

print("QUALITY GATE PASSED")
print("Model performance satisfies the required threshold.")
sys.exit(0)
