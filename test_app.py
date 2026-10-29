"""
Automated Tests for Telecom Churn Flask Prediction Application
Practical 5 - Continuous Delivery of an ML Prediction Application
"""

import unittest
from app import app


class TestPredictionApplication(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.get_json()["service"], "telecom-churn-prediction")

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
        self.assertEqual(
            response.get_json()["prediction"],
            "CHURN"
        )
        self.assertEqual(
            response.get_json()["prediction_code"],
            0
        )

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
        self.assertEqual(
            response.get_json()["prediction"],
            "CHURN"
        )
        self.assertEqual(
            response.get_json()["prediction_code"],
            1
        )

    def test_missing_field_validation(self):
        response = self.client.post(
            "/predict",
            json={
                "age": 25,
                "calls_made": 90
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "missing_fields",
            response.get_json()
        )


if __name__ == "__main__":
    unittest.main()
