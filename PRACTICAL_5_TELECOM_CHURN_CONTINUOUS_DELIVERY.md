# PRACTICAL - 5: Continuous Delivery of an ML Prediction Application using GitHub Actions

**MLOps Practical Series | CI/CD with GitHub Actions**  
**Continuation of**: Practical-4: Preserving ML Artifacts  
**Dataset**: `telecom_churn.csv`  
**Deliverable**: Deployable Release Package (`telecom-churn-ml-release`)  

---

## 1. Practical Objective

The objective of Practical 5 is to transition from **Continuous Integration (CI)** to **Continuous Delivery (CD)** by combining the validated Telecom Churn machine learning model with a production-ready **Flask REST API**, verifying the application via automated tests, and packaging it into a standalone **deployable release candidate**.

```
Code / Workflow Change
        ↓
GitHub Actions (train-test-deliver)
        ↓
Train ML Model (train_model.py)
        ↓
ML Quality Gate (quality_gate.py)
        ↓
Automated ML Tests (test_ml_pipeline.py)
        ↓
Prediction API Tests (test_app.py)
        ↓
Prepare Release Candidate (release_candidate/ + DEPLOYMENT.txt)
        ↓
Upload Release Package (actions/upload-artifact@v4)
        ↓
READY FOR PRODUCTION DEPLOYMENT
```

> **Learning Outcome**: Understand the architectural boundary between CI and CD. CI guarantees that the model and code function correctly; CD packages the verified model and application into a production-ready release candidate artifact without publishing directly to production servers.

---

## 2. CI vs. CD Stage Breakdown

| Stage | Action in this Practical | Output |
|:---|:---|:---|
| **Continuous Integration (CI)** | Train model, evaluate accuracy, enforce quality gate ($\ge 0.50$), run ML tests | Verified model `.pkl` + `metrics.json` |
| **Continuous Delivery (CD)** | Validate Flask HTTP endpoints, construct `release_candidate/` directory, package artifacts | `telecom-churn-ml-release.zip` |
| **Production Deployment** | Deploy container / cloud web service | Handled in Practical 6 & 10 |

---

## 3. Implemented Components

### 3.1 Dependencies (`requirements.txt`)
Flask is added to the project dependencies:
```text
numpy
pandas
scikit-learn
joblib
flask
```

---

### 3.2 Prediction Application (`app.py`)
A Flask REST API exposing health and prediction endpoints:

```python
"""
Flask Prediction API for Telecom Customer Churn
Practical 5 - Continuous Delivery of an ML Prediction Application
"""

from pathlib import Path
import joblib
import pandas as pd
from flask import Flask, jsonify, request

app = Flask(__name__)

MODEL_PATH = Path("telecom_churn_model.pkl")
FEATURES = [
    "age",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used"
]


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "telecom_churn_model.pkl was not found. "
            "Run the training pipeline first."
        )
    return joblib.load(MODEL_PATH)


@app.get("/")
def health_check():
    return jsonify({
        "status": "ok",
        "service": "telecom-churn-prediction"
    })


@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON request body is required"}), 400

    missing_fields = [
        feature for feature in FEATURES
        if feature not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    sample = pd.DataFrame([{
        feature: data[feature]
        for feature in FEATURES
    }])

    model = load_model()
    prediction_code = int(model.predict(sample)[0])
    prediction = "CHURN" if prediction_code == 1 else "RETAIN"

    return jsonify({
        "prediction": prediction,
        "prediction_code": prediction_code
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

### 3.3 Automated Application Tests (`test_app.py`)

```python
"""
Automated Tests for Telecom Churn Flask Prediction Application
Practical 5 - Continuous Delivery of an ML Prediction Application
"""

import unittest
from app import app


class TestPredictionApplication(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.get_json()["service"], "telecom-churn-prediction")

    def test_low_risk_retained_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 25,
                "num_dependents": 4,
                "estimated_salary": 140000,
                "calls_made": 90,
                "sms_sent": 50,
                "data_used": 9000
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["prediction"],
            "RETAIN"
        )
        self.assertEqual(
            response.get_json()["prediction_code"],
            0
        )

    def test_high_risk_churn_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 70,
                "num_dependents": 0,
                "estimated_salary": 30000,
                "calls_made": 5,
                "sms_sent": 2,
                "data_used": 100
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["prediction"],
            "CHURN"
        )
        self.assertEqual(
            response.get_json()["prediction_code"],
            1
        )

    def test_missing_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 25,
                "calls_made": 90
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "missing_fields",
            response.get_json()
        )


if __name__ == "__main__":
    unittest.main()
```

---

### 3.4 Continuous Delivery Workflow (`.github/workflows/ml-ci.yml`)

```yaml
name: Telecom Churn ML CI-CD

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
  train-test-deliver:
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

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Train telecom churn model
        run: python train_model.py

      - name: Check ML quality gate
        run: python quality_gate.py

      - name: Run automated ML tests
        run: python -m unittest test_ml_pipeline.py -v

      - name: Run prediction application tests
        run: python -m unittest test_app.py -v

      - name: Prepare release candidate
        run: |
          mkdir -p release_candidate
          cp app.py release_candidate/
          cp telecom_churn_model.pkl release_candidate/
          cp metrics.json release_candidate/
          cp requirements.txt release_candidate/
          printf "Telecom Customer Churn Prediction ML Application\nRun: python app.py\nEndpoint: POST /predict\n" > release_candidate/DEPLOYMENT.txt

      - name: Upload release candidate
        uses: actions/upload-artifact@v4
        with:
          name: telecom-churn-ml-release
          path: release_candidate/
          if-no-files-found: error
          retention-days: 7
```

---

## 4. Release Candidate Package Structure

```
release_candidate/
├── app.py                     # Flask HTTP REST API
├── telecom_churn_model.pkl    # Serialized ML model pipeline
├── metrics.json               # Recorded evaluation metrics
├── requirements.txt           # Application dependencies
└── DEPLOYMENT.txt             # Startup command & API instructions
```

---

## 5. Step-by-Step Verification Guide on GitHub

### Step 9 & 10: Verify Workflow and Application Tests
1. Go to **Actions** $\rightarrow$ **Telecom Churn ML CI-CD** $\rightarrow$ latest run.
2. Expand **Run prediction application tests**:
   ```text
   test_health_endpoint ... ok
   test_high_risk_churn_prediction ... ok
   test_low_risk_retained_prediction ... ok
   test_missing_field_validation ... ok

   Ran 4 tests in 2.035s

   OK
   ```
3. Verify that **Prepare release candidate** and **Upload release candidate** complete with green checkmarks.

---

### Step 11: Download and Inspect the Release Candidate
1. On the workflow run summary page, navigate to **Artifacts**.
2. Click **`telecom-churn-ml-release`** to download the archive.
3. Extract the ZIP file and verify that `app.py`, `telecom_churn_model.pkl`, `metrics.json`, `requirements.txt`, and `DEPLOYMENT.txt` are present.

---

### Step 12: Controlled Failure Demonstration
1. In `test_app.py` on GitHub, edit `test_low_risk_retained_prediction`:
   ```python
   # Change expected prediction from:
   self.assertEqual(response.get_json()["prediction"], "RETAIN")
   # To:
   self.assertEqual(response.get_json()["prediction"], "CHURN")
   ```
2. Commit with message: `Demonstrate application test failure`.
3. Observe the CI-CD run:
   - Model training, quality gate, and ML tests succeed (`✓`).
   - The application test step fails (`❌`):
     ```text
     FAIL: test_low_risk_retained_prediction (test_app.TestPredictionApplication.test_low_risk_retained_prediction)
     AssertionError: 'RETAIN' != 'CHURN'
     ```
   - **`Prepare release candidate`** and **`Upload release candidate`** are automatically **skipped**.
   - No faulty release candidate is produced!

---

### Step 13: Restore Correct Test and Verify Delivery
1. Restore `"RETAIN"` in `test_app.py`.
2. Commit with message: `Restore valid prediction API test`.
3. Verify that the workflow returns to **Green (SUCCESS)** and the release artifact is generated.

---

## 6. MLOps Lifecycle Progression (Practicals 1 to 5)

| Practical | Focus | Deliverable |
|:---|:---|:---|
| **Practical-1** | Basic Code CI | Automated unit testing on commit |
| **Practical-2** | Automated ML Training CI | Automated data loading, model fitting, and ML tests |
| **Practical-3** | ML Quality Gate | Automated performance threshold gate ($\ge 0.50$) |
| **Practical-4** | Artifact Preservation | Preserving temporary runner outputs on GitHub |
| **Practical-5** | Continuous Delivery (CD) | Packaging validated model + Flask API into a release candidate |

---

## 7. Verification Checklist & Screenshots to Preserve

- [ ] 1. Repository file tree showing `app.py` and `test_app.py`.
- [ ] 2. Updated `requirements.txt` containing `flask`.
- [ ] 3. Updated `ml-ci.yml` showing application test and release packaging steps.
- [ ] 4. Successful workflow run with all CI and delivery stages completed.
- [ ] 5. Application test log showing all 4 API tests passed (`OK`).
- [ ] 6. Artifacts section showing `telecom-churn-ml-release`.
- [ ] 7. Contents of the downloaded and extracted release candidate.
- [ ] 8. Controlled failed workflow run showing prediction application test failure and skipped release steps.
- [ ] 9. Final corrected successful workflow run.

---

## 8. Next Practical Preview

**Practical-6: Dockerize the ML Application**: Practical 6 introduces containerization with Docker so that the packaged release candidate runs in an identical container environment across development, staging, and production.

