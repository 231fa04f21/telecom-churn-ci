"""
Automated Tests for Telecom Churn Prediction API with Logging & Error Tracking
MLOps Practical 11 - Logging and Error Tracking for Deployed Telecom Churn API
"""

import unittest
from app import app


class TestPredictionApplication(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.get_json()["service"], "telecom-churn-prediction")
        self.assertIn("X-Request-ID", response.headers)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertIn("X-Request-ID", response.headers)

    def test_low_risk_retained_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 25,
                "num_dependents": 4,
                "estimated_salary": 140000,
                "calls_made": 90,
                "sms_sent": 50,
                "data_used": 9000
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["prediction"], "RETAIN")
        self.assertEqual(response.get_json()["prediction_code"], 0)
        self.assertIn("X-Request-ID", response.headers)

    def test_high_risk_churn_prediction(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 70,
                "num_dependents": 0,
                "estimated_salary": 30000,
                "calls_made": 5,
                "sms_sent": 2,
                "data_used": 100
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["prediction"], "CHURN")
        self.assertEqual(response.get_json()["prediction_code"], 1)
        self.assertIn("X-Request-ID", response.headers)

    def test_missing_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 25,
                "calls_made": 90
            }
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("missing_fields", response.get_json())
        self.assertIn("X-Request-ID", response.headers)

    def test_unknown_route(self):
        response = self.client.get("/not-a-real-route")
        self.assertEqual(response.status_code, 404)
        self.assertIn("X-Request-ID", response.headers)


if __name__ == "__main__":
    unittest.main()
