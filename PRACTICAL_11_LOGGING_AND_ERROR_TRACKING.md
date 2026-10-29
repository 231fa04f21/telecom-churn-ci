# PRACTICAL - 11: Implement Logging and Error Tracking for Deployed Telecom Churn API

**Course**: MLOps Practical Series | Telecom Churn Prediction  
**Continuation from**: Practical-10: Deploy the Tested Docker Image from GHCR to Render  
**Running Project**: Telecom Churn Prediction  
**Platform**: Render Cloud (`https://telecom-churn-prediction-h5fs.onrender.com`)  
**Registry Host**: `ghcr.io`  
**Logger Name**: `telecom-churn-api`  

---

## 1. Aim & Practical Focus

- **Aim**: To implement application-level structured logging and error tracking in the Telecom Churn Prediction API service (`app.py`), verify that startup/model-loading events, HTTP requests, response latencies, request IDs, input validation errors, and runtime failures are captured to standard output, publish the updated container image through GitHub Actions to GHCR, redeploy on Render, and diagnose production traffic behavior via cloud runtime logs.
- **MLOps Core Concept**: After deploying an ML model into production, observability is essential. Static code cannot report real-world client interaction issues, inference latency bottlenecks, or input distribution failures. Writing structured, log-level-aware events to `stdout` enables cloud platforms (Render, Kubernetes, Datadog) to aggregate, index, and monitor API performance in real time without accessing container internals interactively.

```
Client / Caller (PowerShell, Browser, External Apps)
                       │
                       ▼
Render Public HTTPS Endpoint (https://telecom-churn-prediction-h5fs.onrender.com)
                       │
                       ▼
Flask Prediction API
  ├── [Step 4] Global Logger (StreamHandler to sys.stdout)
  ├── [Step 5] Model Loading: event=model_loaded / event=model_load_failed
  ├── [Step 6] Request Middleware: generates X-Request-ID, measures duration_ms, logs status
  ├── [Step 7] Validation Error Handler: logs field_locations and error_count with HTTP 422
  ├── [Step 8] Safe Prediction Handler: logs feature_names and prediction class (CHURN/RETAIN)
  └── [Step 9] 404 Not Found Handler: logs invalid routes with HTTP 404
                       │
                       ▼
Standard Output Stream (sys.stdout)
                       │
                       ▼
Render Runtime Logs Dashboard (Centralized Cloud Log Stream)
```

---

## 2. Log Levels & Best Practices

| Log Level | Purpose in this Practical | Concrete Example |
|:---|:---|:---|
| **INFO** | Normal operations, milestones, and successful requests | Model loaded successfully, `GET /health` (200), `POST /predict` (200) |
| **WARNING** | Unexpected client behavior or non-crashing validation failures | Missing required feature payload (422), route not found (404) |
| **ERROR** | Unhandled exceptions or server-side runtime failures | Missing model `.pkl` file, scikit-learn inference failure (500) |

### Privacy & Security Rules (What Should & Should NOT Be Logged)
- **Safe to Log**: HTTP Method, path, status code, latency (`duration_ms`), generated `request_id`, feature names (`feature_names=['age', 'calls_made', ...]`), and model output (`prediction=CHURN`).
- **NEVER Log**: Customer personal identifiers (names, emails, phone numbers), authorization headers, GitHub PATs, passwords, or raw unsanitized request payloads.

---

## 3. Implementation in `app.py`

### Step 4 & 5: Logger Configuration and Model Loading
```python
import logging
import sys
import time
import uuid
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("telecom-churn-api")

def load_model():
    if not MODEL_PATH.exists():
        logger.error("event=model_load_failed model_file=%s", MODEL_PATH)
        raise FileNotFoundError(f"{MODEL_PATH} was not found.")
    try:
        loaded_model = joblib.load(MODEL_PATH)
        logger.info("event=model_loaded model_file=%s", MODEL_PATH)
        return loaded_model
    except Exception:
        logger.exception("event=model_load_failed model_file=%s", MODEL_PATH)
        raise
```

### Step 6: Request/Response Middleware
```python
@app.before_request
def before_request_hook():
    g.start_time = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

@app.after_request
def after_request_hook(response):
    start = getattr(g, "start_time", None)
    duration_ms = (time.perf_counter() - start) * 1000 if start else 0.0
    request_id = getattr(g, "request_id", str(uuid.uuid4()))
    response.headers["X-Request-ID"] = request_id

    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(
        level,
        "event=http_request request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.path,
        response.status_code,
        duration_ms,
    )
    return response
```

### Step 7 & 8: Safe Validation and Prediction Logging
```python
@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        logger.warning("event=validation_error path=%s field_locations=['body'] error_count=1", request.path)
        return jsonify({"error": "Validation Error", "detail": "JSON request body required"}), 422

    missing_fields = [f"body.{f}" for f in FEATURES if f not in data or data[f] is None]
    if missing_fields:
        logger.warning("event=validation_error path=%s field_locations=%s error_count=%s", request.path, missing_fields, len(missing_fields))
        return jsonify({"error": "Validation Error", "missing_fields": missing_fields}), 422

    try:
        logger.info("event=prediction_request feature_names=%s safe_input=%s", sorted(data.keys()), {})
        sample = pd.DataFrame([{f: data[f] for f in FEATURES}])
        code = int(model.predict(sample)[0])
        pred = "CHURN" if code == 1 else "RETAIN"
        logger.info("event=prediction_success prediction=%s", pred)
        return jsonify({"prediction": pred, "prediction_code": code}), 200
    except Exception:
        logger.exception("event=prediction_failed")
        return jsonify({"error": "Prediction Error"}), 500
```

---

## 4. Local Test Results

Running `python -m unittest test_app.py -v`:

```text
2026-10-29 12:19:34,794 | INFO | telecom-churn-api | event=model_loaded model_file=telecom_churn_model.pkl
test_health_endpoint (test_app.TestPredictionApplication.test_health_endpoint) ... 2026-10-29 12:19:34,851 | INFO | telecom-churn-api | event=http_request request_id=110f4dbb-60cb-4048-a053-5bc48e5f80d3 method=GET path=/health status=200 duration_ms=0.14
ok
test_high_risk_churn_prediction (test_app.TestPredictionApplication.test_high_risk_churn_prediction) ... 2026-10-29 12:19:34,852 | INFO | telecom-churn-api | event=prediction_request feature_names=['age', 'calls_made', 'data_used', 'estimated_salary', 'num_dependents', 'sms_sent'] safe_input={}
2026-10-29 12:19:34,858 | INFO | telecom-churn-api | event=prediction_success prediction=CHURN
2026-10-29 12:19:34,858 | INFO | telecom-churn-api | event=http_request request_id=5660e534-96f5-49a9-9cd3-6a6718f9ed6d method=POST path=/predict status=200 duration_ms=6.13
ok
test_low_risk_retained_prediction (test_app.TestPredictionApplication.test_low_risk_retained_prediction) ... 2026-10-29 12:19:34,859 | INFO | telecom-churn-api | event=prediction_request feature_names=['age', 'calls_made', 'data_used', 'estimated_salary', 'num_dependents', 'sms_sent'] safe_input={}
2026-10-29 12:19:34,860 | INFO | telecom-churn-api | event=prediction_success prediction=RETAIN
2026-10-29 12:19:34,860 | INFO | telecom-churn-api | event=http_request request_id=11bedf8c-54b8-403f-9d75-30463b143c81 method=POST path=/predict status=200 duration_ms=1.56
ok
test_missing_field_validation (test_app.TestPredictionApplication.test_missing_field_validation) ... 2026-10-29 12:19:34,861 | WARNING | telecom-churn-api | event=validation_error path=/predict field_locations=['body.num_dependents', 'body.estimated_salary', 'body.sms_sent', 'body.data_used'] error_count=4
2026-10-29 12:19:34,861 | WARNING | telecom-churn-api | event=http_request request_id=243e48ce-2e4c-4aea-9e4c-7b04ee50a099 method=POST path=/predict status=422 duration_ms=0.24
ok
test_root_endpoint (test_app.TestPredictionApplication.test_root_endpoint) ... 2026-10-29 12:19:34,862 | INFO | telecom-churn-api | event=http_request request_id=f4cdee14-a16d-42a6-b2fd-777e9d828a7e method=GET path=/ status=200 duration_ms=0.06
ok
test_unknown_route (test_app.TestPredictionApplication.test_unknown_route) ... 2026-10-29 12:19:34,862 | WARNING | telecom-churn-api | event=http_request request_id=d3575a33-2cdd-4609-af50-4028a8b07454 method=GET path=/not-a-real-route status=404 duration_ms=0.07
ok

----------------------------------------------------------------------
Ran 6 tests in 0.066s

OK
```

---

## 5. Production Traffic Testing on Render

Once the image is built by GitHub Actions and redeployed on Render (`Manual Deploy` $\rightarrow$ `Deploy latest reference`), test all traffic types using PowerShell:

### Test 1: Successful Health Check (HTTP 200)
```powershell
Invoke-RestMethod -Uri "https://telecom-churn-prediction-h5fs.onrender.com/health" -Method Get
```
**Render Log Output:**
```text
INFO | telecom-churn-api | event=http_request request_id=... method=GET path=/health status=200 duration_ms=0.74
```

---

### Test 2: Successful Prediction (HTTP 200)
```powershell
Invoke-RestMethod -Uri "https://telecom-churn-prediction-h5fs.onrender.com/predict" -Method Post -ContentType "application/json" -Body '{"age": 70, "num_dependents": 0, "estimated_salary": 30000, "calls_made": 5, "sms_sent": 2, "data_used": 100}'
```
**Render Log Output:**
```text
INFO | telecom-churn-api | event=prediction_request feature_names=['age', 'calls_made', 'data_used', 'estimated_salary', 'num_dependents', 'sms_sent'] safe_input={}
INFO | telecom-churn-api | event=prediction_success prediction=CHURN
INFO | telecom-churn-api | event=http_request request_id=... method=POST path=/predict status=200 duration_ms=3.12
```

---

### Test 3: Client Validation Error (HTTP 422)
Send an incomplete payload missing required fields:
```powershell
Invoke-RestMethod -Uri "https://telecom-churn-prediction-h5fs.onrender.com/predict" -Method Post -ContentType "application/json" -Body '{"age": 70, "calls_made": 5}'
```
**Render Log Output:**
```text
WARNING | telecom-churn-api | event=validation_error path=/predict field_locations=['body.num_dependents', 'body.estimated_salary', 'body.sms_sent', 'body.data_used'] error_count=4
WARNING | telecom-churn-api | event=http_request request_id=... method=POST path=/predict status=422 duration_ms=0.45
```

---

### Test 4: Route Not Found (HTTP 404)
```powershell
Invoke-RestMethod -Uri "https://telecom-churn-prediction-h5fs.onrender.com/not-a-real-route" -Method Get
```
**Render Log Output:**
```text
WARNING | telecom-churn-api | event=http_request request_id=... method=GET path=/not-a-real-route status=404 duration_ms=0.31
```

---

## 6. Observation Table

| Test | Expected HTTP/Result | Expected Log Evidence | Result |
|:---|:---|:---|:---:|
| **Application startup / model load** | Service starts | `event=model_loaded` | PASS |
| **Health endpoint** | 200 OK | `INFO http_request path=/health status=200` | PASS |
| **Valid `/predict`** | 200 + prediction | `prediction_request`, `prediction_success`, `http_request status=200` | PASS |
| **Invalid `/predict`** | 422 Unprocessable | `validation_error + http_request status=422` | PASS |
| **Unknown route** | 404 Not Found | `WARNING http_request status=404` | PASS |
| **Docker container test** | Container remains healthy | Same structured events visible in `docker logs` | PASS |
| **GitHub Actions** | Successful workflow | CI build, test, and publish to GHCR succeed | PASS |
| **Render redeployment** | Live service | Startup and request events visible in Render logs | PASS |

---

## 7. Deliverables & Screenshots Checklist

- [ ] 1. Local terminal output running `python -m unittest test_app.py -v` showing all 6 tests passing and structured logs.
- [ ] 2. GitHub Actions workflow run showing updated image built and pushed to GHCR.
- [ ] 3. GHCR package showing updated `latest` and `sha-<commit>` tags.
- [ ] 4. Render deployment screen showing **Manual Deploy $\rightarrow$ Deploy latest reference** successful.
- [ ] 5. PowerShell terminal showing HTTP 200, HTTP 422, and HTTP 404 responses.
- [ ] 6. Render **Logs** tab showing:
  - Startup `event=model_loaded`
  - Successful `event=http_request status=200`
  - Warning `event=validation_error` and `status=422`
  - Warning `status=404` for missing route
- [ ] 7. Completed observation table.

---

## 8. Viva / Discussion Questions & Answers

1. **What is application logging?**  
   The practice of recording timestamped, contextual runtime events generated by software as it executes, providing visibility into internal execution, state changes, and user requests.

2. **Why are logs important after an ML API is deployed?**  
   Once an ML model is live, operators cannot inspect memory directly. Logs provide the sole source of truth for diagnosing failed inferences, tracking API latency, detecting invalid client schemas, and monitoring server health.

3. **What is the difference between `INFO`, `WARNING`, and `ERROR`?**  
   - `INFO`: Normal operational progress and milestones (e.g. model loaded, HTTP 200).
   - `WARNING`: Recoverable anomalies or client errors that do not crash the service (e.g. HTTP 404, HTTP 422).
   - `ERROR`: Server-side faults, unhandled exceptions, or hardware/dependency failures that prevent request fulfillment (e.g. HTTP 500, missing model file).

4. **Why should container logs be written to `stdout`/`stderr`?**  
   According to 12-Factor App principles, containerized applications should not manage log files on disk. Writing to standard output allows the container runtime (Docker, Kubernetes) and cloud platform (Render) to capture, multiplex, and stream logs without disk consumption or volume mounts.

5. **What information is recorded by the request middleware in this practical?**  
   Incoming HTTP method, endpoint path, assigned `request_id`, response HTTP status code, and total request processing duration (`duration_ms`).

6. **Why is a request ID useful?**  
   A unique request identifier (`X-Request-ID` UUID) links all disparate log lines generated during the lifecycle of a single HTTP call, enabling end-to-end distributed tracing across microservices.

7. **Why is response duration useful?**  
   Measuring `duration_ms` reveals latency trends, identifies slow inference operations, detects cold starts, and helps enforce Service Level Objectives (SLOs).

8. **Why can an invalid request fail before the model runs?**  
   Input validation intercepts malformed payloads before inference occurs, preventing invalid types or missing features from causing unexpected crashes inside NumPy or Scikit-learn.

9. **What HTTP status is commonly returned for request validation errors?**  
   HTTP 422 (Unprocessable Entity), signaling that while the server understands the content-type, the payload fails semantic validation.

10. **Why should the full input payload not automatically be logged?**  
    Logging entire request bodies can inadvertently leak Personally Identifiable Information (PII), customer credentials, or sensitive business data into log storage systems, violating privacy regulations like GDPR and HIPAA.

11. **What is the purpose of `SAFE_INPUT_FIELDS`?**  
    An explicit allow-list defining which non-sensitive feature values may be safely printed to logs for debugging, adhering to the principle of privacy by default.

12. **What is the difference between a 404, 422, and 500 response?**  
    - `404 Not Found`: Client requested a non-existent URL route.
    - `422 Unprocessable Entity`: Client reached a valid route but submitted invalid data.
    - `500 Internal Server Error`: Server encountered an unhandled exception or crash during processing.

13. **How does `logger.exception` help during runtime failures?**  
    It automatically records the error message alongside the complete Python traceback, pinpointing the exact file and line number of the failure without crashing the process.

14. **Why must the original preprocessing logic be preserved when logging is added?**  
    Logging is an observational enhancement. Modifying feature ordering, types, or pipeline steps would alter the mathematical behavior of the ML model, invalidating prior test and validation results.

15. **How do GitHub Actions, GHCR, and Render participate in the Practical-11 update?**  
    - Developers commit updated logging code to GitHub.
    - GitHub Actions automatically runs tests, builds the updated image, and pushes it to GHCR.
    - Render pulls the updated GHCR image via manual redeploy and streams live logs from the updated service.

16. **Why does an image-backed Render service require explicit redeployment?**  
    Render pulls images on deployment and does not poll the registry for tag updates. When the `latest` tag in GHCR points to a new digest, an explicit deploy command must be triggered in Render.

17. **How can logs help identify repeated client errors?**  
    A sudden spike in HTTP 422 warnings with missing feature locations indicates that client developers or frontend apps are using outdated API schemas or corrupt request payloads.

18. **What should never be written into logs?**  
    Passwords, authentication tokens, API keys, private encryption keys, credit card numbers, and identifying personal data.

19. **How is logging different from monitoring?**  
    - **Logging**: Detailed, discrete event-by-event diagnostic records of individual occurrences.
    - **Monitoring**: Aggregated real-time metrics and quantitative time-series data (CPU %, request rate, p99 latency) used to visualize system health and trigger automated alerts.

20. **What production signals should be monitored in the next practical?**  
    Request throughput (requests/sec), error rate (% 5xx/4xx), p50/p95/p99 response latency, CPU and memory utilization, and model availability.

---

## 9. Result

Application logging and error tracking were implemented in the Telecom Churn Prediction API service (`app.py`). Startup events, HTTP access logs with request IDs and latencies, input validation failures (422), route not found warnings (404), and safe prediction metrics were verified locally via unit tests and in the cloud on Render via centralized runtime logs.

