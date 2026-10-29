# PRACTICAL - 9: Automate Docker Image Build, Test, and Publish to GHCR Using GitHub Actions

**Course**: MLOps Practical Series | Telecom Churn Prediction  
**Continuation from**: Practical-8: Publish the Tested Docker Image to GHCR  
**Running Project**: Telecom Churn Prediction  
**Workflow File**: `.github/workflows/docker-publish.yml`  
**Registry Host**: `ghcr.io`  
**Target Package**: `ghcr.io/231fa04f21/telecom-churn-prediction`  

---

## 1. Aim & Practical Focus

- **Aim**: To automate the build, test, and publication of the Telecom Churn Prediction Docker image using GitHub Actions so that every approved push to the `main` branch follows a repeatable CI/CD workflow and publishes to GitHub Container Registry (GHCR) only after the container test succeeds.
- **MLOps Core Concept**: Manual image building, testing, and pushing (as performed in Practical 8) introduces human error, environment drift, and lack of traceability. Automating this release path within GitHub Actions guarantees that every published image is built from verified version-controlled source code, passes automated runtime health/smoke gates, and is tagged with an immutable Git commit SHA for full traceability and rollback capability.

```
Developer pushes to main (or triggers workflow_dispatch)
                       │
                       ▼
GitHub Actions runner starts (ubuntu-latest)
                       │
                       ▼
Checkout repository (actions/checkout@v4)
                       │
                       ▼
Build Docker image from committed Dockerfile
                       │
                       ▼
Start temporary test container (telecom-churn-ci on port 5000)
                       │
                       ▼
Poll /health endpoint (up to 20 attempts)
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
    [Check Fails]               [Check Passes]
         │                           │
  Workflow halts                     ▼
  No image published            Optional prediction smoke test (/predict)
                                     │
                                     ▼
                                Cleanup temporary test container (if: always())
                                     │
                                     ▼
                                Authenticate to ghcr.io using GITHUB_TOKEN
                                     │
                                     ▼
                                Tag image: :latest and :sha-<commit-SHA>
                                     │
                                     ▼
                                Push tested image to GitHub Container Registry (GHCR)
                                     │
                                     ▼
                                Verified package updated on GitHub
```

---

## 2. Naming Conventions Used in This Practical

| Item | Value / Convention |
|:---|:---|
| **Workflow File** | `.github/workflows/docker-publish.yml` |
| **Workflow Name** | `Build, Test and Publish Telecom Churn Prediction` |
| **Trigger Branch** | `main` (and `workflow_dispatch` for manual runs) |
| **Local CI Image** | `telecom-churn-prediction:ci` |
| **GHCR Registry** | `ghcr.io` |
| **GitHub Namespace** | `231fa04f21` |
| **GHCR Package Name** | `telecom-churn-prediction` |
| **Convenience Tag** | `latest` |
| **Traceability Tag** | `sha-<full Git commit SHA>` |
| **Container Test Name** | `telecom-churn-ci` |
| **API Port** | `5000` |
| **Health Endpoint** | `/health` |
| **Prediction Endpoint**| `/predict` |

---

## 3. Step-by-Step Execution Guide

### Step 1 - Confirm the Repository State
Confirm that all necessary runtime files are committed into the repository:
- `Dockerfile`
- `app.py`
- `telecom_churn_model.pkl` (trained model artifact)
- `metrics.json`
- `requirements.txt`
- `test_payload.json`

The GitHub-hosted CI runner can only build files committed to the repository.

---

### Step 2 - Grant the Repository Access to the Existing GHCR Package
Because Practical-8 created the GHCR package manually with a Personal Access Token before this automated workflow, ensure the repository containing the workflow is authorized to publish new versions to that package:

1. Open your GitHub account packages page: `https://github.com/users/231fa04f21/packages/container/package/telecom-churn-prediction`
2. Click **Package settings** (on the right sidebar).
3. Scroll to **Manage Actions access**.
4. Click **Add repository** and select `231fa04f21/telecom-churn-ci`.
5. Set the role to **Write** and save.

*(Note: If the package was linked to the repository automatically, verify that Write permission is selected).*

---

### Step 3 - Create `.github/workflows/docker-publish.yml`

```yaml
name: Build, Test and Publish Telecom Churn Prediction

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: telecom-churn-prediction

jobs:
  build-test-publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t $IMAGE_NAME:ci .

      - name: Start test container
        run: |
          docker run -d \
            --name telecom-churn-ci \
            -p 5000:5000 \
            $IMAGE_NAME:ci

      - name: Test API health endpoint
        run: |
          for attempt in {1..20}; do
            if curl --fail --silent http://localhost:5000/health; then
              echo "Health check passed."
              exit 0
            fi
            echo "Waiting for API..."
            sleep 3
          done
          echo "Health check failed."
          docker logs telecom-churn-ci
          exit 1

      - name: Test prediction endpoint
        run: |
          curl --fail --silent \
            -X POST http://localhost:5000/predict \
            -H "Content-Type: application/json" \
            --data @test_payload.json

      - name: Remove test container
        if: always()
        run: docker rm -f telecom-churn-ci || true

      - name: Create lowercase GHCR image name
        run: |
          IMAGE_ID="${REGISTRY}/${{ github.repository_owner }}/${IMAGE_NAME}"
          IMAGE_ID=$(echo "$IMAGE_ID" | tr '[:upper:]' '[:lower:]')
          echo "IMAGE_ID=$IMAGE_ID" >> "$GITHUB_ENV"

      - name: Log in to GHCR
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
            docker login $REGISTRY \
            -u "${{ github.actor }}" \
            --password-stdin

      - name: Tag tested image
        run: |
          docker tag $IMAGE_NAME:ci $IMAGE_ID:latest
          docker tag $IMAGE_NAME:ci $IMAGE_ID:sha-${{ github.sha }}

      - name: Push tested image to GHCR
        run: |
          docker push $IMAGE_ID:latest
          docker push $IMAGE_ID:sha-${{ github.sha }}
```

---

### Step 4 - Commit and Push the Workflow
In PowerShell:
```powershell
git add .
git commit -m "Add Docker CI/CD workflow for GHCR publishing"
git push origin main
```

---

### Step 5 - Monitor the GitHub Actions Run
1. Open the repository on GitHub: `https://github.com/231fa04f21/telecom-churn-ci`.
2. Click on the **Actions** tab.
3. Select the workflow run for **`Add Docker CI/CD workflow for GHCR publishing`**.
4. Inspect each step:
   - **Checkout repository**: Clones the repo at the push commit.
   - **Build Docker image**: Runs `docker build -t telecom-churn-prediction:ci .`.
   - **Start test container**: Launches `telecom-churn-ci` in detached mode.
   - **Test API health endpoint**: Verifies HTTP 200 from `/health`.
   - **Test prediction endpoint**: Sends `test_payload.json` and receives prediction response.
   - **Remove test container**: Cleans up runner resources.
   - **Log in to GHCR**: Uses the ephemeral `GITHUB_TOKEN`.
   - **Tag tested image**: Tags as `:latest` and `:sha-<commit>`.
   - **Push tested image to GHCR**: Pushes both tags to GitHub Container Registry.

---

### Step 6 - Verify the Automated GHCR Package Version
1. Open GitHub Packages: `https://github.com/users/231fa04f21/packages/container/package/telecom-churn-prediction`.
2. Confirm the new package version created by GitHub Actions.
3. Confirm both **`latest`** and **`sha-<commit-SHA>`** tags are visible.

---

### Step 7 - Simulate a Second Code Update (Automated Repeatability Test)
Make a documented update (e.g. updating a message in `README.md` or version string in `app.py`):
```powershell
git add .
git commit -m "Update Telecom Churn application documentation"
git push origin main
```
1. Open the Actions tab and verify a second workflow run triggers automatically.
2. Verify the new run completes successfully.
3. Confirm that the `latest` tag moves to the new commit, while the previous version remains preserved under its unique `sha-<commit>` tag.

---

### Step 8 - Pull Verification of the Automated Image
```powershell
docker pull ghcr.io/231fa04f21/telecom-churn-prediction:latest
docker run -d --name telecom-churn-automated -p 5000:5000 ghcr.io/231fa04f21/telecom-churn-prediction:latest
Invoke-RestMethod -Uri http://localhost:5000/health -Method Get
docker rm -f telecom-churn-automated
```

---

## 4. Observation Table

| Checkpoint | Expected Observation | Student Record | Result |
|:---|:---|:---|:---:|
| **Workflow file** | `docker-publish.yml` exists under `.github/workflows` | Configured with `push: branches: [main]` and `workflow_dispatch` | PASS |
| **Trigger** | Push to `main` starts a run automatically | GitHub Actions triggered immediately upon push | PASS |
| **Build** | Telecom Churn Docker image builds successfully | Runner executes `docker build -t telecom-churn-prediction:ci .` | PASS |
| **Container test** | Temporary container starts on the runner | Container `telecom-churn-ci` starts listening on port 5000 | PASS |
| **Health gate** | `/health` succeeds before publishing | Polling loop detects HTTP 200 OK (`{"service":"telecom-churn-prediction","status":"ok"}`) | PASS |
| **Prediction smoke test** | `/predict` endpoint returns valid response | Test payload evaluated and returns `prediction: CHURN` | PASS |
| **GHCR login** | Registry authentication succeeds using `GITHUB_TOKEN` | Ephemeral `GITHUB_TOKEN` logs in with `Login Succeeded` | PASS |
| **latest tag** | New tested image is pushed as `latest` | `latest` tag published and updated on GHCR | PASS |
| **SHA tag** | `sha-<commit>` tag is visible in GHCR | Commit SHA tag generated for permanent traceability | PASS |
| **Second update** | A later push starts another workflow automatically | Second commit triggers build-test-publish autonomously | PASS |
| **Failure understanding** | A failed test prevents later publish steps | Health check failure exits 1, skipping all publish steps | PASS |

---

## 5. Practical Deliverables & Screenshots Checklist

- [ ] 1. Screenshot of the Telecom Churn repository showing `.github/workflows/docker-publish.yml`.
- [ ] 2. Copy of the final `docker-publish.yml` workflow file.
- [ ] 3. Screenshot of the first successful GitHub Actions run.
- [ ] 4. Screenshot showing the successful Docker build step.
- [ ] 5. Screenshot showing the successful API health-test step.
- [ ] 6. Screenshot showing GHCR login/push success without exposing any token.
- [ ] 7. Screenshot of the GHCR package showing `latest` and `sha-<commit>` tags.
- [ ] 8. Screenshot of the second workflow run triggered by a later code update.
- [ ] 9. Completed observation table.

---

## 6. Viva / Discussion Questions & Answers

1. **What is GitHub Actions?**  
   A continuous integration and continuous delivery (CI/CD) platform integrated into GitHub that automates software workflows, builds, tests, and deployments directly on events like `push` or `pull_request`.

2. **What is a workflow in GitHub Actions?**  
   A configurable automated process defined in a YAML file inside `.github/workflows/` that consists of one or more jobs executed sequentially or in parallel on runner environments.

3. **Why is the workflow stored under `.github/workflows`?**  
   This is the standard GitHub convention and discovery path. GitHub's workflow orchestration engine automatically scans this directory to register and parse workflow triggers.

4. **What event triggers this practical automatically?**  
   A `push` event to the `main` branch:
   ```yaml
   on:
     push:
       branches: ["main"]
   ```

5. **What is `workflow_dispatch` used for?**  
   It enables manual triggering of the workflow from the GitHub Actions web interface or API, useful for testing, debugging, or ad-hoc releases without modifying code.

6. **Why is the Docker image rebuilt on the CI runner?**  
   To eliminate developer machine dependency ("works on my machine" syndrome), guarantee reproducibility from clean source code, and ensure only committed assets compose the final container image.

7. **What is the purpose of the container health test?**  
   It validates that the application server starts up, initializes dependencies, loads the ML model into memory, binds to the designated port, and responds to HTTP requests inside the container before it is released.

8. **Why must the test run before `docker push`?**  
   It acts as a release quality gate. If the container crashes or fails the health check, the workflow halts and prevents broken images from overwriting the production `latest` tag in the registry.

9. **What happens to later steps when the health test fails?**  
   GitHub Actions aborts subsequent steps by default. The GHCR login, tagging, and `docker push` steps are skipped, protecting the registry from corrupt images.

10. **Why is `if: always()` used for the container cleanup step?**  
    `if: always()` guarantees that the temporary test container is stopped and removed even if the preceding health check or prediction test fails, ensuring the runner environment is not left in a dirty state.

11. **What is `GITHUB_TOKEN`?**  
    An automatically generated, short-lived authentication token provided by GitHub Actions for each workflow run. It allows the runner to authenticate with GitHub APIs and GitHub Container Registry without storing hard-coded credentials.

12. **Why are `contents: read` and `packages: write` declared explicitly?**  
    They follow the security principle of least privilege. The workflow is restricted to reading repository code (`contents: read`) and uploading container images (`packages: write`), preventing unauthorized access to issues, secrets, or pull requests.

13. **How is `GITHUB_TOKEN` different from the Personal Access Token used in Practical-8?**  
    A PAT is long-lived, belongs to a specific user account, and requires manual rotation and secret management. `GITHUB_TOKEN` is dynamically generated per workflow run, scoped strictly to the repository, expires automatically when the job completes, and requires zero manual credential storage.

14. **Why might an existing GHCR package need Manage Actions access for the repository?**  
    When a package is first published manually via PAT (in Practical 8), GitHub creates it with user ownership. To allow automated workflows running in a repository to publish new versions to that pre-existing package, the repository must be granted `Write` permissions under package settings.

15. **Why is the GHCR image name converted to lowercase?**  
    The Open Container Initiative (OCI) and Docker specifications mandate that image names and repository namespaces must consist solely of lowercase alphanumeric characters, dots, dashes, and underscores. Uppercase characters cause registry push failures.

16. **What is the purpose of the `latest` tag?**  
    It serves as a floating convenience pointer referencing the most recent successfully validated build, allowing consumer environments to pull the newest version without querying specific commit IDs.

17. **What is the advantage of a commit-SHA image tag?**  
    It provides immutable traceability. Each image is permanently linked to the exact Git commit that produced it, enabling precise auditability, exact environment reproduction, and trivial rollbacks to any prior version.

18. **How does a commit-specific image tag improve reproducibility and rollback?**  
    If a new release exhibits defects, operators can instantly point deployment manifests to a prior known-good `sha-<commit>` tag without rebuilding or modifying code.

19. **Why should secrets never be placed in workflow files or Docker images?**  
    Workflow files are tracked in version control, and Docker image layers can be easily inspected with `docker history` or extraction tools. Embedding secrets exposes them to unauthorized users, causing severe security compromises.

20. **What additional checks could be added before production deployment?**  
    Static application security testing (SAST), container vulnerability scans (e.g., Trivy or Grype), performance load testing, latency benchmarking, model drift detection, and canary/blue-green deployment gates.

---

## 7. Result

An automated GitHub Actions CI/CD workflow (`docker-publish.yml`) was successfully configured for the Telecom Churn Prediction project. The pipeline automatically checks out the repository upon push to `main`, builds the Docker image from source, boots and verifies a temporary container using automated health and prediction checks as a quality release gate, authenticates securely to GHCR via ephemeral `GITHUB_TOKEN`, creates traceable `latest` and `sha-<commit>` tags, and publishes the validated container image to GitHub Container Registry.
