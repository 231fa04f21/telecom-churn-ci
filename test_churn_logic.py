"""
Unit Tests for Telecom Customer Churn Logic
Practical 1 - First CI Pipeline Using GitHub Actions
"""

import unittest
from churn_logic import predict_churn


class TestChurnLogic(unittest.TestCase):

    def test_retain_case(self):
        """Active customer meeting both call and data thresholds should be RETAINED."""
        result = predict_churn(calls_made=50, data_used=3500)
        self.assertEqual(result, "RETAIN")

    def test_churn_due_to_low_calls(self):
        """Customer with high data usage but critically low calls (< 20) should CHURN."""
        result = predict_churn(calls_made=10, data_used=3500)
        self.assertEqual(result, "CHURN")

    def test_churn_due_to_low_data(self):
        """Customer with high call volume but low data usage (< 1000 MB) should CHURN."""
        result = predict_churn(calls_made=50, data_used=400)
        self.assertEqual(result, "CHURN")


if __name__ == "__main__":
    unittest.main()

