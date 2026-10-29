"""
Telecom Churn Prediction ML Model Training Program
Practical 2 - Student Result Prediction ML Model adapted to Telecom Churn
"""

import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def load_dataset(filepath="telecom_churn.csv"):
    """Loads and returns the telecom churn dataset."""
    print("Loading dataset from", filepath, "...")
    data = pd.read_csv(filepath)
    print("Dataset loaded successfully.")
    print("Number of records:", len(data))
    return data


def train_model():
    """Trains the Logistic Regression pipeline, evaluates performance, and saves artifacts."""
    data = load_dataset()

    features = [
        "age",
        "num_dependents",
        "estimated_salary",
        "calls_made",
        "sms_sent",
        "data_used"
    ]

    X = data[features]
    y = data["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print("Training records:", len(X_train))
    print("Testing records :", len(X_test))

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    ])

    print("Training model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions)

    print("\nModel Evaluation")
    print("----------------")
    print("Accuracy:", round(accuracy, 4))
    print("\nConfusion Matrix:")
    print(matrix)

    joblib.dump(model, "telecom_churn_model.pkl")
    print("\nModel saved as telecom_churn_model.pkl")

    metrics = {
        "accuracy": float(accuracy),
        "training_records": len(X_train),
        "testing_records": len(X_test)
    }

    with open("metrics.json", "w") as file:
        json.dump(metrics, file, indent=4)

    print("Metrics saved as metrics.json")
    return accuracy


if __name__ == "__main__":
    train_model()
