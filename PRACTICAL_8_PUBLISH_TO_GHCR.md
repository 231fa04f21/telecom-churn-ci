# PRACTICAL - 8: Publish the Tested Docker Image to GitHub Container Registry (GHCR)

**Course**: MLOps Practical Series | Student Result Prediction (Customized for Telecom Churn)  
**Continuation from**: Practical-7: Automate Docker Build and Test  
**Local Image Source**: `telecom-churn-ml:1.0`  
**GHCR Package Name**: `telecom-churn-prediction`  
**Registry Host**: `ghcr.io`  

---

## 1. Aim & Practical Focus

- **Aim**: To publish the tested Docker image of the Telecom Churn application from Practical-7 to **GitHub Container Registry (GHCR)**, verify the published package on GitHub, pull the image from GHCR onto a clean environment, run it as a container, and confirm that the prediction API functions identically.
- **MLOps Core Concept**: A container registry acts as the single source of truth for distributable, production-ready ML artifacts. Rather than re-running training or rebuilds on every target machine, deployment platforms pull immutable, tested images directly from the registry.

```
Tested Local Docker Image (telecom-churn-ml:1.0)
                       ↓
GHCR Tagging (ghcr.io/<username>/telecom-churn-prediction:v1 & :latest)
                       ↓
Docker Authentication (docker login ghcr.io)
                       ↓
Docker Push to GitHub Container Registry
                       ↓
Package Stored on GitHub (github.com/<username>?tab=packages)
                       ↓
Docker Pull from Remote Registry
                       ↓
Run Container from Registry Image (telecom-churn-from-ghcr)
                       ↓
Verify Health (/health) & Predict (/predict)
```

---

## 2. Naming Conventions

Replace `<github-username>` with your GitHub username (e.g. `nuthan257p` or `231fa04f21`). Image and package names must be **all lowercase**.

| Item | Name in this Practical |
|:---|:---|
| **Local Source Image** | `telecom-churn-ml:1.0` |
| **GitHub Namespace** | `<github-username>` (e.g., `nuthan257p`) |
| **Package Name** | `telecom-churn-prediction` |
| **Versioned Tag** | `v1` |
| **Latest Tag** | `latest` |
| **Full Versioned Image** | `ghcr.io/<github-username>/telecom-churn-prediction:v1` |
| **Full Latest Image** | `ghcr.io/<github-username>/telecom-churn-prediction:latest` |

---

## 3. Step-by-Step Execution Guide

### Step 1 - Confirm the Tested Local Image
Verify that `telecom-churn-ml:1.0` exists locally:
```powershell
docker images telecom-churn-ml
```

---

### Step 2 - Create GitHub Personal Access Token (PAT) for GHCR
1. Log in to [GitHub](https://github.com).
2. Go to **Settings** (top right profile icon) $\rightarrow$ **Developer Settings** (at the bottom of the left sidebar).
3. Click **Personal access tokens** $\rightarrow$ **Tokens (classic)** $\rightarrow$ **Generate new token (classic)**.
4. Note name: `GHCR Practical 8 Token`.
5. Select Scopes:
   - `write:packages` (Upload packages to GitHub Package Registry)
   - `read:packages` (Download packages from GitHub Package Registry)
   - *(Optional: `delete:packages`)*
6. Click **Generate token** and copy the token string immediately.

---

### Step 3 - Authenticate Docker to GHCR
In PowerShell, authenticate Docker to GitHub Container Registry:
```powershell
echo <YOUR_GITHUB_TOKEN> | docker login ghcr.io -u <github-username> --password-stdin
```
> **Expected Output**: `Login Succeeded`

---

### Step 4 - Tag the Image for GHCR
Tag the tested image with both a version tag (`v1`) and the `latest` tag:

```powershell
docker tag telecom-churn-ml:1.0 ghcr.io/<github-username>/telecom-churn-prediction:v1
docker tag telecom-churn-ml:1.0 ghcr.io/<github-username>/telecom-churn-prediction:latest
```

Verify that both tags appear with the same IMAGE ID:
```powershell
docker images ghcr.io/<github-username>/telecom-churn-prediction
```

---

### Step 5 - Push the Versioned Image to GHCR
Upload the `v1` tagged image to GitHub Container Registry:
```powershell
docker push ghcr.io/<github-username>/telecom-churn-prediction:v1
```
> **Expected Output**: Layer progress indicators, followed by `v1: digest: sha256:... size: ...`

---

### Step 6 - Push the Latest Tag to GHCR
```powershell
docker push ghcr.io/<github-username>/telecom-churn-prediction:latest
```
> **Expected Output**: Existing layers show `Layer already exists`, followed by `latest: digest: sha256:...`

---

### Step 7 - Verify the Package on GitHub
1. Open your GitHub Profile: `https://github.com/<github-username>`
2. Click the **Packages** tab.
3. Locate **`telecom-churn-prediction`**.
4. Confirm both `v1` and `latest` tags are visible.
5. *(Optional)*: In Package Settings, you can switch visibility from **Private** to **Public** if desired.

---

### Step 8 - Validate by Pulling from GHCR
To prove the image is accessible from the remote registry, pull it down:
```powershell
docker pull ghcr.io/<github-username>/telecom-churn-prediction:v1
```
> **Expected Output**: `Status: Image is up to date for ghcr.io/<github-username>/telecom-churn-prediction:v1`

---

### Step 9 - Run the Image Pulled from GHCR
Start a new container named `telecom-churn-from-ghcr` using the registry image reference:
```powershell
docker run -d --name telecom-churn-from-ghcr -p 5000:5000 ghcr.io/<github-username>/telecom-churn-prediction:v1
```

Verify the container is active:
```powershell
docker ps
```

---

### Step 10 - Re-test the Running API

#### Test Health Endpoint:
```powershell
Invoke-RestMethod -Uri http://localhost:5000/health -Method Get
```
**Expected Response**:
```json
{
    "service": "telecom-churn-prediction",
    "status": "ok"
}
```

#### Test High-Risk Customer Prediction (`CHURN`):
```powershell
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -Body '{"age": 70, "num_dependents": 0, "estimated_salary": 30000, "calls_made": 5, "sms_sent": 2, "data_used": 100}'
```
**Expected Response**:
```text
prediction prediction_code
---------- ---------------
CHURN                    1
```

---

### Step 11 - Clean Up Container and Log Out

```powershell
# Stop and remove verification container
docker stop telecom-churn-from-ghcr
docker rm telecom-churn-from-ghcr

# Log out from GitHub Container Registry
docker logout ghcr.io
```
> **Expected Output**: `Removing login credentials for ghcr.io`

---

## 4. Observation Table

| Checkpoint | Expected Observation | Verification Result |
|:---|:---|:---:|
| **Local image available** | `telecom-churn-ml:1.0` present in `docker images` | PASS |
| **GHCR login** | `Login Succeeded` | PASS |
| **Version tag** | `ghcr.io/<username>/telecom-churn-prediction:v1` tagged | PASS |
| **Push status** | Layers uploaded and image digest reported | PASS |
| **GitHub package** | `telecom-churn-prediction` visible under GitHub Packages | PASS |
| **Pull status** | Image pulled successfully from `ghcr.io` | PASS |
| **Container status** | Container running from GHCR image reference | PASS |
| **Health / API test** | `/health` returns 200 OK; `/predict` returns CHURN (1) | PASS |

---

## 5. Practical Deliverables & Screenshots to Preserve

- [ ] 1. `docker images` showing `telecom-churn-ml:1.0` and the GHCR tags.
- [ ] 2. `docker login ghcr.io` showing `Login Succeeded` (token value kept secret).
- [ ] 3. `docker push` output showing layers pushed and digest.
- [ ] 4. GitHub Packages page showing the published `v1` and `latest` tags.
- [ ] 5. `docker pull` output showing the image pulled from `ghcr.io`.
- [ ] 6. `docker ps` showing the running container from the GHCR image reference.
- [ ] 7. Health endpoint output (`status: ok`).
- [ ] 8. Prediction request output (`prediction: CHURN`).
- [ ] 9. Cleanup and `docker logout ghcr.io` output.

---

## 6. Viva / Discussion Questions & Answers

1. **What is a container registry?**  
   A centralized remote repository for storing, versioning, securing, and distributing container images across machines and deployment clusters.
2. **What is GitHub Container Registry (GHCR)?**  
   GitHub's OCI-compliant container registry (`ghcr.io`) tightly integrated with GitHub repositories, permissions, and GitHub Actions.
3. **What is the difference between `v1` and `latest`?**  
   `v1` is an immutable version identifier for reproducibility, while `latest` is a convenient rolling pointer pointing to the most recent release.
4. **Why is model retraining unnecessary in this practical?**  
   Because Practical 8 focuses exclusively on artifact distribution. The verified model artifact from Practical 7 is already packaged inside the Docker image.
