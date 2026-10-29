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
from flask import Flask, jsonify, request, g, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

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


@app.errorhandler(404)
def handle_404(e):
    return jsonify({
        "error": "Not Found",
        "detail": "The requested URL was not found on the server."
    }), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
