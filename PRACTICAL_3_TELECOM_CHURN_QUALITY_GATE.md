# PRACTICAL - 3: Implementing an ML Quality Gate using GitHub Actions (Telecom Churn Model)

**MLOps Practical Series | CI/CD with GitHub Actions**  
**Continuation of**: Practical-2: Telecom Churn ML CI  
**Dataset**: `telecom_churn.csv` (243,553 rows)  
**Quality Decision Metric**: Minimum Accuracy Threshold  

---

## 1. Practical Objective

The objective of Practical 3 is to integrate an **automated model-quality decision gate** into the GitHub Actions CI pipeline. The pipeline trains the Telecom Churn model, reads the generated evaluation metrics (`metrics.json`), compares the evaluated accuracy against a predefined operational threshold (`MINIMUM_ACCURACY = 0.50`), and **automatically terminates the pipeline** if the trained model fails to satisfy the quality criterion.

```
Code / Workflow Change
        ↓
GitHub Actions Triggered
        ↓
Train Telecom Churn Model (train_model.py)
        ↓
Generate metrics.json & telecom_churn_model.pkl
        ↓
Execute Quality Gate (quality_gate.py)
        ↓
Is Model Accuracy ≥ Required Threshold?
        ↓
PASS (exit 0) → Continue to Unit Tests | FAIL (exit 1) → Terminate Pipeline
```

---

## 2. Prerequisites & Repository Structure

This practical builds directly on Practical 2. The repository structure is:

```
mlops-ass-1/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Practical 1 workflow
│       └── ml-ci.yml              # Practical 2 & 3 ML CI workflow (updated)
├── requirements.txt               # numpy, pandas, scikit-learn, joblib
├── telecom_churn.csv              # Customer dataset
├── train_model.py                 # Scikit-learn training script
├── test_ml_pipeline.py            # Automated ML pipeline tests
├── quality_gate.py                # Quality gate verification program
├── .gitignore                     # Ignores runtime artifacts
└── README.md                      # Documentation
```

During CI execution, `train_model.py` generates temporary files on the runner:
- `telecom_churn_model.pkl`: Trained Scikit-Learn Pipeline
- `metrics.json`: Model evaluation metrics

---

## 3. Quality Gate Concept

A **Quality Gate** is an automated checkpoint enforcing strict criteria that any machine learning model must satisfy before proceeding downstream (e.g., towards unit testing, packaging, or deployment).

$$\text{Decision} = \begin{cases} \text{QUALITY GATE PASSED (exit 0)} & \text{if } \text{Accuracy} \ge 0.50 \\ \text{QUALITY GATE FAILED (exit 1)} & \text{if } \text{Accuracy} < 0.50 \end{cases}$$

> **Key MLOps Principle**: A successfully trained model is **not automatically an acceptable model**. A training script might run without syntax errors and produce a `.pkl` file, but if its performance drops below production thresholds, the CI pipeline must reject it immediately.

---

## 4. Implementation Steps

### Step 1 & 2 - Verify `metrics.json` Output
The `train_model.py` program from Practical 2 outputs:
```json
{
    "accuracy": 0.5034,
    "training_records": 194842,
    "testing_records": 48711
}
```

---

### Step 3 - Create Quality Gate Program (`quality_gate.py`)

Create `quality_gate.py` in the root of the repository:

```python
"""
ML Quality Gate for Telecom Customer Churn Model
Practical 3 - Implementing an ML Quality Gate using GitHub Actions
"""

import json
import sys

# Minimum acceptable accuracy threshold
MINIMUM_ACCURACY = 0.50

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
```

---

### Step 4 - Understanding the Quality Gate Code

1. **Threshold Definition (`MINIMUM_ACCURACY = 0.50`)**:
   Defines the operational quality bar. If the model achieves $\ge 50\%$, it qualifies for testing and downstream use.
2. **Decoupled Metric Reading (`metrics.json`)**:
   `quality_gate.py` operates as an independent stage, decoupling model training logic from business deployment policies.
3. **Failing the CI Workflow (`sys.exit(1)`)**:
   A non-zero exit code informs GitHub Actions that the step has failed, which immediately stops the runner from proceeding to subsequent steps (`test_ml_pipeline.py` is skipped).
4. **Passing the CI Workflow (`sys.exit(0)`)**:
   Exit code `0` signals success, prompting GitHub Actions to move to the automated testing stage.

---

### Step 5 - Update GitHub Actions ML CI Workflow (`.github/workflows/ml-ci.yml`)

Add the `Check ML quality gate` step immediately after model training:

```yaml
name: Telecom Churn ML CI

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  train-and-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Upgrade pip
        run: python -m pip install --upgrade pip

      - name: Install ML dependencies
        run: pip install -r requirements.txt

      - name: Train telecom churn model
        run: python train_model.py

      - name: Check ML quality gate
        run: python quality_gate.py

      - name: Run automated ML tests
        run: python -m unittest test_ml_pipeline.py -v
```

---

### Step 6 - Observe Successful Quality Gate Run

In GitHub $\rightarrow$ **Actions** $\rightarrow$ **Telecom Churn ML CI** $\rightarrow$ latest run:
1. `✓ Set up job`
2. `✓ Checkout repository`
3. `✓ Set up Python`
4. `✓ Upgrade pip`
5. `✓ Install ML dependencies`
6. `✓ Train telecom churn model`
7. `✓ Check ML quality gate` (PASS)
8. `✓ Run automated ML tests` (PASS)
9. `✓ Complete job`

#### Quality Gate Log Output:
```text
Reading model evaluation metrics...
Model Accuracy   : 0.5034
Required Accuracy: 0.5
QUALITY GATE PASSED
Model performance satisfies the required threshold.
```
**Result**: **PASS (Green Checkmark)**.

---

### Step 7 - Deliberately Demonstrate Quality Gate Failure

To verify that the gate blocks subpar models:
1. Open `quality_gate.py`.
2. Temporarily raise `MINIMUM_ACCURACY` higher than the model's performance:
   ```python
   # Original:
   MINIMUM_ACCURACY = 0.50

   # Controlled Failure:
   MINIMUM_ACCURACY = 0.90
   ```
3. Commit with message: `Increase threshold for quality gate failure demo`.
4. Push to `main`.
5. Observe the CI run in GitHub Actions:
   - `✓ Train telecom churn model` (Completed)
   - `❌ Check ML quality gate` (**FAILED**, exit code 1)
   - `⚪ Run automated ML tests` (**SKIPPED**)

#### Failed Step Log:
```text
Reading model evaluation metrics...
Model Accuracy   : 0.5034
Required Accuracy: 0.9
QUALITY GATE FAILED
Model performance is below the required threshold.
Error: Process completed with exit code 1.
```

---

### Step 8 - Restore the Correct Quality Gate

1. Restore `MINIMUM_ACCURACY = 0.50`.
2. Commit with message: `Restore ML quality gate threshold`.
3. Push to `main`.
4. Observe that the workflow completes with all steps green (**PASS**).

---

## 5. Successful vs. Failed Quality Gate Matrix

| Condition | Result | GitHub Actions Behavior |
|:---|:---:|:---|
| Model Accuracy = 0.5034, Threshold = 0.50 | **PASS** | Quality gate succeeds; workflow continues to unit tests. |
| Model Accuracy = 0.5034, Threshold = 0.90 | **FAIL** | Workflow terminates at quality gate; unit tests are skipped. |
| Model Accuracy = 0.3500, Threshold = 0.50 | **FAIL** | Model rejected due to poor training results. |

---

## 6. Why the Quality Gate is Separate from Unit Tests

| Characteristic | Unit / Pipeline Tests (`test_ml_pipeline.py`) | Model Quality Gate (`quality_gate.py`) |
|:---|:---|:---|
| **Primary Question** | *Did the code and pipeline execute correctly?* | *Is the resulting model accurate enough for business use?* |
| **Validation Scope** | File existence, valid data types, unpickling, syntax | Statistical evaluation metrics (accuracy, precision, recall) |
| **Example Check** | `os.path.exists("telecom_churn_model.pkl")` | `accuracy >= MINIMUM_ACCURACY` |
| **Failure Implication** | Implementation bug or broken environment | Degraded model performance / data drift / insufficient data |

---

## 7. Troubleshooting Guide

| Issue | Possible Cause | Corrective Action |
|:---|:---|:---|
| `FileNotFoundError: metrics.json` | `quality_gate.py` ran before `train_model.py` | Verify workflow order in `ml-ci.yml`. `Train telecom churn model` must precede `Check ML quality gate`. |
| `KeyError: 'accuracy'` | Key name mismatch | Ensure `train_model.py` writes `"accuracy"` and `quality_gate.py` reads `"accuracy"`. |
| Workflow stops at quality gate | Evaluated accuracy is below configured threshold | Check training log and metrics; verify threshold is set to `0.50`. |
| Automated tests are skipped | Quality gate failed with exit code 1 | This is the expected behavior when a gate fails. |

---

## 8. Verification Checklist & Screenshots to Preserve

- [ ] 1. Repository file tree showing `quality_gate.py` alongside Practical 2 files.
- [ ] 2. `quality_gate.py` displaying `MINIMUM_ACCURACY = 0.50`.
- [ ] 3. Updated `ml-ci.yml` showing the `Check ML quality gate` step.
- [ ] 4. Successful GitHub Actions run with all steps green.
- [ ] 5. Expanded successful `Check ML quality gate` log showing `QUALITY GATE PASSED`.
- [ ] 6. Failed GitHub Actions run showing `Check ML quality gate` in red and tests skipped.
- [ ] 7. Expanded failed quality gate log showing `exit code 1`.
- [ ] 8. Final restored run showing green success indicator.

---

## 9. Result & Next Practical Preview

### Result:
An automated Machine Learning Quality Gate was successfully integrated into the Telecom Customer Churn CI workflow. The pipeline now validates performance against a defined minimum accuracy threshold, transforming the CI pipeline from a mechanical test runner into an automated governance quality gate.

### Next Practical Preview (Practical - 4):
**Preserve ML Artifacts**: Practical 4 will preserve the generated model (`telecom_churn_model.pkl`) and metrics (`metrics.json`) as downloadable workflow artifacts using GitHub Actions `actions/upload-artifact`.
