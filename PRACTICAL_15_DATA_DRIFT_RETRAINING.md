# Practical 15: Detect Data Drift and Trigger Model Retraining
## Running Project: Telecom Churn Prediction | Continuation from Practical 14

---

## 1. Aim
To extend the production MLOps lifecycle of the **Telecom Churn Prediction system** by comparing recent customer input data against the baseline training distribution, detecting statistically significant **data drift** using two-sample Kolmogorov-Smirnov (KS) tests, and triggering candidate model retraining **only when drift is detected and verified ground truth labels are available**, preserving the quality gate before promoting any model to production.

---

## 2. Learning Objectives
- Understand why deployed machine learning models must be actively monitored for statistical shifts in feature distributions.
- Clearly differentiate **data drift**, **concept drift**, **performance drift**, and **normal statistical variation**.
- Establish a baseline **reference dataset** tied directly to the production model version.
- Implement automated two-sample Kolmogorov-Smirnov (KS) hypothesis tests ($p < 0.05$) for numerical features.
- Generate structured, machine-readable drift audit reports (`drift_report.json`).
- Implement **conditional retraining** that prevents unnecessary compute waste and avoids accidental model degradation.
- Enforce the **model quality gate** ($\text{accuracy} \ge 0.50$) on candidate models before approving promotion.
- Maintain end-to-end MLOps auditability from drift detection to candidate evaluation and Kubernetes deployment.

---

## 3. Data Drift vs. Concept Drift vs. Performance Drift

| Type | Definition | Telecom Churn Real-World Example | Detection Mechanism |
| :--- | :--- | :--- | :--- |
| **Data Drift** (Covariate Shift) | Change in the statistical distribution of input features $P(X)$. | Customer demographic shifts (e.g., influx of older subscribers, surge in data usage, drop in voice calls). | **Direct**: Compare reference vs. recent feature distributions using KS tests without needing labels. |
| **Concept Drift** | Change in the relationship between input features and target labels $P(Y \mid X)$. | The same high data usage no longer signals churn because competitive pricing altered customer loyalty patterns. | **Indirect**: Requires post-hoc label analysis and decision boundary evaluation. |
| **Performance Drift** | Degradation in runtime model evaluation metrics over time. | Model accuracy or F1-score drops from 72% to 54% on recent quarters. | **Delayed**: Requires delayed ground truth labels (actual customer churn confirmations). |
| **Normal Variation** | Harmless statistical sampling noise occurring by chance. | Minor day-to-day fluctuations in calls made or SMS sent. | Statistical significance tests ($p \ge 0.05$) filter out random variation. |

---

## 4. End-to-End MLOps Drift & Retraining Architecture

```
               +-------------------------------------------+
               |        Recent Customer Input Batch        |
               |         (drift/current_data.csv)          |
               +-------------------------------------------+
                                     |
                                     v
               +-------------------------------------------+
               |          Drift Detection Engine           |
               |          (drift/detect_drift.py)          |
               |   Two-sample KS Test (p < 0.05 per col)   |
               +-------------------------------------------+
                                     |
                    +----------------+----------------+
                    |                                 |
              No Drift Detected                 Drift Detected
           (drifted_features < 2)           (drifted_features >= 2)
                    |                                 |
                    v                                 v
        +-----------------------+         +-----------------------+
        |  Continue Monitoring  |         | Check for Ground Truth|
        |  (Skip Retraining)    |         | (current_labeled_data)|
        +-----------------------+         +-----------------------+
                                                      |
                                          +-----------+-----------+
                                          |                       |
                                     Labels Missing        Labels Present
                                          |                       |
                                          v                       v
                              +-----------------------+ +-------------------+
                              | Await True Churn Data | | Retrain Candidate |
                              | (Do not train blind)  | |  (combined data)  |
                              +-----------------------+ +-------------------+
                                                                  |
                                                                  v
                                                        +-------------------+
                                                        |   Quality Gate    |
                                                        |  Accuracy >= 0.50 |
                                                        +-------------------+
                                                                  |
                                                      +-----------+-----------+
                                                      |                       |
                                                 FAIL (< 0.50)           PASS (>= 0.50)
                                                      |                       |
                                                      v                       v
                                          +-----------------------+ +-------------------+
                                          | Reject Candidate      | | Approve & Promote |
                                          | Keep Current Model    | | Overwrite Model   |
                                          +-----------------------+ +-------------------+
                                                                              |
                                                                              v
                                                                    +-------------------+
                                                                    | Trigger CI/CD     |
                                                                    | Automated K8s CD  |
                                                                    +-------------------+
```

---

## 5. File Structure & Implementations

```
drift/
├── prepare_reference.py           # Extracts baseline distribution from training data
├── simulate_current_data.py       # Simulates recent incoming batches (stable vs. drifted)
├── detect_drift.py                # Runs KS 2-sample tests and generates drift_report.json
├── retrain_candidate.py           # Conditional retraining on combined historical + new labeled data
├── approve_candidate.py           # Validates candidate accuracy against the quality gate
├── reference_data.csv             # Baseline feature distribution (243,553 rows)
├── current_data.csv               # Recent unlabelled inputs (1,000 rows)
├── current_labeled_data.csv       # Recent ground truth records for retraining
├── drift_report.json              # Machine-readable drift report with KS statistics & p-values
├── retraining_metrics.json        # Training and testing metrics of the retrained candidate
└── telecom_churn_model_candidate.pkl # Candidate model isolated prior to approval
```

---

## 6. Step-by-Step Execution & Results

### Step 1: Create Baseline Reference Dataset
```powershell
python drift/prepare_reference.py
```
**Output:**
```text
Reference dataset created.
Rows: 243553
File: C:\Users\Nutha\Downloads\MLOPS-tell\MLOPS-ASS-1\drift\reference_data.csv
```

### Step 2: Test the No-Drift Case (Stable Production Data)
```powershell
python drift/simulate_current_data.py --mode stable
python drift/detect_drift.py
```
**Report Output (`drift_report.json`):**
```json
{
  "method": "two-sample KS test",
  "p_value_threshold": 0.05,
  "min_drifted_features": 2,
  "drifted_feature_count": 0,
  "drifted_features": [],
  "overall_drift": false,
  "features": {
    "age": {"ks_statistic": 0.035687, "p_value": 0.154407, "drift_detected": false},
    "num_dependents": {"ks_statistic": 0.017584, "p_value": 0.912291, "drift_detected": false},
    "estimated_salary": {"ks_statistic": 0.025506, "p_value": 0.527679, "drift_detected": false},
    "calls_made": {"ks_statistic": 0.014796, "p_value": 0.979051, "drift_detected": false},
    "sms_sent": {"ks_statistic": 0.021917, "p_value": 0.716435, "drift_detected": false},
    "data_used": {"ks_statistic": 0.017493, "p_value": 0.915351, "drift_detected": false}
  }
}
```
**Verify Retraining is Skipped:**
```powershell
python drift/retrain_candidate.py
```
**Output:**
```text
No overall drift detected.
Retraining skipped.
```
> **Core Principle**: Unconditional retraining wastes compute resources and introduces unnecessary risks of model regression.

---

### Step 3: Test the Drifted Case (Cohort Shift)
```powershell
python drift/simulate_current_data.py --mode drift
python drift/detect_drift.py
```
**Report Output (`drift_report.json`):**
```json
{
  "method": "two-sample KS test",
  "p_value_threshold": 0.05,
  "min_drifted_features": 2,
  "drifted_feature_count": 4,
  "drifted_features": [
    "age",
    "estimated_salary",
    "calls_made",
    "data_used"
  ],
  "overall_drift": true,
  "features": {
    "age": {"ks_statistic": 0.317774, "p_value": 0.0, "drift_detected": true},
    "num_dependents": {"ks_statistic": 0.017584, "p_value": 0.912291, "drift_detected": false},
    "estimated_salary": {"ks_statistic": 0.346779, "p_value": 0.0, "drift_detected": true},
    "calls_made": {"ks_statistic": 0.575289, "p_value": 0.0, "drift_detected": true},
    "sms_sent": {"ks_statistic": 0.021917, "p_value": 0.716435, "drift_detected": false},
    "data_used": {"ks_statistic": 0.421669, "p_value": 0.0, "drift_detected": true}
  }
}
```
**Interpretation**: 4 out of 6 features exhibit statistically significant drift ($p = 0.0 < 0.05$), exceeding `MIN_DRIFTED_FEATURES=2`. `overall_drift` evaluates to `true`.

---

### Step 4: Retrain Candidate Model
```powershell
python drift/retrain_candidate.py
```
**Output:**
```json
{
  "candidate_accuracy": 0.506757,
  "training_rows": 195642,
  "test_rows": 48911,
  "historical_rows": 243553,
  "recent_labeled_rows": 1000
}
```
`telecom_churn_model_candidate.pkl` generated and isolated in `drift/`.

---

### Step 5: Evaluate Quality Gate & Promote Model
```powershell
python drift/approve_candidate.py
```
**Output:**
```text
Candidate accuracy: 0.506757
Required accuracy : 0.5
QUALITY GATE: PASS
Candidate promoted to: C:\Users\Nutha\Downloads\MLOPS-tell\MLOPS-ASS-1\telecom_churn_model.pkl
```

---

### Step 6: Verify Promoted Model Operability & Run Automated Tests
```powershell
python -c "import joblib; m=joblib.load('telecom_churn_model.pkl'); print('Model loaded successfully:', type(m))"
python -m unittest test_app.py
```
**Output:**
```text
Model loaded successfully: <class 'sklearn.pipeline.Pipeline'>
Ran 9 tests in 0.115s

OK
```

---

## 7. Observation Table

| Experiment | Expected Observation | Student Observation |
| :--- | :--- | :--- |
| **Stable Current Batch** | Most features remain statistically similar ($p \ge 0.05$); `overall_drift` is `false`. | `drifted_feature_count: 0`, all features had $p$-values between 0.15 and 0.98. `overall_drift: false`. Retraining was cleanly skipped. |
| **Drifted Current Batch** | Multiple features are flagged ($p < 0.05$); `overall_drift` becomes `true`. | 4 features flagged (`age`, `estimated_salary`, `calls_made`, `data_used`) with $p = 0.0$. `overall_drift: true`. |
| **Drift but No Labels** | Retraining is blocked until verified ground truth labels arrive. | `retrain_candidate.py` raises `FileNotFoundError` if `current_labeled_data.csv` is missing, preventing unverified training. |
| **Candidate Below Threshold** | Quality gate fails; existing production model remains untouched. | If candidate accuracy $< 0.50$, script exits with status 1 and leaves production `telecom_churn_model.pkl` intact. |
| **Candidate Meets Threshold** | Candidate is approved and replaces the production model. | Candidate achieved accuracy $0.5068 \ge 0.50$; promoted to `telecom_churn_model.pkl`. |
| **Post-Promotion Tests** | All API regression tests pass before triggering Docker CI/CD. | 9/9 unit and API integration tests passed in 0.115s. |

---

## 8. Viva & Discussion Questions with Answers

### Q1: What is data drift, and how is it different from concept drift?
**Answer:**
- **Data Drift (Covariate Shift)**: Occurs when the input feature distribution $P(X)$ changes between training and production, even if the underlying mapping to labels $P(Y \mid X)$ remains unchanged. Example: New subscribers are predominantly senior citizens using minimal voice minutes.
- **Concept Drift**: Occurs when the mathematical relationship between inputs and targets $P(Y \mid X)$ changes. Example: Due to a rival telco's aggressive pricing, even customers with historically high usage and long tenure suddenly churn.

### Q2: Why is a fixed reference dataset required, and why must it be tied to a model version?
**Answer:**
A drift test compares two empirical distributions. The reference dataset represents the exact training/validation baseline from which the current model learned its decision boundaries. If the reference is constantly updated on every incoming batch, the baseline "floats" and slow, continuous drift will go undetected.

### Q3: What does the two-sample Kolmogorov-Smirnov (KS) test compare?
**Answer:**
The two-sample KS test is a non-parametric statistical hypothesis test that compares the empirical cumulative distribution functions (eCDFs) of two continuous or numerical samples. It computes the maximum vertical distance ($D$-statistic) between the two distributions without assuming any underlying parametric shape (like normal or Gaussian distributions).

### Q4: What does a small p-value ($p < 0.05$) indicate in this practical?
**Answer:**
Under the null hypothesis ($H_0$), both samples are drawn from identical continuous distributions. A $p$-value $< 0.05$ indicates that there is less than a 5% probability that the observed divergence between reference and production data occurred by random chance alone. Therefore, we reject $H_0$ and declare statistically significant drift for that feature.

### Q5: Why can unlabeled production inputs be used for drift detection while retraining requires labels?
**Answer:**
Drift detection monitors the feature space $X$ ($P(X)$), which is collected immediately whenever clients call the `/predict` API. Retraining a supervised classifier requires both feature inputs $X$ and true outcome ground-truth labels $Y$ ($P(Y \mid X)$) so the optimization algorithm can calculate loss and adjust weights.

### Q6: Why is a retrained candidate model saved separately before approval?
**Answer:**
Isolating the candidate model (`telecom_churn_model_candidate.pkl`) prevents an untested or degraded model from replacing the active production model (`telecom_churn_model.pkl`). The candidate must first undergo objective evaluation against the predefined quality gate.

### Q7: Should every data drift alert automatically trigger retraining and production deployment?
**Answer:**
No. A drift alert should trigger an investigation. Drift could be caused by transient anomalies, sensor or API bugs, upstream pipeline failures, or seasonal spikes (e.g., holiday data surges). Blind automatic retraining can corrupt production models with corrupted or non-representative data. Retraining should only occur when drift is genuine, sustained, and verified ground-truth labels are available.

---

## 9. Result
The Telecom Churn Prediction system was successfully expanded to include automated data drift detection and controlled conditional retraining. Empirical feature distributions were evaluated against a 243,553-row baseline using two-sample KS tests. The pipeline demonstrated that stable data correctly suppresses unnecessary retraining, while detected drift safely initiates supervised retraining on combined data, validates the candidate through an accuracy quality gate, and promotes the approved model with full test verification.

