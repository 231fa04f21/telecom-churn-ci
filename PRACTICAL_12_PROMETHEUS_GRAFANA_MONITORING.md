# PRACTICAL - 12: Monitor the Deployed Telecom Churn Prediction API Using Prometheus and Grafana

**Course**: MLOps Practical Series | Telecom Churn Prediction  
**Continuation from**: Practical-11: Implement Logging and Error Tracking  
**Running Project**: Telecom Churn Prediction  
**Render Endpoint**: `https://telecom-churn-prediction-h5fs.onrender.com`  
**Metrics URL**: `https://telecom-churn-prediction-h5fs.onrender.com/metrics`  
**Monitoring Stack**: Prometheus (port 9090) + Grafana (port 3000)  

---

## 1. Aim & Practical Focus

- **Aim**: To instrument the deployed Telecom Churn Prediction API with Prometheus metrics, collect and store those metrics over time using Prometheus, visualize operational performance via Grafana dashboards, and configure alert rules to detect client error spikes (HTTP 4xx) and service unavailability.
- **MLOps Core Concept**: Logging (Practical 11) provides granular event-level traces, whereas **monitoring** provides time-series quantitative aggregates (rates, percentiles, error ratios). Combining Prometheus (metrics scraping & time-series storage) and Grafana (multi-panel visualization) allows engineering teams to detect performance degradations, traffic surges, and model availability issues before users report outages.

```
Client / Swagger (/docs) / Automation
                  │
                  ▼
Render Cloud Service (https://telecom-churn-prediction-h5fs.onrender.com)
  ├── /health (200 OK)
  ├── /predict (ML Inference)
  └── /metrics (Prometheus Text Format)
                  ▲
                  │  (Scrapes every 15s over HTTPS)
                  │
Prometheus Container (port 9090, network: mlops-monitoring)
  ├── Targets Page: http://localhost:9090/targets (Target = UP)
  ├── PromQL Engine: rate(), histogram_quantile(), sum()
  └── Alerting Rules: StudentAPIClientErrors, StudentAPIDown
                  │
                  ▼
Grafana Container (port 3000, network: mlops-monitoring)
  ├── Data Source: http://prometheus:9090
  └── Operational Dashboard (Stat & Time-Series Panels)
```

---

## 2. Metrics Exposed by the API

| Metric Name | Type | Purpose |
|:---|:---|:---|
| **`student_api_http_requests_total`** | Counter | Total HTTP requests categorized by `method`, `path`, and `status` |
| **`student_api_http_request_duration_seconds`** | Histogram | Response duration in seconds for latency percentile calculation (P95/P99) |
| **`student_api_predictions_total`** | Counter | Total prediction attempts labeled by outcome (`result="success"` or `result="error"`) |
| **`student_api_model_loaded`** | Gauge | Binary indicator of model readiness in memory (1 = loaded, 0 = failed) |
| **`up`** | Built-in | Prometheus health indicator for scrape target reachability (1 = UP, 0 = DOWN) |

---

## 3. PromQL Queries Cheat Sheet

| Question | PromQL Query | Recommended Panel View |
|:---|:---|:---|
| **Is the model loaded?** | `student_api_model_loaded` | Stat |
| **Total API Requests?** | `sum(student_api_http_requests_total)` | Stat |
| **Current Request Rate?** | `sum(rate(student_api_http_requests_total[1m]))` | Time series |
| **Successful Predictions?** | `sum(student_api_predictions_total{result="success"})` | Stat |
| **Client/Server Error Rate?**| `sum(rate(student_api_http_requests_total{status=~"4..\|5.."}[5m]))` | Time series |
| **P95 Request Latency?** | `histogram_quantile(0.95, sum by (le) (rate(student_api_http_request_duration_seconds_bucket[5m])))` | Time series |
| **Is target reachable?** | `up{job="student-result-api"}` | Stat |

---

## 4. Step-by-Step Execution Guide

### Step 1 - Instrument `app.py` & Verify Locally
Add `prometheus-client` to `requirements.txt` and instrument middleware and endpoints in `app.py`.  
Verify locally:
```powershell
python -m unittest test_app.py -v
```
*(All 9 tests pass including `/metrics` validation)*

---

### Step 2 - Commit & Push to GitHub Actions
```powershell
git add .
git commit -m "Add Prometheus metrics and monitoring stack (Practical 12)"
git push origin main
```
GitHub Actions automatically builds the Docker image and pushes it to GHCR.

---

### Step 3 - Redeploy on Render
1. Open Render Dashboard $\rightarrow$ **`telecom-churn-prediction`**.
2. Click **Manual Deploy** $\rightarrow$ **Deploy latest reference**.
3. Once live, open in browser:
   `https://telecom-churn-prediction-h5fs.onrender.com/metrics`
4. Confirm metric names `student_api_model_loaded 1.0` and `student_api_http_requests_total` appear.

---

### Step 4 - Launch Prometheus & Grafana Locally

From the project root:
```powershell
# Create network (if not existing)
docker network create mlops-monitoring

# Start Prometheus
docker run -d --name prometheus --network mlops-monitoring -p 9090:9090 -v "${PWD}/Practical_12_Monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" -v "${PWD}/Practical_12_Monitoring/student_api_alerts.yml:/etc/prometheus/student_api_alerts.yml:ro" prom/prometheus

# Start Grafana
docker run -d --name grafana --network mlops-monitoring -p 3000:3000 grafana/grafana
```

---

### Step 5 - Verify Prometheus Target
1. Open **[http://localhost:9090/targets](http://localhost:9090/targets)** in your browser.
2. Confirm that the endpoint `student-result-api` displays **State: UP (1/1 up)** with green indicator.

---

### Step 6 - Connect Grafana to Prometheus
1. Open **[http://localhost:3000](http://localhost:3000)** (Default login: `admin` / `admin`).
2. Navigate to **Connections** $\rightarrow$ **Data sources** $\rightarrow$ **Add data source** $\rightarrow$ **Prometheus**.
3. Set **Prometheus server URL**:
   ```text
   http://prometheus:9090
   ```
4. Click **Save & test**. A green notification *"Successfully queried the Prometheus API"* confirms connection.

---

### Step 7 - Build the Monitoring Dashboard in Grafana
Click **Dashboards** $\rightarrow$ **New Dashboard** $\rightarrow$ **Add visualization** and add the 6 panels:
1. **Model Loaded**: PromQL: `student_api_model_loaded`, View: **Stat**.
2. **Total API Requests**: PromQL: `sum(student_api_http_requests_total)`, View: **Stat**.
3. **Requests per Second**: PromQL: `sum(rate(student_api_http_requests_total[1m]))`, View: **Time series**.
4. **Successful Predictions**: PromQL: `sum(student_api_predictions_total{result="success"})`, View: **Stat**.
5. **Client Error Rate (4xx)**: PromQL: `sum(rate(student_api_http_requests_total{status=~"4.."}[2m]))`, View: **Time series**.
6. **P95 Latency**: PromQL: `histogram_quantile(0.95, sum by (le) (rate(student_api_http_request_duration_seconds_bucket[5m])))`, View: **Time series**.

Save the dashboard as: **`Telecom Churn - API Monitoring`**.

---

### Step 8 - Trigger the Classroom Alert Demonstration
To safely observe an alert rule transition from **Inactive $\rightarrow$ Pending $\rightarrow$ Firing**:
1. Run repeated invalid requests in PowerShell:
   ```powershell
   1..15 | ForEach-Object {
       try { Invoke-RestMethod -Uri "https://telecom-churn-prediction-h5fs.onrender.com/predict" -Method Post -ContentType "application/json" -Body '{"age": 70}' } catch {}
       Start-Sleep -Milliseconds 500
   }
   ```
2. Open **[http://localhost:9090/alerts](http://localhost:9090/alerts)**.
3. Observe **`StudentAPIClientErrors`** turn yellow (**Pending**) and then red (**Firing**).

---

## 5. Observation Table

| Test / Observation | Expected Evidence | Result |
|:---|:---|:---:|
| **Local `/metrics`** | `student_api_*` metrics visible in text format | PASS |
| **Model readiness** | `student_api_model_loaded = 1` | PASS |
| **Valid prediction** | Prediction counter increments upon valid inference | PASS |
| **Invalid request** | 4xx HTTP metric increases and log warning is emitted | PASS |
| **Docker container test** | `/health`, `/predict`, and `/metrics` work inside container | PASS |
| **GitHub Actions** | Build/test/publish workflow passes on push | PASS |
| **GHCR** | Updated image tagged and pushed to registry | PASS |
| **Render** | Updated service is live and responding | PASS |
| **Prometheus target** | `student-result-api = UP` on `http://localhost:9090/targets` | PASS |
| **Grafana** | Dashboard panels display live metric data | PASS |
| **Alert demonstration** | `StudentAPIClientErrors` reaches expected Pending/Firing state | PASS |
| **Logs + metrics correlation**| Same HTTP request verified in logs and Prometheus counter | PASS |

---

## 6. Practical Deliverables & Screenshots Checklist

- [ ] 1. Terminal screenshot running `python -m unittest test_app.py -v` (9 passing tests).
- [ ] 2. Browser screenshot of `https://telecom-churn-prediction-h5fs.onrender.com/metrics`.
- [ ] 3. Prometheus Targets page (**http://localhost:9090/targets**) showing target **UP**.
- [ ] 4. Prometheus Graph query page showing PromQL query execution (e.g. `sum(student_api_http_requests_total)`).
- [ ] 5. Grafana Data Source configuration page showing successful test connection.
- [ ] 6. Grafana Dashboard showing live operational panels (Model Loaded, Requests, Latency, Errors).
- [ ] 7. Prometheus Alerts page (**http://localhost:9090/alerts**) showing `StudentAPIClientErrors` in **Pending** or **Firing** state.
- [ ] 8. Completed observation table.

---

## 7. Viva / Discussion Questions & Answers

1. **What is monitoring in MLOps?**  
   The ongoing collection, aggregation, and analysis of quantitative metrics from running ML services to track availability, traffic volume, latency, error rates, and model quality over time.

2. **How are logs different from metrics?**  
   Logs are discrete, qualitative event records with rich text context (e.g. stack traces, request IDs). Metrics are numeric, aggregated time-series values optimized for mathematical evaluation, real-time dashboards, and alerting.

3. **What is Prometheus?**  
   An open-source systems monitoring and alerting toolkit that collects metrics by pulling (scraping) HTTP endpoints at configured intervals and stores them in a time-series database.

4. **What is Grafana?**  
   An open-source visualization and analytics platform that connects to time-series databases like Prometheus to render interactive, customizable operational dashboards.

5. **What is the purpose of a `/metrics` endpoint?**  
   It exposes current internal application counters, gauges, and histograms formatted in Prometheus standard exposition text format for scrapers to retrieve.

6. **What is a Prometheus scrape?**  
   A scheduled HTTP GET request initiated by Prometheus to a target's `/metrics` endpoint to sample and record current metric values.

7. **What does the Prometheus `up` metric represent?**  
   A binary metric automatically generated for every target. A value of `1` indicates the target was successfully scraped; `0` indicates connection or parsing failure.

8. **What is the difference between Counter, Gauge, and Histogram?**  
   - **Counter**: Cumulative metric that can only increase or reset to zero on restart (e.g. total requests).
   - **Gauge**: Instantaneous numerical value that can arbitrary go up or down (e.g. CPU %, model loaded).
   - **Histogram**: Samples observations (usually durations or payload sizes) and counts them in configurable buckets.

9. **Why is request latency measured with a Histogram?**  
   Histograms allow calculating arbitrary statistical percentiles (such as P50, P90, P95, P99) across distributed time windows without storing individual raw observations.

10. **What is PromQL?**  
    Prometheus Query Language—a domain-specific functional expression language used to filter, aggregate, rate, and analyze time-series data.

11. **Why are `rate()` and `increase()` useful for counters?**  
    Because counters increase monotonically since server start, raw counter values do not show current activity. `rate()` computes the per-second rate of change over a time window, revealing real-time spikes and trends.

12. **What does P95 latency mean?**  
    95% of all requests were served faster than this duration, while only the slowest 5% experienced higher latency.

13. **Why is `/metrics` excluded from user-traffic counting?**  
    Prometheus scrapes `/metrics` continuously at fixed intervals. Including scrape calls would artificially inflate API request counts and skew latency percentiles.

14. **Why should metric labels not contain customer names or phone numbers?**  
    High cardinality. Creating a unique metric label for every user causes unbounded memory growth in the time-series database, degrading database performance and crashing monitoring nodes.

15. **How does Prometheus obtain metrics from the Render deployment?**  
    Prometheus executes an outbound HTTPS request (`https://telecom-churn-prediction-h5fs.onrender.com/metrics`) over the public internet, parses the exposition text, and timestamps the samples.

16. **Why does Grafana use Prometheus instead of querying the API directly?**  
    The API only knows instantaneous in-memory values. Prometheus stores historical time-series data, computes moving averages and percentiles via PromQL, and relieves the serving API from computing analytics.

17. **What is an alert rule?**  
    A boolean or relational PromQL condition (e.g. `error_rate > 0.05 for 2m`) evaluated periodically by Prometheus that shifts an alert state from Inactive to Pending and Firing.

18. **What is the difference between a pending and a firing alert?**  
    - **Pending**: The alert condition has been met, but the specified duration (`for: 30s`) has not yet elapsed (guards against transient blips).
    - **Firing**: The condition has persisted continuously for the full required duration, confirming an active incident.

19. **Why is a client-error alert used for classroom demonstration?**  
    It allows students to safely trigger an alert state by intentionally sending malformed payloads (HTTP 422) without crashing the production container or inducing service downtime.

20. **What would be monitored additionally in a larger production ML system?**  
    Feature drift, prediction distribution drift, concept drift, ground-truth label delays, memory leaks, GPU utilization, cache hit rates, and downstream database latency.

---

## 8. Result

The deployed Telecom Churn Prediction API was instrumented with Prometheus metrics (`/metrics`). A monitoring stack comprising Prometheus and Grafana was configured locally in Docker. Prometheus successfully scrapes the live Render service over HTTPS (target UP). A Grafana operational dashboard was constructed with six panels, and an alert rule for client error spikes was demonstrated.

