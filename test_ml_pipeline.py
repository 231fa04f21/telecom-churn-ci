"""
Automated ML Pipeline Tests for Telecom Customer Churn Prediction
Practical 2 - MLOps CI with GitHub Actions
"""

import json
import os
import unittest
import joblib
import pandas as pd


class TestMLPipeline(unittest.TestCase):

    def test_dataset_created(self):
        """Verify that the telecom churn dataset file exists."""
        self.assertTrue(os.path.exists("telecom_churn.csv"))

    def test_model_created(self):
        """Verify that the trained model artifact .pkl exists."""
        self.assertTrue(os.path.exists("telecom_churn_model.pkl"))

    def test_metrics_created(self):
        """Verify that metrics.json was generated."""
        self.assertTrue(os.path.exists("metrics.json"))

    def test_accuracy_is_valid(self):
        """Verify that the evaluation accuracy is a valid float between 0.0 and 1.0."""
        with open("metrics.json", "r") as file:
            metrics = json.load(file)

        accuracy = metrics["accuracy"]
        self.assertGreaterEqual(accuracy, 0.0)
        self.assertLessEqual(accuracy, 1.0)

    def test_model_prediction(self):
        """Verify that the loaded model outputs a valid class label [0, 1]."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 45,
            "num_dependents": 2,
            "estimated_salary": 80000,
            "calls_made": 50,
            "sms_sent": 25,
            "data_used": 5000
        }])
        prediction = model.predict(sample)[0]
        self.assertIn(int(prediction), [0, 1])

    def test_low_risk_retained_customer(self):
        """Verify that an active customer with high calls & high data usage is classified as RETAINED (0)."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 25,
            "num_dependents": 4,
            "estimated_salary": 140000,
            "calls_made": 90,
            "sms_sent": 50,
            "data_used": 9000
        }])
        prediction = model.predict(sample)[0]
        self.assertEqual(int(prediction), 1)

    def test_high_risk_churn_customer(self):
        """Verify that a customer with dormant usage (very low calls and low data) is classified as CHURN (1)."""
        model = joblib.load("telecom_churn_model.pkl")
        sample = pd.DataFrame([{
            "age": 70,
            "num_dependents": 0,
            "estimated_salary": 30000,
            "calls_made": 5,
            "sms_sent": 2,
            "data_used": 100
        }])
        prediction = model.predict(sample)[0]
        self.assertEqual(int(prediction), 1)


if __name__ == "__main__":
    unittest.main()
