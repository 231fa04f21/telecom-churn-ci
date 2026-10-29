# PRACTICAL - 7: Automate Docker Build and Test Using GitHub Actions

**Course**: MLOps Practical Series | CI/CD, Delivery and Docker  
**Continuation of**: Practical-6: Dockerized ML Prediction Application  
**Dataset**: `telecom_churn.csv`  
**Automated Image Tag**: `telecom-churn-ml:${{ github.sha }}`  
**Container Test Runtime**: GitHub-Hosted `ubuntu-latest` Runner  

---

## 1. Practical Aim & Concept

- **Aim**: Extend the Telecom Churn ML CI/CD pipeline so that Docker image creation, container execution, `/health` polling, and `/predict` testing are automated entirely within the **GitHub Actions cloud runner**.
- **Key MLOps Principle**: Code passing unit tests is **not guaranteed** to run in production. Packaging bugs, missing system packages, or wrong port bindings can cause container crashes. Practical 7 tests the final Dockerized container in CI before it is accepted.

```
Code Commit / Push
        ↓
GitHub Actions (train-test-containerize)
        ↓
Train ML Model (train_model.py)
        ↓
ML Quality Gate (quality_gate.py)
        ↓
Automated ML & Application Unit Tests
        ↓
Build Docker Image (docker build -t telecom-churn-ml:${{ github.sha }} .)
        ↓
Start Container (docker run -d -p 5000:5000)
        ↓
Health Check Polling Loop (GET http://localhost:5000/health)
        ↓
Live Prediction Test (curl POST http://localhost:5000/predict)
        ↓
Capture Logs (docker logs) & Teardown (docker rm -f)
        ↓
PASS / FAIL
```

---

## 2. Manual Docker (Practical 6) vs. Automated Docker (Practical 7)

| Feature | Practical-6 (Manual Docker) | Practical-7 (Automated Docker CI) |
|:---|:---|:---|
| **Build Execution** | Executed manually in local PowerShell | Executed automatically on GitHub Ubuntu runner |
| **Container Startup** | Started manually by user | Started automatically by GitHub Actions |
| **API Testing** | Manually invoked via `Invoke-RestMethod` | Automatically tested via `curl` polling loop |
| **Container Teardown** | Manually stopped with `docker stop/rm` | Automated cleanup (`always()` condition) |
| **Traceability** | Tagged manually as `:1.0` | Tagged with Git Commit SHA (`${{ github.sha }}`) |
| **Quality Guarantee** | Dependent on local operator | Consistent, repeatable quality gate on every push |

---

## 3. Automated CI/CD Workflow (`.github/workflows/ml-ci.yml`)

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
  train-test-containerize:
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

      - name: Build Docker image
        run: docker build -t telecom-churn-ml:${{ github.sha }} .

      - name: Start Docker container
        run: |
          docker run -d \
            --name telecom-churn-ml-container \
            -p 5000:5000 \
            telecom-churn-ml:${{ github.sha }}

      - name: Wait for application to become ready
        run: |
          for i in {1..15}; do
            if curl --fail --silent http://localhost:5000/health; then
              echo "Application is ready."
              exit 0
            fi
            echo "Waiting for application... attempt $i"
            sleep 2
          done
          echo "Application did not become ready."
          docker logs telecom-churn-ml-container
          exit 1

      - name: Test prediction endpoint
        run: |
          response=$(curl --fail --silent --show-error \
            -X POST \
            -H "Content-Type: application/json" \
            -d '{
              "age": 25,
              "num_dependents": 4,
              "estimated_salary": 140000,
              "calls_made": 90,
              "sms_sent": 50,
              "data_used": 9000
            }' \
            http://localhost:5000/predict)
          echo "Prediction response: $response"
          echo "$response" | grep -q '"prediction"'

      - name: Show Docker container logs
        if: always()
        run: docker logs telecom-churn-ml-container || true

      - name: Stop and remove Docker container
        if: always()
        run: docker rm -f telecom-churn-ml-container || true
```

---

## 4. Step-by-Step GitHub Verification Guide

### Step 10 & 11: Inspect the Successful Automated Run
1. Go to [github.com/231fa04f21/telecom-churn-ci](https://github.com/231fa04f21/telecom-churn-ci) $\rightarrow$ **Actions** tab.
2. Select **Telecom Churn ML CI-CD** $\rightarrow$ latest run.
3. Observe the sequential execution:
   - `✓ Checkout repository`
   - `✓ Set up Python`
   - `✓ Upgrade pip`
   - `✓ Install dependencies`
   - `✓ Train telecom churn model`
   - `✓ Check ML quality gate`
   - `✓ Run automated ML tests`
   - `✓ Run prediction application tests`
   - `✓ Build Docker image` (Tagged with commit SHA)
   - `✓ Start Docker container`
   - `✓ Wait for application to become ready` (`Application is ready.`)
   - `✓ Test prediction endpoint` (`Prediction response: {"prediction":"RETAIN","prediction_code":0}`)
   - `✓ Show Docker container logs`
   - `✓ Stop and remove Docker container`
4. Result: **Green Checkmark (SUCCESS)**.

---

### Step 19: Controlled Failure Demonstration (Wrong Port)
1. On GitHub, edit `.github/workflows/ml-ci.yml`.
2. In the `Wait for application to become ready` step, modify line 53:
   ```yaml
   # Change from port 5000 to 5001:
   if curl --fail --silent http://localhost:5001/health; then
   ```
3. Commit with message: `Demonstrate Docker health check failure`.
4. Observe the CI run in the Actions tab:
   - Docker image builds and container starts (`✓`).
   - `Wait for application to become ready` retries 15 times and fails (`❌`):
     ```text
     Waiting for application... attempt 15
     Application did not become ready.
     Error: Process completed with exit code 1.
     ```
   - `Show Docker container logs` executes automatically due to `if: always()`.
   - `Stop and remove Docker container` executes automatically to prevent leaked containers.

---

### Step 20: Restore and Verify
1. Edit `.github/workflows/ml-ci.yml` and restore port `5000`:
   ```yaml
   if curl --fail --silent http://localhost:5000/health; then
   ```
2. Commit with message: `Restore Docker health check port`.
3. Verify that the workflow returns to **Green (SUCCESS)**.

---

## 5. Local Terminal Commands for Screenshots

If you want to run and capture local screenshots of the Docker container lifecycle:

### Command 1: Re-build Image
```powershell
docker build -t telecom-churn-ml:1.0 .
```

### Command 2: List Local Images
```powershell
docker images telecom-churn-ml
```

### Command 3: Start Container with Port Mapping
```powershell
docker run -d --name telecom-churn-ml-container -p 5000:5000 telecom-churn-ml:1.0
```

### Command 4: Check Running Container
```powershell
docker ps
```

### Command 5: Health Check
```powershell
Invoke-RestMethod -Uri http://localhost:5000/health -Method Get
```

### Command 6: Low-Risk Prediction (RETAIN)
```powershell
$body = @{ age = 25; num_dependents = 4; estimated_salary = 140000; calls_made = 90; sms_sent = 50; data_used = 9000 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -Body $body
```

### Command 7: High-Risk Prediction (CHURN)
```powershell
$body = @{ age = 70; num_dependents = 0; estimated_salary = 30000; calls_made = 5; sms_sent = 2; data_used = 100 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -Body $body
```

### Command 8: View Container Logs
```powershell
docker logs telecom-churn-ml-container
```

### Command 9: Cleanup Container
```powershell
docker stop telecom-churn-ml-container ; docker rm telecom-churn-ml-container
```

---

## 6. Screenshots Checklist to Preserve

- [ ] 1. Repository file tree with `Dockerfile`, `.dockerignore`, `app.py`, and `ml-ci.yml`.
- [ ] 2. Updated GitHub Actions workflow showing automated Docker build and test steps.
- [ ] 3. Successful `Build Docker image` log in Actions.
- [ ] 4. Successful `Start Docker container` log in Actions.
- [ ] 5. Successful `Wait for application to become ready` log displaying `Application is ready.`
- [ ] 6. Successful `Test prediction endpoint` log displaying JSON prediction response.
- [ ] 7. Complete green GitHub Actions workflow run.
- [ ] 8. Controlled failure showing `Wait for application to become ready` in red (exit code 1).
- [ ] 9. Container logs displayed during the failed run.
- [ ] 10. Final corrected successful run after restoring port 5000.

---

## 7. Next Practical Preview

**Practical-8: Push Validated Docker Image to Container Registry (GHCR)**:  
Practical 8 will authenticate to GitHub Container Registry (GHCR) and automatically push the verified Docker image so it can be deployed to production environments.
