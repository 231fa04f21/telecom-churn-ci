# Telecom Churn CI Pipeline - MLOps Practical 1

An automated Continuous Integration (CI) pipeline for **Telecom Customer Churn Prediction** implemented using **GitHub Actions** and Python's native `unittest` framework.

---

## 📌 Project Overview

This repository demonstrates the foundational principles of **Continuous Integration (CI)** in Machine Learning Operations (MLOps). Before deploying complex ML models, CI ensures that decision rules, data transformations, and business prediction logic are automatically tested upon every commit and pull request to the `main` branch.

### Business Decision Logic (`churn_logic.py`)
Predicts customer retention vs. churn based on core customer engagement indicators:
- **Calls Made**: Minimum threshold of **20 calls**
- **Data Used**: Minimum threshold of **1,000 MB**

| Calls Made | Data Used | Expected Outcome | Rationale |
|:---:|:---:|:---:|:---|
| $\ge 20$ | $\ge 1000\text{ MB}$ | **RETAIN** | Customer is actively using voice and data services. |
| $< 20$ | Any | **CHURN** | Customer has stopped making calls; high churn risk. |
| Any | $< 1000\text{ MB}$ | **CHURN** | Customer has ceased data consumption; high churn risk. |

---

## 📁 Repository Structure

```
mlops-ass-1/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow definition
├── telecom_churn.csv            # Telecom customer dataset (243,553 records)
├── churn_logic.py               # Churn decision function
├── test_churn_logic.py          # Automated unit test suite
├── .gitignore                   # Git ignore file
└── README.md                    # Project documentation
```

---

## 🧪 Automated Unit Tests (`test_churn_logic.py`)

The test suite validates three core scenarios:
1. `test_retain_case`: Validates that active usage (`calls=50, data=3500`) yields `RETAIN`.
2. `test_churn_due_to_low_calls`: Validates that low call volume (`calls=10, data=3500`) yields `CHURN`.
3. `test_churn_due_to_low_data`: Validates that low data volume (`calls=50, data=400`) yields `CHURN`.

### Running Tests Locally

To run the unit tests in your local terminal:

```bash
python -m unittest discover -v
```

Expected output:
```text
test_churn_due_to_low_calls (test_churn_logic.TestChurnLogic.test_churn_due_to_low_calls) ... ok
test_churn_due_to_low_data (test_churn_logic.TestChurnLogic.test_churn_due_to_low_data) ... ok
test_retain_case (test_churn_logic.TestChurnLogic.test_retain_case) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.001s

OK
```

---

## ⚙️ GitHub Actions CI Workflow (`.github/workflows/ci.yml`)

The workflow is triggered on:
- `push` to `main`
- `pull_request` to `main`
- `workflow_dispatch` (manual one-click trigger from GitHub Actions tab)

### Workflow Steps:
1. **Checkout Code**: Clones repository files onto the GitHub-hosted Ubuntu runner (`actions/checkout@v4`).
2. **Setup Python**: Initializes Python 3.11 (`actions/setup-python@v5`).
3. **Execute Unit Tests**: Runs `python -m unittest discover -v`.
4. **CI Status**: Reports a green checkmark (`SUCCESS`) or red cross (`FAILURE`).

---

## 🔄 CI Failure & Recovery Demonstration

### Step A: Introduce Deliberate Defect
In `churn_logic.py`, modify the return value in the active condition from `"RETAIN"` to `"CHURN"`:
```python
def predict_churn(calls_made: int, data_used: int) -> str:
    if calls_made >= 20 and data_used >= 1000:
        return "CHURN"  # Intentional bug!
    else:
        return "CHURN"
```
**CI Result**: ❌ `FAIL: test_retain_case` (`AssertionError: 'CHURN' != 'RETAIN'`).

### Step B: Fix Defect and Verify
Restore the correct logic:
```python
def predict_churn(calls_made: int, data_used: int) -> str:
    if calls_made >= 20 and data_used >= 1000:
        return "RETAIN"
    else:
        return "CHURN"
```
**CI Result**: ✅ `Ran 3 tests ... OK`.
