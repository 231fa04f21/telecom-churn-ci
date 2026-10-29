"""
Flask Prediction API with Structured Logging, Error Tracking, Swagger UI & Prometheus Metrics
MLOps Practical 12 - Monitor Deployed API Using Prometheus and Grafana
"""

import logging
import os
from pathlib import Path
import sys
import time
import uuid
import joblib
import pandas as pd
from flask import Flask, jsonify, request, g, Response, render_template_string
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

try:
    from drift.service import (
        detect_drift as run_detect_drift,
        simulate_data as run_simulate_data,
        retrain_candidate as run_retrain_candidate,
        approve_candidate as run_approve_candidate,
        DRIFT_REPORT,
        RETRAINING_METRICS,
    )
except ImportError:
    run_detect_drift = None
    run_simulate_data = None
    run_retrain_candidate = None
    run_approve_candidate = None

# Step 4 - Configure the Application Logger (stdout for Docker/Render capture)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger("telecom-churn-api")

app = Flask(__name__)

MODEL_PATH = Path("telecom_churn_model.pkl")
FEATURES = [
    "age",
    "num_dependents",
    "estimated_salary",
    "calls_made",
    "sms_sent",
    "data_used"
]

# Privacy rule: Add only non-sensitive model features when classroom input-value logging is required
SAFE_INPUT_FIELDS = set()

# Practical 12: Define Prometheus Metrics (both standard curriculum names & domain names)
HTTP_REQUESTS = Counter(
    "student_api_http_requests_total",
    "Total HTTP requests received by the API",
    ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "student_api_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"]
)
PREDICTIONS = Counter(
    "student_api_predictions_total",
    "Total prediction attempts",
    ["result"]
)
MODEL_LOADED = Gauge(
    "student_api_model_loaded",
    "Whether the prediction model is loaded"
)

CHURN_HTTP_REQUESTS = Counter(
    "telecom_churn_http_requests_total",
    "Total HTTP requests received by the Telecom Churn API",
    ["method", "path", "status"]
)
CHURN_HTTP_LATENCY = Histogram(
    "telecom_churn_http_request_duration_seconds",
    "HTTP request duration in seconds for Telecom Churn API",
    ["method", "path"]
)
CHURN_PREDICTIONS = Counter(
    "telecom_churn_predictions_total",
    "Total Telecom Churn prediction attempts",
    ["result"]
)
CHURN_MODEL_LOADED = Gauge(
    "telecom_churn_model_loaded",
    "Whether the Telecom Churn model is loaded"
)


# Step 5 & 6 - Log Model Loading and Connect Model-Loaded Gauge
def load_model():
    if not MODEL_PATH.exists():
        MODEL_LOADED.set(0)
        CHURN_MODEL_LOADED.set(0)
        logger.error("event=model_load_failed model_file=%s", MODEL_PATH)
        raise FileNotFoundError(
            f"{MODEL_PATH} was not found. Run the training pipeline first."
        )
    try:
        loaded_model = joblib.load(MODEL_PATH)
        MODEL_LOADED.set(1)
        CHURN_MODEL_LOADED.set(1)
        logger.info("event=model_loaded model_file=%s", MODEL_PATH)
        return loaded_model
    except Exception:
        MODEL_LOADED.set(0)
        CHURN_MODEL_LOADED.set(0)
        logger.exception("event=model_load_failed model_file=%s", MODEL_PATH)
        raise


# Pre-load model at application startup
model = load_model()


# Step 6 & 7 - Request/Response Logging Middleware & Prometheus Metrics
@app.before_request
def before_request_hook():
    g.start_time = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))


@app.after_request
def after_request_hook(response):
    start = getattr(g, "start_time", None)
    if start is not None:
        duration_sec = time.perf_counter() - start
        duration_ms = duration_sec * 1000
    else:
        duration_sec = 0.0
        duration_ms = 0.0

    request_id = getattr(g, "request_id", str(uuid.uuid4()))
    response.headers["X-Request-ID"] = request_id

    # Exclude /metrics scrape requests from application traffic metrics
    if request.path != "/metrics":
        HTTP_REQUESTS.labels(
            method=request.method,
            path=request.path,
            status=str(response.status_code)
        ).inc()
        HTTP_LATENCY.labels(
            method=request.method,
            path=request.path
        ).observe(duration_sec)

        CHURN_HTTP_REQUESTS.labels(
            method=request.method,
            path=request.path,
            status=str(response.status_code)
        ).inc()
        CHURN_HTTP_LATENCY.labels(
            method=request.method,
            path=request.path
        ).observe(duration_sec)

    # Log WARNING for HTTP error status codes (>= 400), INFO for successful ones
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


# Step 9 - Prometheus /metrics Endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# Root & Health Endpoints
@app.get("/")
@app.get("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "service": "telecom-churn-prediction"
    }), 200


# OpenAPI Specification for Swagger UI
@app.get("/openapi.json")
def openapi_spec():
    return jsonify({
        "openapi": "3.0.2",
        "info": {
            "title": "Telecom Churn Prediction API",
            "version": "1.0.0",
            "description": "Interactive API documentation for Telecom Customer Churn Prediction"
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health Check",
                    "operationId": "health_check_health_get",
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "ok",
                                        "service": "telecom-churn-prediction"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/predict": {
                "post": {
                    "summary": "Predict",
                    "operationId": "predict_predict_post",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/TelecomChurnInput"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "prediction": "CHURN",
                                        "prediction_code": 1
                                    }
                                }
                            }
                        },
                        "422": {
                            "description": "Validation Error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HTTPValidationError"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/metrics": {
                "get": {
                    "summary": "Prometheus Metrics",
                    "operationId": "metrics_metrics_get",
                    "responses": {
                        "200": {
                            "description": "Prometheus formatted metrics"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "TelecomChurnInput": {
                    "title": "TelecomChurnInput",
                    "required": [
                        "age",
                        "num_dependents",
                        "estimated_salary",
                        "calls_made",
                        "sms_sent",
                        "data_used"
                    ],
                    "type": "object",
                    "properties": {
                        "age": {"title": "Age", "type": "integer", "example": 70},
                        "num_dependents": {"title": "Num Dependents", "type": "integer", "example": 0},
                        "estimated_salary": {"title": "Estimated Salary", "type": "number", "example": 30000},
                        "calls_made": {"title": "Calls Made", "type": "integer", "example": 5},
                        "sms_sent": {"title": "Sms Sent", "type": "integer", "example": 2},
                        "data_used": {"title": "Data Used", "type": "number", "example": 100}
                    }
                },
                "HTTPValidationError": {
                    "title": "HTTPValidationError",
                    "type": "object",
                    "properties": {
                        "detail": {
                            "title": "Detail",
                            "type": "string",
                            "example": "Missing required fields"
                        },
                        "missing_fields": {
                            "title": "Missing Fields",
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["body.num_dependents", "body.estimated_salary"]
                        }
                    }
                }
            }
        }
    })


# Swagger UI Interactive Documentation Endpoint
@app.get("/docs")
def swagger_ui():
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Telecom Churn Prediction API - Swagger UI</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    window.onload = function() {
        window.ui = SwaggerUIBundle({
            url: "/openapi.json",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout"
        });
    };
    </script>
</body>
</html>"""
    return html_content, 200, {"Content-Type": "text/html"}


# Step 8 - Prediction Endpoint with Safe Logging, Validation Tracking & Prometheus Counters
@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        logger.warning(
            "event=validation_error path=%s field_locations=['body'] error_count=1",
            request.path,
        )
        return jsonify({
            "error": "Validation Error",
            "detail": "JSON request body is required",
            "missing_fields": FEATURES
        }), 422

    missing_fields = [
        f"body.{feature}" for feature in FEATURES
        if feature not in data or data[feature] is None or data[feature] == ""
    ]

    if missing_fields:
        logger.warning(
            "event=validation_error path=%s field_locations=%s error_count=%s",
            request.path,
            missing_fields,
            len(missing_fields),
        )
        return jsonify({
            "error": "Validation Error",
            "detail": "Missing required fields",
            "missing_fields": [f.replace("body.", "") for f in missing_fields]
        }), 422

    try:
        # Privacy-safe input logging (only approved non-sensitive keys logged)
        safe_input = {
            key: data[key]
            for key in data
            if key in SAFE_INPUT_FIELDS
        }
        logger.info(
            "event=prediction_request feature_names=%s safe_input=%s",
            sorted(data.keys()),
            safe_input,
        )

        sample = pd.DataFrame([{
            feature: data[feature]
            for feature in FEATURES
        }])

        prediction_code = int(model.predict(sample)[0])
        prediction = "CHURN" if prediction_code == 1 else "RETAIN"

        # Record prediction success in Prometheus
        PREDICTIONS.labels(result="success").inc()
        CHURN_PREDICTIONS.labels(result="success").inc()

        logger.info(
            "event=prediction_success prediction=%s",
            prediction,
        )

        return jsonify({
            "prediction": prediction,
            "prediction_code": prediction_code
        }), 200

    except Exception:
        # Record prediction error in Prometheus
        PREDICTIONS.labels(result="error").inc()
        CHURN_PREDICTIONS.labels(result="error").inc()

        logger.exception("event=prediction_failed")
        return jsonify({
            "error": "Prediction Error",
            "detail": "Prediction failed during inference"
        }), 500


# Practical 15: Data Drift & Retraining HTML Dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Telecom Churn MLOps — Data Drift & Retraining Control Center</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-heading: #f0f6fc;
      --primary: #2563eb;
      --success: #22c55e;
      --success-bg: rgba(34, 197, 94, 0.15);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.15);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { color: var(--text-heading); font-size: 22px; font-weight: 600; }
    .subtitle { color: #8b949e; font-size: 13px; margin-top: 4px; }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-success { background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }
    .badge-danger { background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger); }
    .badge-neutral { background: rgba(139, 148, 158, 0.2); color: #8b949e; border: 1px solid #30363d; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }
    .card-title { font-size: 12px; color: #8b949e; text-transform: uppercase; margin-bottom: 8px; }
    .card-value { font-size: 24px; font-weight: 700; color: var(--text-heading); }
    .card-meta { font-size: 13px; color: #8b949e; margin-top: 6px; }

    .toolbar {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }
    .btn {
      padding: 10px 16px;
      border-radius: 6px;
      border: none;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      color: #fff;
      transition: all 0.2s ease;
    }
    .btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn-green { background: #16a34a; }
    .btn-red { background: #dc2626; }
    .btn-blue { background: #2563eb; }
    .btn-purple { background: #7c3aed; }
    .btn-emerald { background: #059669; }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 13px;
    }
    th, td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: rgba(255, 255, 255, 0.02);
      color: #8b949e;
      text-transform: uppercase;
      font-size: 11px;
    }
    tr:hover { background: rgba(255, 255, 255, 0.03); }

    .console {
      background: #090d13;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 12px;
      color: #38bdf8;
      max-height: 200px;
      overflow-y: auto;
      white-space: pre-wrap;
      margin-top: 16px;
    }
    .links a {
      color: #58a6ff;
      text-decoration: none;
      margin-right: 16px;
      font-size: 13px;
    }
    .links a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Telecom Churn MLOps — Data Drift & Retraining Control Center</h1>
        <div class="subtitle">Practical 15 | Two-Sample Kolmogorov-Smirnov (KS) Test & Quality Gate Automation</div>
      </div>
      <div>
        <span id="overall-badge" class="badge badge-neutral">Checking Status...</span>
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <div class="card-title">Production Model</div>
        <div class="card-value" style="font-size: 18px;">telecom_churn_model.pkl</div>
        <div class="card-meta">Baseline Records: <strong style="color: #fff;">243,553</strong></div>
      </div>
      <div class="card">
        <div class="card-title">Recent Input Sample</div>
        <div class="card-value" id="kpi-rows">1,000 rows</div>
        <div class="card-meta">Batch Status: <strong id="kpi-mode" style="color: #fff;">Active</strong></div>
      </div>
      <div class="card">
        <div class="card-title">Drift Status</div>
        <div class="card-value" id="kpi-drifted-count">0 / 6 Features</div>
        <div class="card-meta">KS Significance Threshold: <strong style="color: #fff;">p &lt; 0.05</strong></div>
      </div>
      <div class="card">
        <div class="card-title">Model Quality Gate</div>
        <div class="card-value" style="color: #38bdf8;">Accuracy &ge; 50.0%</div>
        <div class="card-meta" id="kpi-candidate-accuracy">Candidate: <strong>Ready</strong></div>
      </div>
    </div>

    <div class="toolbar">
      <span style="font-size: 12px; font-weight: 600; color: #8b949e;">ONE-CLICK ACTIONS:</span>
      <button class="btn btn-green" onclick="simulateData('stable')">1. Simulate Stable Batch</button>
      <button class="btn btn-red" onclick="simulateData('drift')">2. Simulate Drifted Batch</button>
      <button class="btn btn-blue" onclick="detectDrift()">3. Run KS Drift Test</button>
      <button class="btn btn-purple" onclick="retrainModel()">4. Retrain Candidate</button>
      <button class="btn btn-emerald" onclick="approveCandidate()">5. Approve & Promote</button>
    </div>

    <div class="card" style="margin-bottom: 24px;">
      <h2 style="font-size: 16px; color: var(--text-heading); margin-bottom: 8px;">Feature Distribution Analysis (KS Hypothesis Test)</h2>
      <table>
        <thead>
          <tr>
            <th>Feature Name</th>
            <th>Reference Mean</th>
            <th>Recent Mean</th>
            <th>KS Statistic (D)</th>
            <th>P-Value (p)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="features-table-body">
          <tr><td colspan="6" style="text-align: center; color: #8b949e;">Loading drift report...</td></tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2 style="font-size: 15px; color: var(--text-heading);">MLOps Execution Console</h2>
      <div id="console-output" class="console">Ready. Click any action button above to demonstrate drift detection and conditional retraining to your faculty.</div>
      <div class="links" style="margin-top: 14px;">
        <a href="/docs" target="_blank">&#128214; Swagger API Docs (/docs)</a>
        <a href="/metrics" target="_blank">&#128202; Prometheus Metrics (/metrics)</a>
        <a href="/health" target="_blank">&#9889; Health (/health)</a>
        <a href="/api/drift/report" target="_blank">&#128203; Raw Drift JSON Report</a>
      </div>
    </div>
  </div>

  <script>
    function log(msg) {
      const el = document.getElementById("console-output");
      const time = new Date().toLocaleTimeString();
      el.textContent = `[${time}] ${msg}\\n` + el.textContent;
    }

    async function loadReport() {
      try {
        const res = await fetch('/api/drift/report');
        const data = await res.json();
        renderReport(data);
      } catch (err) {
        log("Error loading drift report: " + err);
      }
    }

    function renderReport(data) {
      const overallBadge = document.getElementById("overall-badge");
      if (data.overall_drift) {
        overallBadge.className = "badge badge-danger";
        overallBadge.textContent = "DRIFT DETECTED";
      } else {
        overallBadge.className = "badge badge-success";
        overallBadge.textContent = "HEALTHY (NO DRIFT)";
      }

      document.getElementById("kpi-drifted-count").textContent = `${data.drifted_feature_count} / 6 Features`;

      const tbody = document.getElementById("features-table-body");
      tbody.innerHTML = "";

      for (const [name, stats] of Object.entries(data.features)) {
        const tr = document.createElement("tr");
        const statusBadge = stats.drift_detected 
          ? `<span class="badge badge-danger">DRIFTED (p < 0.05)</span>`
          : `<span class="badge badge-success">STABLE</span>`;
        
        tr.innerHTML = `
          <td><strong>${name}</strong></td>
          <td>${stats.reference_mean.toLocaleString()}</td>
          <td>${stats.current_mean.toLocaleString()}</td>
          <td>${stats.ks_statistic.toFixed(4)}</td>
          <td>${stats.p_value.toFixed(6)}</td>
          <td>${statusBadge}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    async function simulateData(mode) {
      log(`Simulating ${mode.toUpperCase()} customer batch...`);
      try {
        const res = await fetch(`/api/drift/simulate?mode=${mode}`, { method: 'POST' });
        const data = await res.json();
        log(`Batch generated successfully (Mode: ${mode}, Rows: ${data.rows}). Running drift analysis...`);
        renderReport(data.report);
      } catch (err) {
        log(`Simulation error: ${err}`);
      }
    }

    async function detectDrift() {
      log("Running two-sample Kolmogorov-Smirnov statistical tests on all 6 features...");
      try {
        const res = await fetch('/api/drift/detect', { method: 'POST' });
        const data = await res.json();
        renderReport(data);
        log(`KS analysis complete. Overall drift: ${data.overall_drift}. Flagged features: [${data.drifted_features.join(', ')}]`);
      } catch (err) {
        log(`Drift test error: ${err}`);
      }
    }

    async function retrainModel() {
      log("Initiating conditional retraining...");
      try {
        const res = await fetch('/api/drift/retrain', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'skipped') {
          log(`Retraining skipped: ${data.message}`);
        } else {
          log(`Candidate trained on ${data.training_rows.toLocaleString()} rows! Candidate Accuracy: ${(data.candidate_accuracy * 100).toFixed(2)}%`);
          document.getElementById("kpi-candidate-accuracy").innerHTML = `Candidate: <strong style="color: #22c55e;">${(data.candidate_accuracy * 100).toFixed(2)}%</strong>`;
        }
      } catch (err) {
        log(`Retraining error: ${err}`);
      }
    }

    async function approveCandidate() {
      log("Evaluating candidate model against Quality Gate (Accuracy >= 50.0%)...");
      try {
        const res = await fetch('/api/drift/approve', { method: 'POST' });
        const data = await res.json();
        log(`Quality Gate Result: ${data.message}`);
        if (data.promoted) {
          log("Active production model hot-reloaded successfully in memory!");
        }
      } catch (err) {
        log(`Approval error: ${err}`);
      }
    }

    window.onload = loadReport;
  </script>
</body>
</html>
"""


@app.get("/drift")
@app.get("/dashboard")
def drift_dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.get("/api/drift/report")
def api_drift_report():
    if run_detect_drift is None:
        return jsonify({"error": "Drift service not available"}), 503
    try:
        report = run_detect_drift()
        return jsonify(report), 200
    except Exception as e:
        logger.exception("event=drift_report_failed")
        return jsonify({"error": str(e)}), 500


@app.post("/api/drift/simulate")
def api_drift_simulate():
    if run_simulate_data is None:
        return jsonify({"error": "Drift service not available"}), 503
    mode = request.args.get("mode") or (request.get_json(silent=True) or {}).get("mode", "stable")
    try:
        sim_result = run_simulate_data(mode=mode)
        report = run_detect_drift()
        sim_result["report"] = report
        return jsonify(sim_result), 200
    except Exception as e:
        logger.exception("event=drift_simulate_failed")
        return jsonify({"error": str(e)}), 500


@app.post("/api/drift/detect")
def api_drift_detect():
    if run_detect_drift is None:
        return jsonify({"error": "Drift service not available"}), 503
    try:
        report = run_detect_drift()
        return jsonify(report), 200
    except Exception as e:
        logger.exception("event=drift_detect_failed")
        return jsonify({"error": str(e)}), 500


@app.post("/api/drift/retrain")
def api_drift_retrain():
    if run_retrain_candidate is None:
        return jsonify({"error": "Drift service not available"}), 503
    try:
        retrain_result = run_retrain_candidate()
        return jsonify(retrain_result), 200
    except Exception as e:
        logger.exception("event=drift_retrain_failed")
        return jsonify({"error": str(e)}), 500


@app.post("/api/drift/approve")
def api_drift_approve():
    global model
    if run_approve_candidate is None:
        return jsonify({"error": "Drift service not available"}), 503
    try:
        approval_result = run_approve_candidate()
        if approval_result.get("promoted"):
            model = load_model()
        return jsonify(approval_result), 200
    except Exception as e:
        logger.exception("event=drift_approve_failed")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify({
        "error": "Not Found",
        "detail": "The requested URL was not found on the server."
    }), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
