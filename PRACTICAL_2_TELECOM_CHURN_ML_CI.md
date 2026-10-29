# PRACTICAL - 2: Telecom Churn Prediction ML Model with GitHub Actions CI

**Course**: MLOps Practical Guide | CI/CD with GitHub Actions  
**Practical**: Practical - 2 (ML CI Pipeline)  
**Dataset**: `telecom_churn.csv` (243,553 customer records)  
**Artifacts Generated**: `telecom_churn_model.pkl`, `metrics.json`  

---

## 1. Purpose & Aim

- **Purpose**: Extend the first CI workflow from simple Python unit tests to a complete **Machine Learning Continuous Integration (ML CI)** workflow that installs ML libraries, trains a Scikit-Learn classifier, evaluates model metrics, saves the trained model artifact, and automatically validates the model via unit tests.
- **Aim**: To build a Telecom Churn Prediction machine learning model and configure GitHub Actions to automatically train, evaluate, and test the model whenever the repository is updated.

---

## 2. Expected CI Flow

```
Source Code in GitHub
        ↓
GitHub Actions Push / PR Trigger
        ↓
Set Up Python 3.11
        ↓
Upgrade pip & Install ML Libraries (requirements.txt)
        ↓
Load Dataset (telecom_churn.csv)
        ↓
Train Model (train_model.py: StandardScaler + LogisticRegression)
        ↓
Evaluate Model (Accuracy & Confusion Matrix)
        ↓
Save Artifacts (telecom_churn_model.pkl + metrics.json)
        ↓
Run Automated ML Tests (test_ml_pipeline.py: 7 tests)
        ↓
PASS (Green) / FAIL (Red)
```

---

## 3. Software / Dependencies Required

| Requirement | Used For | Execution Environment |
|:---|:---|:---|
| **GitHub Account & Repo** | Version control & CI host | Cloud |
| **Python 3.11** | Execution runtime | GitHub-hosted `ubuntu-latest` runner |
| **NumPy** | Array computations | Installed via `requirements.txt` |
| **Pandas** | Tabular data manipulation | Installed via `requirements.txt` |
| **Scikit-Learn** | Pipeline, scaling, logistic regression, evaluation | Installed via `requirements.txt` |
| **Joblib** | Serialization of `.pkl` model artifact | Installed via `requirements.txt` |

---

## 4. Implementation Steps

### Step 1 - Repository Structure
```
MLOPS-ASS-1/
├── .github/
│   └── workflows/
│       ├── ci.yml               # Practical 1 Workflow
│       └── ml-ci.yml            # Practical 2 ML CI Workflow
├── requirements.txt             # ML dependencies
├── telecom_churn.csv            # Dataset
├── train_model.py               # ML training and evaluation script
├── test_ml_pipeline.py          # 7 automated ML tests
├── .gitignore                   # Ignore generated artifacts
└── README.md                    # Documentation
```

---

### Step 2 - Create the Dependency File (`requirements.txt`)
```text
numpy
pandas
scikit-learn
joblib
```

---

### Step 3 - Create the Model Training Program (`train_model.py`)

```python
"""
Telecom Churn Prediction ML Model Training Program
Practical 2 - Student Result Prediction ML Model adapted to Telecom Churn
"""

import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def load_dataset(filepath="telecom_churn.csv"):
    """Loads and returns the telecom churn dataset."""
    print("Loading dataset from", filepath, "...")
    data = pd.read_csv(filepath)
    print("Dataset loaded successfully.")
    print("Number of records:", len(data))
    return data


def train_model():
    """Trains the Logistic Regression pipeline, evaluates performance, and saves artifacts."""
    data = load_dataset()

    features = [
        "age",
        "num_dependents",
        "estimated_salary",
        "calls_made",
        "sms_sent",
        "data_used"
    ]

    X = data[features]
    y = data["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print("Training records:", len(X_train))
    print("Testing records :", len(X_test))

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    ])

    print("Training model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions)

    print("\nModel Evaluation")
    print("----------------")
    print("Accuracy:", round(accuracy, 4))
    print("\nConfusion Matrix:")
    print(matrix)

    joblib.dump(model, "telecom_churn_model.pkl")
    print("\nModel saved as telecom_churn_model.pkl")

    metrics = {
        "accuracy": float(accuracy),
        "training_records": len(X_train),
        "testing_records": len(X_test)
    }

    with open("metrics.json", "w") as file:
        json.dump(metrics, file, indent=4)

    print("Metrics saved as metrics.json")
    return accuracy


if __name__ == "__main__":
    train_model()
```

---

### Step 4 - Understanding the ML Pipeline

1. **Features & Target**:
   - `age`: Customer age in years
   - `num_dependents`: Family dependents
   - `estimated_salary`: Estimated income
   - `calls_made`: Outgoing voice calls
   - `sms_sent`: Outgoing SMS messages
   - `data_used`: Mobile data volume in MB
   - `churn`: Target (1 = Churned, 0 = Retained)
2. **Fixed Random Seed (`random_state=42`)**:
   Ensures deterministic train/test splits and consistent model evaluation across CI runs.
3. **Train-Test Split (80/20)**:
   - Total records: 243,553
   - Training records: 194,842 (80%)
   - Testing records: 48,711 (20%)
4. **Pipeline**:
   `StandardScaler` normalizes feature distributions $\rightarrow$ `LogisticRegression` fits linear decision boundaries.
5. **Generated Artifacts**:
   - `telecom_churn_model.pkl`: Serialized Scikit-learn Pipeline
   - `metrics.json`: JSON file storing test accuracy and split counts

---

### Step 5 - Create Automated ML Tests (`test_ml_pipeline.py`)

```python
"""
Automated ML Pipeline Tests for Telecom Customer Churn Prediction
Practical 2 - MLOps CI with GitHub Actions
"""

import json
import os
import unittest
import joblib
import pandas as pd


class TestMLPipeline(unittest.TestCase):

    def test_dataset_created(self):
        """Verify that the telecom churn dataset file exists."""
        self.assertTrue(os.path.exists("telecom_churn.csv"))

    def test_model_created(self):
        """Verify that the trained model artifact .pkl exists."""
        self.assertTrue(os.path.exists("telecom_churn_model.pkl"))

    def test_metrics_created(self):
        """Verify that metrics.json was generated."""
        self.assertTrue(os.path.exists("metrics.json"))

    def test_accuracy_is_valid(self):
        """Verify that the evaluation accuracy is a valid float between 0.0 and 1.0."""
        with open("metrics.json", "r") as file:
            metrics = json.load(file)

        accuracy = metrics["accuracy"]
        self.assertGreaterEqual(accuracy, 0.0)
        self.assertLessEqual(accuracy, 1.0)

    def test_model_prediction(self):
        """Verify that the loaded model outputs a valid class label [0, 1]."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 45,
            "num_dependents": 2,
            "estimated_salary": 80000,
            "calls_made": 50,
            "sms_sent": 25,
            "data_used": 5000
        }])
        prediction = model.predict(sample)[0]
        self.assertIn(int(prediction), [0, 1])

    def test_low_risk_retained_customer(self):
        """Verify that an active customer with high calls & high data usage is classified as RETAINED (0)."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 25,
            "num_dependents": 4,
            "estimated_salary": 140000,
            "calls_made": 90,
            "sms_sent": 50,
            "data_used": 9000
        }])
        prediction = model.predict(sample)[0]
        self.assertEqual(int(prediction), 0)

    def test_high_risk_churn_customer(self):
        """Verify that a customer with dormant usage (very low calls and low data) is classified as CHURN (1)."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 70,
            "num_dependents": 0,
            "estimated_salary": 30000,
            "calls_made": 5,
            "sms_sent": 2,
            "data_used": 100
        }])
        prediction = model.predict(sample)[0]
        self.assertEqual(int(prediction), 1)


if __name__ == "__main__":
    unittest.main()
```

#### What the 7 Tests Verify:
1. `test_dataset_created`: Ensures dataset is available in working directory.
2. `test_model_created`: Ensures `train_model.py` serialized `telecom_churn_model.pkl`.
3. `test_metrics_created`: Ensures `metrics.json` is generated.
4. `test_accuracy_is_valid`: Confirms accuracy is bounded in $[0.0, 1.0]$.
5. `test_model_prediction`: Confirms model unpickling and inference returns valid class.
6. `test_low_risk_retained_customer`: Confirms active user is predicted as Retained (`0`).
7. `test_high_risk_churn_customer`: Confirms dormant user is predicted as Churned (`1`).

---

### Step 6 & 7 - Create GitHub Actions ML CI Workflow (`.github/workflows/ml-ci.yml`)

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

      - name: Run automated ML tests
        run: python -m unittest test_ml_pipeline.py -v
```

#### Workflow Stages:
| Step Name | Command / Action | Expected Result |
|:---|:---|:---|
| Checkout repository | `actions/checkout@v4` | Source code and dataset available on runner |
| Set up Python | `actions/setup-python@v5` | Python 3.11 virtual environment configured |
| Upgrade pip | `python -m pip install --upgrade pip` | Latest pip version ready |
| Install ML dependencies | `pip install -r requirements.txt` | NumPy, Pandas, Scikit-learn, Joblib installed |
| Train telecom churn model | `python train_model.py` | Model trained; `.pkl` & `metrics.json` created |
| Run automated ML tests | `python -m unittest test_ml_pipeline.py -v` | All 7 tests executed; PASS or FAIL reported |

---

### Step 8, 9 & 10 - Verify Execution Logs

#### Step 9: Training Step Log (`Train telecom churn model`):
```text
Loading dataset from telecom_churn.csv ...
Dataset loaded successfully.
Number of records: 243553
Training records: 194842
Testing records : 48711
Training model...

Model Evaluation
----------------
Accuracy: 0.5034

Confusion Matrix:
[[19602 19344]
 [ 4848  4917]]

Model saved as telecom_churn_model.pkl
Metrics saved as metrics.json
```

#### Step 10: Test Step Log (`Run automated ML tests`):
```text
test_accuracy_is_valid (test_ml_pipeline.TestMLPipeline.test_accuracy_is_valid) ... ok
test_dataset_created (test_ml_pipeline.TestMLPipeline.test_dataset_created) ... ok
test_high_risk_churn_customer (test_ml_pipeline.TestMLPipeline.test_high_risk_churn_customer) ... ok
test_low_risk_retained_customer (test_ml_pipeline.TestMLPipeline.test_low_risk_retained_customer) ... ok
test_metrics_created (test_ml_pipeline.TestMLPipeline.test_metrics_created) ... ok
test_model_created (test_ml_pipeline.TestMLPipeline.test_model_created) ... ok
test_model_prediction (test_ml_pipeline.TestMLPipeline.test_model_prediction) ... ok

----------------------------------------------------------------------
Ran 7 tests in 1.208s

OK
```
**CI Status**: **SUCCESS (Green checkmark)**.

---

### Step 11 - Manual Execution (`workflow_dispatch`)
1. Go to repository **Actions** tab.
2. Select **Telecom Churn ML CI**.
3. Click **Run workflow** $\rightarrow$ select `main` $\rightarrow$ click **Run workflow**.

---

### Step 12 & 13 - Controlled Failure for CI Demonstration
To simulate an automated quality gate failure:
1. In `test_ml_pipeline.py`, temporarily change `test_low_risk_retained_customer`:
   ```python
   # Original:
   self.assertEqual(int(prediction), 0)

   # Deliberate failure condition:
   self.assertEqual(int(prediction), 1)
   ```
2. Commit: `Introduce test failure for CI demonstration`.
3. Push to `main`.
4. Observe the failure log:
   ```text
   FAIL: test_low_risk_retained_customer (test_ml_pipeline.TestMLPipeline.test_low_risk_retained_customer)
   AssertionError: 0 != 1
   FAILED (failures=1)
   Error: Process completed with exit code 1.
   ```
5. **Observation**: Model training succeeded, but the CI assertion failed, stopping faulty deployments.

---

### Step 14 - Correct the Test and Re-run CI
1. Restore `self.assertEqual(int(prediction), 0)`.
2. Commit: `Fix ML prediction test`.
3. Push to `main`.
4. Observe that CI turns **Green (PASS)**.

---

## 5. Practical-1 vs Practical-2 Comparison

| Feature | Practical-1: Python CI | Practical-2: ML CI |
|:---|:---|:---|
| **Logic Type** | Hardcoded decision rule | Trained Machine Learning Model |
| **Dependencies** | Standard Python built-ins | NumPy, Pandas, Scikit-Learn, Joblib |
| **Data Source** | Hardcoded values in functions | Real dataset (`telecom_churn.csv`) |
| **Artifact Generation** | None | Trained Model (`.pkl`) & Metrics (`.json`) |
| **Test Verification** | Functional behavior only | Artifact generation, metrics validity, and ML inference |
| **Pipeline Flow** | Code $\rightarrow$ Test | Code $\rightarrow$ Train $\rightarrow$ Evaluate $\rightarrow$ Save $\rightarrow$ Test |

---

## 6. Troubleshooting Guide

| Problem | Likely Cause | Action |
|:---|:---|:---|
| Workflow does not appear | Path typo | Verify file is at `.github/workflows/ml-ci.yml`. |
| Dependency installation fails | Package version conflict or typo | Check `requirements.txt` syntax. |
| Model file test fails | Training failed or wrong filename | Check `train_model.py` log to confirm `.pkl` is dumped with exact name. |
| Tests run before model exists | Step ordering incorrect in YAML | Ensure `Train telecom churn model` runs before `Run automated ML tests`. |
| `AssertionError: 0 != 1` | Sample input changed or seed not set | Ensure `random_state=42` is set in split and classifier. |

---

## 7. Verification Checklist

- [x] Repository contains `requirements.txt`, `train_model.py`, `test_ml_pipeline.py`, and `.github/workflows/ml-ci.yml`.
- [x] ML dependencies install successfully.
- [x] Model training runs in under 2 seconds on 243k records.
- [x] Model artifact `telecom_churn_model.pkl` and `metrics.json` are created.
- [x] All 7 automated unit tests pass locally and in CI.
- [x] Intentional defect produces red failure in CI.
- [x] Restoring correct assertion returns CI to green.
