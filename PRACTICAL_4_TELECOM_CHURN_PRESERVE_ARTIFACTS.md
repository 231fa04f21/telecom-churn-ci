# PRACTICAL - 4: Preserving ML Models and Metrics as GitHub Actions Artifacts

**MLOps Practical Series | CI/CD with GitHub Actions**  
**Continuation of**: Practical-3: ML Quality Gate  
**Dataset**: `telecom_churn.csv`  
**Preserved Artifact**: `telecom-churn-ml-artifacts` (`telecom_churn_model.pkl`, `metrics.json`, `telecom_churn.csv`)  

---

## 1. Practical Objective & Aim

- **Objective**: To preserve the trained Telecom Churn Prediction model, its evaluation metrics, and the dataset as a downloadable GitHub Actions workflow artifact.
- **Workflow Policy**: Upload occurs **only after** model training, the quality gate, and automated unit tests complete successfully.
- **Learning Outcome**: Understand the difference between repository source files, ephemeral GitHub runner files, and preserved GitHub Actions artifacts.

```
Code / Workflow Change
        ↓
GitHub Actions Triggered
        ↓
Train ML Model (train_model.py)
        ↓
ML Quality Gate (quality_gate.py)
        ↓
Automated Unit Tests (test_ml_pipeline.py)
        ↓
Upload ML Artifacts (actions/upload-artifact@v4)
        ↓
Model + Metrics Remain Available After the Runner is Destroyed
```

---

## 2. Artifact Concept in MLOps

A GitHub-hosted Ubuntu runner is **ephemeral**. When the job finishes, the virtual machine is immediately destroyed and all files created during execution are erased.

```
Without Artifact Upload:
Training → Model Created → Workflow Ends → Runner Terminated → Model is LOST ❌

With Artifact Upload:
Training → Model Created → Validation Passed → Artifact Uploaded → Workflow Ends → Model PRESERVED ✅
```

### Storage Distinction:
| Storage Location | What It Contains | Lifecycle & Persistence |
|:---|:---|:---|
| **GitHub Repository** | Source code, test scripts, workflow YAML | Permanent (until modified or deleted by user) |
| **GitHub-Hosted Runner** | Temporary workspace, packages, runtime output | Temporary (discarded immediately after job completion) |
| **GitHub Actions Artifact** | Serialized model (`.pkl`), metrics (`.json`), data | Preserved according to retention policy (7 days) |

---

## 3. Preserved Artifact Bundle

The preserved artifact archive is named **`telecom-churn-ml-artifacts`** and contains:
```
telecom-churn-ml-artifacts/
├── telecom_churn_model.pkl   # Serialized trained Scikit-learn Pipeline
├── metrics.json              # Evaluation accuracy & dataset counts
└── telecom_churn.csv         # Dataset associated with the training run
```

---

## 4. Updated GitHub Actions Workflow (`.github/workflows/ml-ci.yml`)

The artifact upload step is configured at the end of `ml-ci.yml`:

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

      - name: Upload validated ML artifacts
        uses: actions/upload-artifact@v4
        with:
          name: telecom-churn-ml-artifacts
          path: |
            telecom_churn_model.pkl
            metrics.json
            telecom_churn.csv
          if-no-files-found: error
          retention-days: 7
```

### Explanation of Artifact Parameters:
- `uses: actions/upload-artifact@v4`: Official GitHub Action to upload artifacts from the runner to GitHub storage.
- `name: telecom-churn-ml-artifacts`: Name of the downloadable ZIP archive displayed on the Actions summary page.
- `path: |`: Multi-line path specification capturing the model, metrics, and dataset.
- `if-no-files-found: error`: Ensures the CI pipeline fails immediately if any required artifact was not generated, preventing silent omissions.
- `retention-days: 7`: Retains the artifact on GitHub servers for 7 days.

---

## 5. Step-by-Step Verification Guide

### Step 6: Verify Successful Workflow & Upload Log
In GitHub $\rightarrow$ **Actions** $\rightarrow$ **Telecom Churn ML CI** $\rightarrow$ select the latest run:
1. `✓ Checkout repository`
2. `✓ Set up Python`
3. `✓ Upgrade pip`
4. `✓ Install ML dependencies`
5. `✓ Train telecom churn model`
6. `✓ Check ML quality gate`
7. `✓ Run automated ML tests`
8. `✓ Upload validated ML artifacts`
9. `✓ Complete job`

Expand **Upload validated ML artifacts** in the log:
```text
With the provided path, there will be 3 files uploaded
Artifact name is valid!
Uploading artifact: telecom-churn-ml-artifacts.zip
Uploaded bytes ...
Artifact telecom-churn-ml-artifacts successfully finalized.
```
**Status**: **PASS (Green Checkmark)**.

---

### Step 7 & 8: Locate and Inspect Downloaded Artifact
1. Go to the workflow run summary page (click on the run name in the Actions tab).
2. Scroll to the bottom to find the **Artifacts** section:
   - Name: `telecom-churn-ml-artifacts`
3. Click to download the `.zip` archive.
4. Extract the zip file and confirm the presence of:
   - `telecom_churn_model.pkl`
   - `metrics.json`
   - `telecom_churn.csv`
5. Open `metrics.json` and verify the recorded evaluation metrics match the log:
   ```json
   {
       "accuracy": 0.5034,
       "training_records": 194842,
       "testing_records": 48711
   }
   ```

---

### Step 10: Demonstrate Controlled Artifact Upload Failure
To verify that `if-no-files-found: error` halts faulty pipelines:
1. Open `.github/workflows/ml-ci.yml` on GitHub and click **Edit**.
2. Change the model path to a non-existent filename:
   ```yaml
   # Original:
   telecom_churn_model.pkl

   # Failure demo:
   telecom_churn_model_missing.pkl
   ```
3. Commit with message: `Demonstrate missing artifact failure`.
4. Observe the CI run:
   - Training, quality gate, and unit tests all pass (`✓`).
   - The upload step fails (`❌`):
     ```text
     No files were found with the provided path: telecom_churn_model_missing.pkl.
     Error: Process completed with exit code 1.
     ```

---

### Step 11: Restore the Correct Artifact Path
1. Restore `telecom_churn_model.pkl` in `.github/workflows/ml-ci.yml`.
2. Commit with message: `Restore ML artifact path`.
3. Push to `main`.
4. Observe that the workflow completes with all steps green (**PASS**) and the artifact is once again uploaded.

---

## 6. Artifact Preservation Logic Matrix

| Stage Status | Artifact Upload Step | Overall Pipeline Result | Preserved Artifact? |
|:---|:---:|:---:|:---:|
| Training fails | Skipped | **FAIL** | No |
| Quality gate fails | Skipped | **FAIL** | No |
| Unit tests fail | Skipped | **FAIL** | No |
| All checks pass, but a file is missing | **FAIL** (`if-no-files-found: error`) | **FAIL** | No |
| All checks pass and all files exist | **PASS** | **SUCCESS** | **Yes (`telecom-churn-ml-artifacts.zip`)** |

---

## 7. Troubleshooting Guide

| Issue | Possible Cause | Action |
|:---|:---|:---|
| Artifact section not visible | Earlier step failed or job was cancelled | Check step logs; upload step only runs if all preceding steps succeed. |
| `No files were found with the provided path` | Path mismatch between `train_model.py` and `ml-ci.yml` | Confirm filenames match exactly (`telecom_churn_model.pkl`, `metrics.json`). |
| Upload step fails with error | `if-no-files-found: error` is active and a file was not generated | Verify that `train_model.py` executed without errors and generated all 3 files. |
| Artifact expired | 7-day retention period passed | Trigger the workflow manually (`workflow_dispatch`) to generate a fresh artifact. |

---

## 8. Verification Checklist & Screenshots to Preserve

- [ ] 1. Repository file tree showing `.github/workflows/ml-ci.yml` and project files.
- [ ] 2. Updated `ml-ci.yml` showing the `Upload validated ML artifacts` step.
- [ ] 3. Successful workflow run with all 8 steps marked green.
- [ ] 4. Expanded `Upload validated ML artifacts` log showing 3 files uploaded.
- [ ] 5. Run summary page displaying the `telecom-churn-ml-artifacts` download link.
- [ ] 6. Downloaded and extracted folder showing `telecom_churn_model.pkl`, `metrics.json`, and `telecom_churn.csv`.
- [ ] 7. Opened `metrics.json` displaying accuracy and record counts.
- [ ] 8. Controlled failed run with `Upload validated ML artifacts` marked red.
- [ ] 9. Final restored run showing green success indicator.

---

## 9. Result & Next Practical Preview

### Result:
The Telecom Customer Churn CI workflow was successfully extended to preserve validated model outputs as downloadable GitHub Actions artifacts. The model, metrics, and dataset remain accessible after the temporary runner is destroyed, establishing the bridge between Continuous Integration (CI) and Continuous Delivery (CD).

### Next Practical Preview (Practical - 5):
**Continuous Delivery / Model Deployment Application**: Preparing the validated Telecom Churn model for consumption by creating a prediction web service and automating its delivery.
