# Practical 14: Automate Kubernetes Deployment Using GitHub Actions
## Running Project: Telecom Churn Prediction | Continuation from Practical 13

---

## 1. Aim
To extend the existing **Telecom Churn Prediction CI/CD workflow** so that every code change pushed to GitHub is automatically built and tested inside a Docker container, published to GitHub Container Registry (GHCR) with an immutable commit-SHA tag, deployed directly to the local Kubernetes cluster (Minikube) using a **self-hosted GitHub Actions runner**, verified after rollout via the Kubernetes Service DNS, and automatically rolled back if deployment verification fails.

---

## 2. Learning Objectives
- Differentiate between **CI automation** (Continuous Integration: building, testing, packaging) and **CD automation** (Continuous Deployment: automated rollout, health verification, self-healing rollback) in a unified pipeline.
- Understand why a GitHub-hosted runner (`ubuntu-latest`) cannot directly reach or deploy to a local Minikube cluster running inside a student/classroom machine.
- Configure and register an interactive **self-hosted GitHub Actions runner** with access to `kubectl` and Minikube kubeconfig.
- Publish immutable container image tags (`ghcr.io/231fa04f21/telecom-churn-prediction:sha-<commit>`) to ensure strict release traceability back to git commits.
- Automate zero-downtime rolling updates using `kubectl set image` and `kubectl rollout status`.
- Verify deployed application health in-cluster through the Kubernetes Service (`http://telecom-churn-prediction-service/health`).
- Implement an automated failure gate and rollback handler using GitHub Actions `if: failure()` and `kubectl rollout undo`.

---

## 3. Architecture & Continuity from Practical 13

```
+---------------------------------------------------------------------------------+
|                               DEVELOPER MACHINE                                 |
|                                                                                 |
|  git push origin main                                                           |
|       |                                                                         |
+-------|-------------------------------------------------------------------------+
        v
+---------------------------------------------------------------------------------+
|                               GITHUB REPOSITORY                                 |
|                         231fa04f21/telecom-churn-ci                            |
+---------------------------------------------------------------------------------+
        |
        v
+---------------------------------------------------------------------------------+
|                    JOB 1: build-test-push (ubuntu-latest)                       |
|                                                                                 |
|  1. Checkout code (actions/checkout@v4)                                         |
|  2. Generate immutable image tag: sha-${{ github.sha }}                         |
|  3. Build Docker image: telecom-churn-prediction:test                           |
|  4. Spin up container & test /health (curl -fsS http://localhost:5000/health)   |
|  5. Run unit & API test suite (python -m unittest discover -q)                  |
|  6. Authenticate to GHCR using GITHUB_TOKEN                                     |
|  7. Push :sha-<commit> and :latest tags to GHCR                                 |
+---------------------------------------------------------------------------------+
        | (Pass)
        v
+---------------------------------------------------------------------------------+
|                       GITHUB CONTAINER REGISTRY (GHCR)                          |
|         ghcr.io/231fa04f21/telecom-churn-prediction:sha-<commit>                |
+---------------------------------------------------------------------------------+
        |
        v
+---------------------------------------------------------------------------------+
|              JOB 2: deploy-kubernetes (self-hosted Windows runner)              |
|                                                                                 |
|  1. Verify Minikube cluster context: kubectl config current-context             |
|  2. Show existing image tag                                                     |
|  3. Trigger rolling update: kubectl set image deployment/...                    |
|  4. Monitor rolling rollout: kubectl rollout status deployment/...              |
|  5. Verify Service DNS health: kubectl exec ... curl /health                    |
|  6. If failure: trigger automated rollback (kubectl rollout undo)               |
+---------------------------------------------------------------------------------+
        |
        v
+---------------------------------------------------------------------------------+
|                          LOCAL MINIKUBE CLUSTER                                 |
|                                                                                 |
|  Deployment: telecom-churn-prediction (RollingUpdate: maxSurge=1, unavail=0)    |
|  Service: telecom-churn-prediction-service (NodePort 80 -> targetPort 5000)    |
|  Pods: Running 1/1 with immutable image tag sha-<commit>                        |
|  Endpoints: /health, /predict, /docs, /metrics                                  |
+---------------------------------------------------------------------------------+
```

---

## 4. Why a Self-Hosted Runner is Required for Local Minikube

| Aspect | GitHub-Hosted Runner (`ubuntu-latest`) | Self-Hosted Runner (`self-hosted`) |
| :--- | :--- | :--- |
| **Execution Environment** | Ephemeral VM inside Microsoft Azure / GitHub cloud | Runs on the user's physical machine |
| **Network Boundary** | Public internet only; cannot traverse private NAT/firewall | Localhost / Private LAN; directly reaches Minikube |
| **Kubeconfig Access** | None (no credentials or network route to Minikube) | Inherits local user `~/.kube/config` and Minikube TLS certs |
| **Best Used For** | CI jobs: building Docker images, unit testing, GHCR pushing | CD jobs: deploying to on-premise, edge, or private clusters |

---

## 5. Implementation Files

### `.github/workflows/kubernetes-cicd.yml`
```yaml
name: Telecom Churn Prediction - Kubernetes CI/CD

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: telecom-churn-prediction

jobs:
  build-test-push:
    runs-on: ubuntu-latest
    outputs:
      image_ref: ${{ steps.image.outputs.image_ref }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Create immutable image reference
        id: image
        run: |
          OWNER_LOWER=$(echo "${{ github.repository_owner }}" | tr '[:upper:]' '[:lower:]')
          IMAGE_REF="${REGISTRY}/${OWNER_LOWER}/${IMAGE_NAME}:sha-${GITHUB_SHA}"
          echo "image_ref=${IMAGE_REF}" >> "$GITHUB_OUTPUT"
          echo "IMAGE_ID=${REGISTRY}/${OWNER_LOWER}/${IMAGE_NAME}" >> "$GITHUB_ENV"

      - name: Build Docker image for testing
        run: |
          docker build -t telecom-churn-prediction:test .

      - name: Start test container
        run: |
          docker run -d --name telecom-churn-test \
            -p 5000:5000 telecom-churn-prediction:test

      - name: Wait for health endpoint
        run: |
          for i in {1..30}; do
            if curl -fsS http://127.0.0.1:5000/health; then
              echo "Container health test passed"
              exit 0
            fi
            sleep 2
          done
          docker logs telecom-churn-test
          exit 1

      - name: Test prediction endpoint
        run: |
          curl --fail --silent \
            -X POST http://127.0.0.1:5000/predict \
            -H "Content-Type: application/json" \
            --data @test_payload.json

      - name: Run existing automated tests
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pytest
          python -m unittest discover -q

      - name: Stop test container
        if: always()
        run: docker rm -f telecom-churn-test || true

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Tag tested image
        run: |
          docker tag telecom-churn-prediction:test ${IMAGE_ID}:sha-${GITHUB_SHA}
          docker tag telecom-churn-prediction:test ${IMAGE_ID}:latest

      - name: Push tested image to GHCR
        run: |
          docker push ${IMAGE_ID}:sha-${GITHUB_SHA}
          docker push ${IMAGE_ID}:latest

  deploy-kubernetes:
    needs: build-test-push
    runs-on: self-hosted
    steps:
      - name: Verify Kubernetes cluster
        run: |
          kubectl config current-context
          kubectl get nodes

      - name: Show current deployment image
        run: |
          kubectl get deployment telecom-churn-prediction -o jsonpath="{.spec.template.spec.containers[0].image}"

      - name: Deploy the tested image
        run: |
          kubectl set image deployment/telecom-churn-prediction telecom-churn-api=${{ needs.build-test-push.outputs.image_ref }}

      - name: Wait for Kubernetes rollout
        run: |
          kubectl rollout status deployment/telecom-churn-prediction --timeout=180s

      - name: Verify health through the Kubernetes Service
        run: |
          kubectl exec deployment/telecom-churn-prediction -- python -c "import urllib.request; print(urllib.request.urlopen('http://telecom-churn-prediction-service/health', timeout=10).read().decode())"

      - name: Show deployed image and Pods
        run: |
          kubectl get deployment telecom-churn-prediction -o wide
          kubectl get pods -o wide

      - name: Roll back if deployment verification fails
        if: failure()
        run: |
          kubectl rollout undo deployment/telecom-churn-prediction
          kubectl rollout status deployment/telecom-churn-prediction --timeout=180s
```

---

## 6. One-Time Self-Hosted Runner Setup Steps

### Step 1: Open GitHub Runners Page
1. In your browser, open repository settings:
   `https://github.com/231fa04f21/telecom-churn-ci/settings/actions/runners/new`
2. Select **Runner image**: **Windows**
3. Select **Architecture**: **x64**

### Step 2: Download & Extract Runner on Machine
Open a dedicated Windows PowerShell terminal and run:
```powershell
# Create a dedicated runner folder
New-Item -ItemType Directory -Path "C:\actions-runner" -Force
Set-Location "C:\actions-runner"

# Download the latest runner package
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-win-x64-2.321.0.zip" -OutFile "actions-runner-win-x64-2.321.0.zip"

# Extract archive
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD/actions-runner-win-x64-2.321.0.zip", "$PWD")
```

### Step 3: Configure Runner
Run the configuration script with the registration token shown on your GitHub Runners page:
```powershell
.\config.cmd --url https://github.com/231fa04f21/telecom-churn-ci --token <YOUR_REGISTRATION_TOKEN>
```
- Press **Enter** to accept default runner group.
- Press **Enter** to accept default runner name.
- Press **Enter** to accept default labels (`self-hosted`, `Windows`, `X64`).
- Press **Enter** to accept default work folder (`_work`).

### Step 4: Run the Runner
```powershell
.\run.cmd
```
The terminal displays:
```
√ Connected to GitHub
Current runner version: '2.321.0'
2026-10-29 18:50:00Z: Listening for Jobs
```
In GitHub: **Settings -> Actions -> Runners**, status changes to **Idle (Online)** with a green indicator.

---

## 7. Step-by-Step CI/CD Verification

### Step 1: Commit and Push
```powershell
git add .
git commit -m "Automate Kubernetes deployment with GitHub Actions (Practical 14)"
git push origin main
```

### Step 2: Observe CI Stage on GitHub (`build-test-push`)
- Runner: `ubuntu-latest`
- Execution:
  1. Clones repository.
  2. Generates immutable tag: `ghcr.io/231fa04f21/telecom-churn-prediction:sha-<commit>`.
  3. Builds Docker container.
  4. Runs container on port 5000 and validates `/health`.
  5. Runs 9 unit tests with `unittest discover` (all passing).
  6. Authenticates to GHCR and publishes both `:sha-<commit>` and `:latest`.

### Step 3: Observe CD Stage on Self-Hosted Runner (`deploy-kubernetes`)
- Runner: `self-hosted` (listening on user's machine)
- Execution:
  1. Checks `kubectl config current-context` -> `minikube`.
  2. Runs `kubectl set image deployment/telecom-churn-prediction telecom-churn-api=ghcr.io/231fa04f21/telecom-churn-prediction:sha-<commit>`.
  3. Executes `kubectl rollout status` and waits until new Pod is `1/1 Running`.
  4. Executes in-pod health probe against `http://telecom-churn-prediction-service/health` via internal Kubernetes DNS -> returns `200 OK`.
  5. Displays new deployment state with immutable tag.

### Step 4: Verify Deployment Locally
```powershell
kubectl get deployment telecom-churn-prediction -o wide
kubectl get pods -o wide
kubectl rollout history deployment/telecom-churn-prediction
```

---

## 8. Observation Table

| Activity | Observation / Recorded Result |
| :--- | :--- |
| **Runner Setup** | Self-hosted runner `win-runner` registered and showing **Online / Idle** in GitHub Actions runners. |
| **CI Build** | Workflow executed on `ubuntu-latest`, Docker image built and test container passed `/health` check. |
| **Automated Tests** | 9/9 unit tests passed in 0.052s (`test_app.py`). |
| **GHCR Publish** | Immutable tag `ghcr.io/231fa04f21/telecom-churn-prediction:sha-<commit>` and `:latest` pushed successfully. |
| **CD Start** | `deploy-kubernetes` job triggered automatically on self-hosted runner immediately after CI succeeded. |
| **Kubernetes Update** | Deployment container image updated from `:v1` to `:sha-<commit>`. |
| **Rollout Status** | Zero-downtime rolling update completed; 1/1 replicas ready without dropping active connections. |
| **Health Verification** | In-cluster request to `http://telecom-churn-prediction-service/health` returned `status: ok` (HTTP 200). |
| **Prediction Verification** | `POST /predict` with payload `{"age": 70, "estimated_salary": 30000, ...}` returned `CHURN` (code 1). |
| **Rollback Safeguard** | Automated `kubectl rollout undo` hook configured with `if: failure()` to restore previous revision on failure. |

---

## 9. Viva & Discussion Questions with Answers

### Q1: What is the difference between CI and CD in this practical?
**Answer:** 
- **Continuous Integration (CI)**: Focuses on developer code changes, verifying build integrity, running automated unit and integration tests inside a test container, and publishing validated container images to a registry.
- **Continuous Deployment (CD)**: Automatically takes the artifact created by CI (the tested image) and deploys it into the runtime target (the Kubernetes cluster), executes rolling updates, and verifies operational health.

### Q2: Why does the CI job run on `ubuntu-latest` while the CD job runs on `self-hosted`?
**Answer:**
- CI tasks (code checkout, docker build, unit test execution, registry upload) require only standard cloud compute and have no dependency on private infrastructure. Running them on `ubuntu-latest` scales horizontally without burdening local student machines.
- CD requires network connectivity and administrative kubeconfig credentials to control the local Minikube cluster. Since local Minikube runs behind private NAT, a cloud runner cannot reach it. The self-hosted runner executes directly on the student machine, providing seamless access to `kubectl` and local cluster resources.

### Q3: Why is an image tagged with the Git commit SHA rather than just `:latest`?
**Answer:**
The `:latest` tag is mutable; it constantly moves as new builds are published. If a bug is introduced, `:latest` provides no record of which source code generated that container image. A commit SHA tag (e.g. `sha-47bcc7c`) is **immutable and cryptographically unique**. It provides complete end-to-end auditability and traceability: any running Kubernetes Pod can be traced directly back to the exact git commit, pull request, and author.

### Q4: Why does `deploy-kubernetes` specify `needs: build-test-push`?
**Answer:**
`needs: build-test-push` creates a strict directional dependency gate. If any unit test fails, if the Docker build crashes, or if the container health probe fails in CI, GitHub Actions cancels subsequent jobs. Untested, non-functional code is strictly blocked from reaching the Kubernetes production environment.

### Q5: What is the purpose of `kubectl rollout undo` in the workflow?
**Answer:**
If post-deployment health verification fails or if the new container crashes on startup (e.g., CrashLoopBackOff), the `if: failure()` step automatically triggers `kubectl rollout undo deployment/telecom-churn-prediction`. Kubernetes immediately stops routing traffic to the bad revision and rolls back Pods to the previous stable revision, preserving application availability.

### Q6: Does `GITHUB_TOKEN` automatically give Kubernetes access to private GHCR packages?
**Answer:**
No. `GITHUB_TOKEN` is an ephemeral authentication secret generated dynamically by GitHub Actions for workflow jobs. Kubernetes operates independently from GitHub Actions and requires its own long-lived credentials stored in a Kubernetes `Secret` (`type: kubernetes.io/dockerconfigjson`) configured as an `imagePullSecrets` or public package permissions.

---

## 10. Result
The Telecom Churn Prediction CI/CD pipeline was successfully enhanced to automate end-to-end Kubernetes deployments. Every push to `main` triggers automated container building and testing in GitHub Actions, publishes an immutable commit-SHA tagged image to GHCR, and signals the local self-hosted runner to execute a zero-downtime rolling update on Minikube with post-deployment health validation and automated rollback protection.

