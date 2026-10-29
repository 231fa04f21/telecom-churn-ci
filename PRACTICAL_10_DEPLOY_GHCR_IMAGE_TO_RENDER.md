# PRACTICAL - 10: Deploy the Tested Docker Image from GHCR to Render

**Course**: MLOps Practical Series | Telecom Churn Prediction  
**Continuation from**: Practical-9: Automate Docker Build, Test, and Publish to GHCR  
**Running Project**: Telecom Churn Prediction  
**Image Reference**: `ghcr.io/231fa04f21/telecom-churn-prediction:latest`  
**Hosting Platform**: Render Cloud (render.com)  
**Service Type**: Web Service (Existing Image)  

---

## 1. Aim & Practical Focus

- **Aim**: To deploy the tested Telecom Churn Prediction container image from GitHub Container Registry (GHCR) to **Render** as a publicly accessible Web Service, and verify the live public root, health, and prediction API endpoints.
- **MLOps Core Concept**: A mature MLOps pipeline decouples **artifact production** (CI/CD in GitHub Actions) from **cloud runtime deployment** (Render). The cloud host pulls the pre-built, pre-tested immutable container image directly from GHCR rather than cloning source code or retraining models on production servers.

```
Source Code (GitHub Repository: telecom-churn-ci)
                       │
                       ▼
GitHub Actions CI/CD (Practical-9: docker-publish.yml)
                       │
                       ▼
Docker Build + Container Health Gate (/health) + Prediction Test (/predict)
                       │
                       ▼
GitHub Container Registry (ghcr.io/231fa04f21/telecom-churn-prediction:latest)
                       │
                       │ (Image Pull)
                       ▼
Render Cloud Platform (Existing Image Web Service)
                       │
                       ▼
Public HTTPS URL: https://<service-name>.onrender.com
                       │
     ┌─────────────────┼─────────────────┐
     ▼                 ▼                 ▼
GET /             GET /health       POST /predict
(Service Status)  (Health Check)   (Live ML Inference)
```

---

## 2. Service and Configuration Values

| Setting | Recommended Value | Purpose |
|:---|:---|:---|
| **Service Type** | Web Service | Exposes an HTTP/HTTPS internet endpoint |
| **Source Type** | Existing Image | Pulls the pre-built GHCR image directly |
| **Image URL** | `ghcr.io/231fa04f21/telecom-churn-prediction:latest` | References the tested image from Practical 9 |
| **Service Name** | `telecom-churn-prediction` | Identifies service and forms `<name>.onrender.com` |
| **Region** | Choose closest (e.g. Singapore, Frankfurt, Oregon) | Geographic server location |
| **Instance Type** | Free ($0/month) | Lab compute resource |
| **Environment Variable** | `PORT` = `5000` | Informs Render of container's internal listening port |
| **Health Check Path** | `/health` | Allows Render to verify application health |
| **Root Endpoint** | `/` | Confirms API is alive |
| **Prediction Endpoint**| `/predict` | Ingests JSON customer features and returns churn prediction |

---

## 3. GHCR Image Visibility (Public vs. Private)

Render needs to pull your container image from `ghcr.io`.

### Recommended Option: Make Package Public (Fastest & Simplest)
1. Go to: `https://github.com/users/231fa04f21/packages/container/telecom-churn-prediction/settings`
2. Scroll to the bottom to **Danger Zone**.
3. Under **Change package visibility**, click **Change visibility** $\rightarrow$ select **Public** $\rightarrow$ Confirm.
4. Render will now be able to pull the image directly without needing credentials!

### Alternative Option: If Package is Kept Private
If you keep the package private:
1. In Render, when entering the image URL, click **Add credential**.
2. Select **GitHub** as the registry.
3. Username: `231fa04f21`
4. Token: Your GitHub Personal Access Token (classic) with `read:packages` permission.

---

## 4. Step-by-Step Deployment Procedure on Render

### Step 1 - Confirm the Latest GHCR Image
1. Open GitHub Packages: `https://github.com/users/231fa04f21/packages/container/package/telecom-churn-prediction`
2. Confirm that the `latest` tag exists and matches the commit from the successful Practical 9 workflow run.

---

### Step 2 - Sign In to Render and Create a Web Service
1. Navigate to **[https://dashboard.render.com](https://dashboard.render.com)** and log in (or sign up with GitHub).
2. Click the **+ New** button (top right) $\rightarrow$ select **Web Service**.
3. Under the source options, choose **"Existing Image"** (do NOT choose Git Repository).

---

### Step 3 - Enter the Image Reference
Enter the complete GHCR image URL:
```text
ghcr.io/231fa04f21/telecom-churn-prediction:latest
```
Click **Next** (or **Connect**).

---

### Step 4 - Configure the Service
Fill in the deployment settings:
- **Name**: `telecom-churn-prediction` (or `telecom-churn-<your-name>`)
- **Region**: Any available free region (e.g. Singapore, Frankfurt, Ohio, Oregon)
- **Instance Type**: **Free**
- Scroll to **Advanced** (or Environment Variables):
  - Click **Add Environment Variable**:
    - **Key**: `PORT`
    - **Value**: `5000`
  - Set **Health Check Path**: `/health`

Click **Create Web Service**.

---

### Step 5 - Monitor Deployment Events & Logs
1. Render will begin pulling the image from GHCR:
   ```text
   ==> Pulling image ghcr.io/231fa04f21/telecom-churn-prediction:latest
   ==> Starting service with 'python app.py'
   ==> Running on http://0.0.0.0:5000 (Press CTRL+C to quit)
   ==> Detected port 5000
   ==> GET /health 200
   ==> Your service is live 🎉
   ```
2. Wait until the status badge displays **Live** with a green dot.
3. Copy your public service URL:
   ```text
   https://<your-service-name>.onrender.com
   ```

---

## 5. Live Endpoint Verification

Once live, test all public endpoints using your browser or PowerShell:

### Test 1 - Root Endpoint (`GET /`)
In browser or PowerShell:
```powershell
Invoke-RestMethod -Uri "https://<your-service-name>.onrender.com/" -Method Get
```
**Expected JSON Response**:
```json
{
  "service": "telecom-churn-prediction",
  "status": "ok"
}
```

---

### Test 2 - Health Endpoint (`GET /health`)
```powershell
Invoke-RestMethod -Uri "https://<your-service-name>.onrender.com/health" -Method Get
```
**Expected JSON Response**:
```json
{
  "service": "telecom-churn-prediction",
  "status": "ok"
}
```

---

### Test 3 - Live Prediction Endpoint (`POST /predict`)
Send a customer feature payload to the cloud API:

```powershell
Invoke-RestMethod -Uri "https://<your-service-name>.onrender.com/predict" -Method Post -ContentType "application/json" -Body '{"age": 70, "num_dependents": 0, "estimated_salary": 30000, "calls_made": 5, "sms_sent": 2, "data_used": 100}'
```

**Expected JSON Response**:
```text
prediction prediction_code
---------- ---------------
CHURN                    1
```

#### Test a Low-Risk Customer (`RETAIN`):
```powershell
Invoke-RestMethod -Uri "https://<your-service-name>.onrender.com/predict" -Method Post -ContentType "application/json" -Body '{"age": 25, "num_dependents": 4, "estimated_salary": 140000, "calls_made": 90, "sms_sent": 50, "data_used": 9000}'
```

**Expected JSON Response**:
```text
prediction prediction_code
---------- ---------------
RETAIN                   0
```

---

## 6. Verifying the Cloud Redeploy Cycle (Step 16)

Image-backed Render services do not automatically redeploy merely because the mutable `latest` tag in GHCR changes. To update the service when a new image is pushed:

1. Push a commit to GitHub to let Practical 9 publish an updated image to GHCR.
2. In the Render Dashboard, open your service.
3. Click **Manual Deploy** (top right) $\rightarrow$ select **"Deploy latest reference"**.
4. Observe Render pulling the new image and re-initiating the service with zero configuration changes.

---

## 7. Observation Table

| Checkpoint | Expected Observation | Student Record | Result |
|:---|:---|:---|:---:|
| **GHCR latest image** | Latest tested image exists after Practical 9 | Tag `latest` verified in GHCR | PASS |
| **Render source** | `Existing Image` is selected | Deployed via image reference without source rebuild | PASS |
| **Image access** | Render verifies access to GHCR image | Image pulled successfully from registry | PASS |
| **Service deployment** | Web Service becomes live/running | Status indicates `Live` with green indicator | PASS |
| **Public URL** | Unique `onrender.com` URL is assigned | `https://telecom-churn-prediction-h5fs.onrender.com` | PASS |
| **Root endpoint** | `/` returns expected running status | HTTP 200 OK with `service` and `status` | PASS |
| **Health endpoint** | `/health` returns expected health status | HTTP 200 OK used by cloud orchestrator | PASS |
| **Prediction endpoint** | `/predict` returns valid prediction | Evaluates feature payload and returns CHURN/RETAIN | PASS |
| **Logs** | No repeated runtime error present | Flask server logs visible with HTTP 200 access logs | PASS |
| **Redeployment** | `Deploy latest reference` pulls newly published image | Manual redeploy updates running container to new image | PASS |

---

## 8. Practical Deliverables & Screenshots Checklist

- [ ] 1. Screenshot of the successful Practical-9 GitHub Actions run used for deployment.
- [ ] 2. Screenshot of the GHCR package showing the `latest` image tag.
- [ ] 3. Screenshot of the Render Existing Image configuration without exposing any secret tokens.
- [ ] 4. Screenshot of the successful Render deployment / live service status.
- [ ] 5. Recorded public `onrender.com` service URL.
- [ ] 6. Screenshot of the deployed root endpoint (`GET /`) in browser or terminal.
- [ ] 7. Screenshot of the deployed `/health` endpoint in browser or terminal.
- [ ] 8. Screenshot of a successful `/predict` request and response using PowerShell `Invoke-RestMethod`.
- [ ] 9. Screenshot of relevant Render runtime logs.
- [ ] 10. Screenshot of a later **Manual Deploy $\rightarrow$ Deploy latest reference** run.
- [ ] 11. Completed observation table.

---

## 9. Viva / Discussion Questions & Answers

1. **What is the difference between pushing an image to GHCR and deploying an image to a cloud platform?**  
   Pushing to GHCR is **artifact publication** (storing a versioned, portable container image in a registry). Deploying to a cloud platform is **runtime execution** (provisioning compute instances, pulling the image, running containers, and routing external network traffic to it).

2. **What is an image-backed web service?**  
   A cloud service configured to run directly from a pre-built Docker container image hosted in a registry, rather than building from raw source code repository files on the hosting platform.

3. **Why is the GHCR image reused instead of rebuilding the application on Render?**  
   It ensures absolute immutability and parity. The exact same image artifact that passed CI automated unit tests, quality gates, and container smoke checks in GitHub Actions is deployed, eliminating environment inconsistencies ("works in CI, breaks in production").

4. **Why must the application bind to `0.0.0.0` inside the container?**  
   Binding to `127.0.0.1` (localhost) restricts connections strictly to within the container itself. Binding to `0.0.0.0` instructs the server to accept traffic on all network interfaces, allowing the host platform router/reverse-proxy to forward incoming public requests into the container.

5. **What is the purpose of the `PORT` environment variable on a cloud platform?**  
   Cloud hosts dynamically assign listening ports or use platform routing defaults (e.g. Render defaults to port 10000). Setting `PORT=5000` informs the platform router which container port to forward incoming HTTP/HTTPS traffic to.

6. **Why is `/health` useful during deployment?**  
   The cloud platform orchestrator polls `/health` to verify that the containerized application has initialized and is capable of servicing traffic before switching routing from the old release to the new one.

7. **What is the difference between the root endpoint and the health endpoint?**  
   The root endpoint (`/`) typically serves user-facing entry points, welcome documentation, or landing pages. The `/health` endpoint is specifically designed for automated orchestration probes (load balancers, Kubernetes, Render) to measure service liveness and readiness.

8. **When are GHCR credentials required by Render?**  
   Credentials (a Personal Access Token with `read:packages` scope) are required only if the GHCR package visibility is set to **Private**. Public GHCR packages require no credentials.

9. **What permission is required for a token that only pulls a private GHCR image?**  
   `read:packages`. Applying least privilege, write or delete permissions should never be granted to runtime pull credentials.

10. **Why should a registry token not be included in screenshots or reports?**  
    Tokens are sensitive credentials. Exposing them compromises package registry security, potentially permitting unauthorized access or tampering with hosted container artifacts.

11. **What is an Image Pull Failed error?**  
    An error indicating that the cloud platform was unable to fetch the container image from the registry, usually caused by an incorrect image URL, misspelled tag, private package without credentials, or deleted repository.

12. **What can cause a 502 Bad Gateway error after a container image is deployed?**  
    A 502 error occurs when the cloud reverse-proxy cannot establish a connection with the container. Common causes include: application crashing on startup, binding to `127.0.0.1` instead of `0.0.0.0`, port mismatch between Render configuration and the container's actual listening port, or unhandled runtime exceptions.

13. **Why can a Docker image run locally but fail in a cloud environment?**  
    Due to architecture discrepancies (e.g. ARM64 vs AMD64), hard-coded local file paths, unmapped environment variables, insufficient RAM/CPU quotas, or strict cloud reverse proxy routing requirements.

14. **Does an image-backed Render service automatically redeploy when the `latest` tag changes?**  
    No. Because Docker registries allow mutating tags in-place, Render does not poll the registry for tag changes. A manual redeploy ("Deploy latest reference") or a webhook deploy hook must be triggered.

15. **How is the latest GHCR image redeployed manually on Render?**  
    By opening the service in the Render dashboard, clicking the **Manual Deploy** dropdown button, and selecting **"Deploy latest reference"**.

16. **What is the difference between `latest` and `sha-<commit>` image tags?**  
    `latest` is a floating, mutable pointer to the newest release. `sha-<commit>` is an immutable, frozen snapshot tied permanently to a specific Git commit, guaranteeing 100% reproducibility.

17. **Why are immutable image digests useful for rollback?**  
    Because image digests (SHA256 hashes of the image manifest) cannot be modified or re-tagged. Pointing a deployment to a known digest guarantees exact restoration of a previous stable state.

18. **How do GitHub Actions, GHCR, and Render divide responsibilities in this workflow?**  
    - **GitHub Actions**: Automated CI/CD engine (builds, tests, validates, tags).
    - **GHCR**: Artifact repository (stores and distributes immutable container images).
    - **Render**: Runtime cloud host (pulls images, executes containers, handles public HTTPS routing and domain management).

---

## 10. Result

The tested Telecom Churn Prediction container image (`ghcr.io/231fa04f21/telecom-churn-prediction:latest`) produced and published by GitHub Actions in Practical 9 was deployed to a cloud Render Web Service. The deployed service was verified through public HTTPS requests to `/`, `/health`, and `/predict`, successfully performing machine learning inference in the cloud.

