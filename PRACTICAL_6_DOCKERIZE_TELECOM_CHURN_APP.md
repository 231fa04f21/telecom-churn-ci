# PRACTICAL - 6: Dockerize the ML Prediction Application (Telecom Churn Model)

**Course**: MLOps Practical Series | CI/CD, Delivery and Docker  
**Continuation of**: Practical-5: Continuous Delivery of an ML Prediction Application  
**Dataset**: `telecom_churn.csv`  
**Docker Image**: `telecom-churn-ml:1.0`  
**Docker Container**: `telecom-churn-ml-container` (Port mapping `5000:5000`)  

---

## 1. Practical Objective & Workflow Architecture

The objective of Practical 6 is to package the validated **Telecom Customer Churn Flask prediction application**, the trained machine learning model (`telecom_churn_model.pkl`), the Python runtime, and all required dependencies into a reproducible **Docker image**, run it as a **Docker container**, and test the REST endpoints from the host operating system.

```
Validated Continuous Delivery Release
                 ↓
Dockerfile + Application (app.py) + Model (.pkl) + .dockerignore
                 ↓
docker build -t telecom-churn-ml:1.0 .
                 ↓
docker run -d --name telecom-churn-ml-container -p 5000:5000 telecom-churn-ml:1.0
                 ↓
Host Request (http://localhost:5000) → Port Mapping (5000:5000) → Flask API inside Container
                 ↓
APPLICATION RUNNING IN AN ISOLATED CONTAINER
```

> **Key Takeaway**: This practical establishes container fundamentals and local container execution. Practical-7 automates the container build and testing inside the GitHub Actions cloud runner.

---

## 2. Docker Terminology in MLOps

| Term | Meaning in this Practical |
|:---|:---|
| **`Dockerfile`** | Text instructions specifying the base OS image, dependencies, model files, and container startup command. |
| **Docker Image (`telecom-churn-ml:1.0`)** | Standalone, read-only executable template packaging Python 3.11-slim, Flask, Scikit-learn, and the trained model. |
| **Docker Container (`telecom-churn-ml-container`)** | An active, isolated running instance of the Docker image. |
| **Port Mapping (`-p 5000:5000`)** | Bridges host port `5000` to container port `5000` so external HTTP clients can reach Flask. |
| **Build Context (`.`)** | The directory whose contents are transmitted to the Docker daemon during `docker build`. |

---

## 3. Docker Configuration Files

### 3.1 `Dockerfile`
Created in the root of the project:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY telecom_churn_model.pkl .
COPY metrics.json .

EXPOSE 5000

CMD ["python", "app.py"]
```

#### Detailed Explanation:
- `FROM python:3.11-slim`: Lightweight, secure Debian-based Python 3.11 base image (~150MB).
- `WORKDIR /app`: Defines `/app` as the root working directory inside the container.
- `COPY requirements.txt .`: Copies the dependency list before copying source code to leverage Docker layer caching.
- `RUN pip install --no-cache-dir -r requirements.txt`: Installs NumPy, Pandas, Scikit-learn, Joblib, and Flask without caching wheel files, reducing image size.
- `COPY app.py .`, `COPY telecom_churn_model.pkl .`, `COPY metrics.json .`: Bundles the Flask API and trained model.
- `EXPOSE 5000`: Documents that Flask listens on port 5000.
- `CMD ["python", "app.py"]`: Entrypoint executed when the container starts.

---

### 3.2 `.dockerignore`
Prevents unnecessary files and heavy datasets from bloating the Docker build context:

```text
__pycache__/
*.pyc
.git/
.github/
test_*.py
telecom_churn.csv
release_candidate/
```
> **Note**: Excluding the 18.8 MB `telecom_churn.csv` keeps the Docker build context lightweight (~4 KB) and ensures only the final serialized model (`.pkl`) is packaged.

---

### 3.3 Updated Continuous Delivery Workflow (`.github/workflows/ml-ci.yml`)

The `Prepare release candidate` step in `.github/workflows/ml-ci.yml` now copies `Dockerfile` and `.dockerignore` into `release_candidate/`:

```yaml
      - name: Prepare release candidate
        run: |
          mkdir -p release_candidate
          cp app.py release_candidate/
          cp telecom_churn_model.pkl release_candidate/
          cp metrics.json release_candidate/
          cp requirements.txt release_candidate/
          cp Dockerfile release_candidate/
          cp .dockerignore release_candidate/
          printf "Telecom Customer Churn Prediction ML Application\nRun: python app.py\nEndpoint: POST /predict\n" > release_candidate/DEPLOYMENT.txt
```

---

## 4. Local Execution & Verification Steps

### Step 10: Build the Docker Image
```powershell
docker build -t telecom-churn-ml:1.0 .
```

### Step 11: Verify Docker Image
```powershell
docker images telecom-churn-ml
```
**Output**:
```text
IMAGE                  ID             DISK USAGE   CONTENT SIZE   EXTRA
telecom-churn-ml:1.0   11ab008f39c6        698MB          159MB
```

---

### Step 12: Run the Docker Container
```powershell
docker run -d --name telecom-churn-ml-container -p 5000:5000 telecom-churn-ml:1.0
```

### Step 13: Verify Container Status
```powershell
docker ps
```
**Output**:
```text
CONTAINER ID   IMAGE                  COMMAND           STATUS          PORTS                                         NAMES
56cad51ceb46   telecom-churn-ml:1.0   "python app.py"   Up 19 seconds   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   telecom-churn-ml-container
```

---

### Step 14: Test the Health Endpoint
In browser or PowerShell:
```powershell
Invoke-RestMethod -Uri http://localhost:5000/ -Method Get
```
**Response**:
```json
{
    "service": "telecom-churn-prediction",
    "status": "ok"
}
```

---

### Step 15: Test Low-Risk / Retained Customer Prediction
In PowerShell:
```powershell
$body = @{
    age = 25
    num_dependents = 4
    estimated_salary = 140000
    calls_made = 90
    sms_sent = 50
    data_used = 9000
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -Body $body
```
**Response**:
```text
prediction prediction_code
---------- ---------------
RETAIN     0
```

---

### Step 16: Test High-Risk / Churned Customer Prediction
In PowerShell:
```powershell
$body = @{
    age = 70
    num_dependents = 0
    estimated_salary = 30000
    calls_made = 5
    sms_sent = 2
    data_used = 100
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/predict -Method Post -ContentType "application/json" -Body $body
```
**Response**:
```text
prediction prediction_code
---------- ---------------
CHURN      1
```

---

### Step 17: Inspect Container Logs
```powershell
docker logs telecom-churn-ml-container
```
**Log Output**:
```text
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
172.17.0.1 - - [29/Oct/2026 04:22:03] "GET / HTTP/1.1" 200 -
172.17.0.1 - - [29/Oct/2026 04:22:24] "POST /predict HTTP/1.1" 200 -
172.17.0.1 - - [29/Oct/2026 04:22:43] "POST /predict HTTP/1.1" 200 -
```

---

### Step 18: Controlled Port-Mapping Demonstration
This experiment proves why `-p 5000:5000` is required:
1. Stop and remove the active container:
   ```powershell
   docker stop telecom-churn-ml-container ; docker rm telecom-churn-ml-container
   ```
2. Run without `-p 5000:5000`:
   ```powershell
   docker run -d --name telecom-churn-no-port telecom-churn-ml:1.0
   ```
3. Attempt to access `http://localhost:5000/`:
   $\rightarrow$ Fails with connection refused because the container's port is not published to the host.
4. Clean up and restore:
   ```powershell
   docker stop telecom-churn-no-port ; docker rm telecom-churn-no-port
   docker run -d --name telecom-churn-ml-container -p 5000:5000 telecom-churn-ml:1.0
   ```

---

## 5. Docker Image vs. Docker Container

| Feature | Docker Image (`telecom-churn-ml:1.0`) | Docker Container (`telecom-churn-ml-container`) |
|:---|:---|:---|
| **Definition** | Built package / blueprint | Running instance of an image |
| **Mutability** | Read-only layer stack | Read-write ephemeral top layer |
| **Creation Command** | `docker build` | `docker run` |
| **State** | Static file on disk | Active process running in RAM/CPU |

---

## 6. MLOps Lifecycle Progression (Practicals 1 to 6)

| Practical | Capability Added | Result |
|:---|:---|:---|
| **Practical-1** | Basic Code CI | Automated unit testing on commit |
| **Practical-2** | Automated ML Training CI | Automated data loading, model fitting, and ML tests |
| **Practical-3** | ML Quality Gate | Enforces minimum accuracy threshold ($\ge 0.50$) |
| **Practical-4** | Artifact Preservation | Uploads validated outputs to GitHub storage |
| **Practical-5** | Continuous Delivery (CD) | Packages model + Flask API into a release candidate |
| **Practical-6** | Containerization | Packages the application into a Docker container for consistent execution |

---

## 7. Evidence / Screenshots Checklist

- [ ] 1. GitHub Actions run showing the release candidate with `Dockerfile` and `.dockerignore`.
- [ ] 2. Downloaded release candidate showing `Dockerfile`, `.dockerignore`, `app.py`, and model.
- [ ] 3. `docker --version` and `docker info` terminal output.
- [ ] 4. Successful `docker build -t telecom-churn-ml:1.0 .` terminal log.
- [ ] 5. `docker images` showing `telecom-churn-ml:1.0`.
- [ ] 6. `docker ps` showing running container with `0.0.0.0:5000->5000/tcp` port mapping.
- [ ] 7. Browser or terminal output from the health endpoint (`{"status":"ok"}`).
- [ ] 8. PowerShell prediction result for low-risk customer (`RETAIN`, code `0`).
- [ ] 9. PowerShell prediction result for high-risk customer (`CHURN`, code `1`).
- [ ] 10. `docker logs` showing incoming HTTP 200 requests.

---

## 8. Next Practical Preview

**Practical-7: Automatically Build and Test the Docker Image using GitHub Actions**:  
Practical 7 will move the `docker build` and container endpoint testing steps from the local machine directly into the **GitHub Actions cloud runner**, completing automated container CI/CD.

