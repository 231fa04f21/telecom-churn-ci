# PRACTICAL - 1: Implementing the First CI Pipeline Using GitHub Actions (Telecom Churn Dataset)

**Course**: MLOps - Continuous Integration  
**Assignment**: Practical - 1 (Customized for Telecom Churn)  
**Dataset**: `telecom_churn.csv` (243,553 rows, 14 columns)  

---

## 1. Objective

To configure an automated **GitHub Actions** Continuous Integration (CI) pipeline that automatically executes Python unit tests whenever code is committed or pushed to the `main` branch, and to observe both successful and failed CI executions using the **Telecom Customer Churn** domain.

---

## 2. Practical Overview

In this practical, we build the initial CI foundation for our MLOps lifecycle on the **Telecom Churn** dataset. Following the reference architecture from the course:
1. A Python prediction module (`churn_logic.py`) is created to model churn decision rules.
2. Automated unit tests (`test_churn_logic.py`) are created using Python's `unittest` framework.
3. A GitHub Actions CI workflow (`.github/workflows/ci.yml`) is configured to run tests on a cloud-hosted Ubuntu runner.
4. A commit triggers the automated test execution, resulting in a **PASS (Success)**.
5. A deliberate defect is introduced into the prediction logic to observe a **FAIL (Failure)** in CI.
6. The defect is corrected and recommitted to restore the **PASS (Success)** state.

```
Create Repository
       ↓
Create Python Program (churn_logic.py)
       ↓
Create Unit Tests (test_churn_logic.py)
       ↓
Create GitHub Actions Workflow (.github/workflows/ci.yml)
       ↓
Commit to main Branch
       ↓
GitHub-hosted Ubuntu Runner Executes Tests
       ↓
PASS (Green) / FAIL (Red)
```

---

## 3. Dataset Context: `telecom_churn.csv`

The dataset consists of **243,553 customer records** with 14 features:
- `customer_id`: Unique identifier
- `telecom_partner`: Reliance Jio, Airtel, Vodafone, BSNL
- `gender`, `age`, `state`, `city`, `pincode`, `date_of_registration`
- `num_dependents`: Family dependents
- `estimated_salary`: Annual/monthly estimated income
- `calls_made`: Outgoing voice calls
- `sms_sent`: SMS messages sent
- `data_used`: Mobile internet usage (MB)
- `churn`: Target label (`1` = Churned, `0` = Retained)

### Business Rule Formulation (Pre-ML Baseline)
As highlighted in MLOps Practical 1, before training machine learning models, CI pipelines must first be established with deterministic business rules:
- **Rule**: If a customer maintains at least **20 calls** and consumes at least **1,000 MB** of data, they have active engagement and are predicted as **RETAIN**.
- If engagement drops below these thresholds (`calls_made < 20` or `data_used < 1000`), the customer is at immediate risk and predicted as **CHURN**.

---

## 4. Step-by-Step Implementation

### Step 1 - Sign in to GitHub
1. Open [https://github.com](https://github.com) in your browser.
2. Sign in with your GitHub account credentials.
3. Navigate to **Your repositories**.

---

### Step 2 - Create a New Repository
1. Click **New** repository.
2. Repository name: `telecom-churn-ci` (or `mlops-ass-1`).
3. Description: `Continuous Integration pipeline for Telecom Customer Churn using GitHub Actions`.
4. Visibility: **Public**.
5. Initialize with README: Checked (or push existing local repo).
6. Click **Create repository**.

---

### Step 3 - Create the Python Program (`churn_logic.py`)
Create `churn_logic.py` in the root of the repository:

```python
"""
Telecom Customer Churn Decision Logic
Practical 1 - First CI Pipeline Using GitHub Actions
"""

def predict_churn(calls_made: int, data_used: int) -> str:
    """
    Predicts whether a telecom customer is likely to CHURN or RETAIN
    based on usage activity thresholds.

    Rules:
    - If calls_made >= 20 and data_used >= 1000 MB: "RETAIN"
    - Otherwise: "CHURN"
    """
    if calls_made >= 20 and data_used >= 1000:
        return "RETAIN"
    else:
        return "CHURN"


if __name__ == "__main__":
    result = predict_churn(calls_made=50, data_used=3500)
    print("Predicted Customer Status:", result)
```

---

### Step 4 - Commit the Python Program
1. Commit message: `Add telecom churn prediction logic`.
2. Commit directly to the `main` branch.

---

### Step 5 - Create the Unit Test File (`test_churn_logic.py`)
Create `test_churn_logic.py` to define the expected behavior and quality gates:

```python
"""
Unit Tests for Telecom Customer Churn Logic
Practical 1 - First CI Pipeline Using GitHub Actions
"""

import unittest
from churn_logic import predict_churn


class TestChurnLogic(unittest.TestCase):

    def test_retain_case(self):
        """Active customer meeting both call and data thresholds should be RETAINED."""
        result = predict_churn(calls_made=50, data_used=3500)
        self.assertEqual(result, "RETAIN")

    def test_churn_due_to_low_calls(self):
        """Customer with high data usage but critically low calls (< 20) should CHURN."""
        result = predict_churn(calls_made=10, data_used=3500)
        self.assertEqual(result, "CHURN")

    def test_churn_due_to_low_data(self):
        """Customer with high call volume but low data usage (< 1000 MB) should CHURN."""
        result = predict_churn(calls_made=50, data_used=400)
        self.assertEqual(result, "CHURN")


if __name__ == "__main__":
    unittest.main()
```

#### Test Cases Summary:
| Test Case Name | Calls Made | Data Used (MB) | Expected Result | Reason |
|:---|:---:|:---:|:---:|:---|
| `test_retain_case` | 50 | 3500 | `RETAIN` | Both calls and data are above thresholds |
| `test_churn_due_to_low_calls` | 10 | 3500 | `CHURN` | Calls (10) < threshold (20) |
| `test_churn_due_to_low_data` | 50 | 400 | `CHURN` | Data (400) < threshold (1000) |

---

### Step 6 - Commit the Unit Tests
1. Commit message: `Add automated tests for telecom churn logic`.
2. Commit directly to the `main` branch.

---

### Step 7 & 8 - Create the GitHub Actions Workflow (`.github/workflows/ci.yml`)
1. Create folder path `.github/workflows/` and file `ci.yml`.
2. Add the following YAML configuration:

```yaml
name: Telecom Churn CI Pipeline

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
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Get project code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run automated tests
        run: python -m unittest discover -v
```

#### Explanation of Workflow Elements:
| Workflow Directive | Purpose |
|:---|:---|
| `name: Telecom Churn CI Pipeline` | Readable display name on the GitHub Actions dashboard |
| `push -> main` | Triggers test execution automatically whenever code is pushed to `main` |
| `pull_request -> main` | Runs verification checks on any proposed PR before merging |
| `workflow_dispatch` | Enables manual run trigger button in the Actions UI |
| `permissions: contents: read` | Grants runner permission to pull repository source code |
| `runs-on: ubuntu-latest` | Allocates a GitHub-hosted Linux VM for running the job |
| `actions/checkout@v4` | Official GitHub Action to clone the repository to the runner |
| `actions/setup-python@v5` | Provisions Python 3.11 environment on the runner |
| `python -m unittest discover -v` | Automatically discovers and runs all test files starting with `test_` |

---

### Step 9 - Commit the Workflow
1. Commit message: `Add first CI workflow for telecom churn`.
2. Commit directly to the `main` branch.

---

### Step 10 & 11 - Inspect First Successful CI Run
1. Go to the **Actions** tab in GitHub.
2. Select **Telecom Churn CI Pipeline**.
3. Click the latest workflow run triggered by the push commit.
4. Expand **test** -> **Run automated tests**.
5. Observe the successful test log:
```text
test_churn_due_to_low_calls (test_churn_logic.TestChurnLogic.test_churn_due_to_low_calls) ... ok
test_churn_due_to_low_data (test_churn_logic.TestChurnLogic.test_churn_due_to_low_data) ... ok
test_retain_case (test_churn_logic.TestChurnLogic.test_retain_case) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.001s

OK
```
Result: **Green Checkmark (SUCCESS)**.

---

### Step 12 - Manual Workflow Trigger
1. Go to **Actions** -> **Telecom Churn CI Pipeline**.
2. Click **Run workflow** dropdown on the right side.
3. Select branch `main` and click **Run workflow**.
4. A new workflow run executes successfully without requiring any code change.

---

### Step 13 - Introduce an Intentional Defect
To verify that CI effectively prevents faulty logic from slipping through, edit `churn_logic.py` and deliberately return `"CHURN"` for the active condition:

```python
def predict_churn(calls_made: int, data_used: int) -> str:
    if calls_made >= 20 and data_used >= 1000:
        return "CHURN"  # INTENTIONAL DEFECT: Should be RETAIN
    else:
        return "CHURN"
```

---

### Step 14 & 15 - Commit Defect and Observe CI Failure
1. Commit message: `Modify churn logic (intentional error)`.
2. Commit to `main`.
3. Open **Actions** tab -> Open newest workflow run.
4. Result: **Red Cross (FAILURE)**.
5. Expand **Run automated tests** log:
```text
======================================================================
FAIL: test_retain_case (test_churn_logic.TestChurnLogic.test_retain_case)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/runner/work/mlops-ass-1/mlops-ass-1/test_churn_logic.py", line 14, in test_retain_case
    self.assertEqual(result, "RETAIN")
AssertionError: 'CHURN' != 'RETAIN'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=1)
Error: Process completed with exit code 1.
```
> **Key Observation**: The Python code executed without syntax errors, but the automated test detected the logical regression and immediately failed the CI pipeline.

---

### Step 16 & 17 - Correct the Code and Verify Success
1. Re-open `churn_logic.py`.
2. Restore the correct return value:
```python
def predict_churn(calls_made: int, data_used: int) -> str:
    if calls_made >= 20 and data_used >= 1000:
        return "RETAIN"
    else:
        return "CHURN"
```
3. Commit message: `Fix churn prediction logic bug`.
4. Observe **Actions** tab: The new run turns **Green (SUCCESS)**.

---

## 5. Final Repository Structure

```
mlops-ass-1/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── README.md
├── churn_logic.py
├── test_churn_logic.py
└── telecom_churn.csv
```

---

## 6. Troubleshooting and Common Issues

| Issue | Root Cause | Solution |
|:---|:---|:---|
| Actions tab does not show a workflow | Workflow file is misplaced or misnamed | Verify path is exactly `.github/workflows/ci.yml` (lowercase). |
| Workflow does not trigger on push | Branch mismatch or invalid YAML indentation | Ensure push branch matches repository default branch (`main`). Validate YAML spacing. |
| `ModuleNotFoundError: No module named 'churn_logic'` | Working directory or filename mismatch | Ensure `churn_logic.py` and `test_churn_logic.py` are both in the repository root. |
| Tests not discovered by `unittest` | Filename does not follow convention | Test files must start with `test_` (e.g. `test_churn_logic.py`). |
| "Run workflow" button not visible | Missing `workflow_dispatch:` trigger | Add `workflow_dispatch:` under the `on:` section in `ci.yml` and commit to default branch. |

---

## 7. Practical Record Checklist (Evidence to Preserve)

Capture and preserve screenshots of:
- [ ] 1. Repository home page displaying `churn_logic.py`, `test_churn_logic.py`, and `.github/workflows/ci.yml`.
- [ ] 2. Workflow file contents of `.github/workflows/ci.yml`.
- [ ] 3. First successful CI run in the Actions tab with green checkmark.
- [ ] 4. Expanded `Run automated tests` log showing 3 tests passed (`OK`).
- [ ] 5. Failed CI run after introducing the deliberate defect (`AssertionError: 'CHURN' != 'RETAIN'`).
- [ ] 6. Corrected CI run showing green checkmark after fixing the logic.

---

## 8. Understanding Check (Viva / Quiz Questions)

### Q1: What triggered the CI workflow automatically?
**Answer**: An event trigger (`push` or `pull_request` to the `main` branch) detected by GitHub Actions when code was committed to the repository.

### Q2: Where did the Python unit tests execute?
**Answer**: On an ephemeral GitHub-hosted Ubuntu virtual machine specified by `runs-on: ubuntu-latest`.

### Q3: Why is `actions/checkout` necessary in the workflow?
**Answer**: By default, the cloud runner is an empty virtual machine. `actions/checkout` clones the repository contents into the runner's workspace so Python can access the code and test files.

### Q4: What is the purpose of `workflow_dispatch`?
**Answer**: It enables manual execution of the CI pipeline directly from the GitHub web interface without needing to make a git commit.

### Q5: Why did the intentional defect cause the CI pipeline to fail?
**Answer**: The unit test `test_retain_case` asserted that an active user produces `"RETAIN"`, but the modified function returned `"CHURN"`. Python's `unittest` raised an `AssertionError`, causing process exit code `1`, which instructed GitHub Actions to mark the job as failed.

### Q6: Does this setup represent a complete CI/CD pipeline?
**Answer**: No. This practical demonstrates **Continuous Integration (CI)**, focusing on automated code checkout and test verification. Continuous Deployment (CD), model packaging (Docker/GHCR), and cloud hosting are subsequent stages.

