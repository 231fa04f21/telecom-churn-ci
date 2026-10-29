"""
Telecom Customer Churn Decision Logic
Practical 1 - First CI Pipeline Using GitHub Actions
"""

def predict_churn(calls_made: int, data_used: int) -> str:
    """
    Predicts whether a telecom customer is likely to CHURN or RETAIN
    based on usage activity thresholds.

    Rules:
    - If calls_made >= 20 and data_used >= 1000 MB: Customer is active and retained ("RETAIN")
    - Otherwise: Customer has critically low engagement and is likely to leave ("CHURN")

    Parameters:
        calls_made (int): Number of outgoing calls made in the billing cycle
        data_used (int): Mobile data volume used in Megabytes (MB)

    Returns:
        str: "RETAIN" if customer meets active thresholds, else "CHURN"
    """
    if calls_made >= 20 and data_used >= 1000:
        return "RETAIN"
    else:
        return "CHURN"


if __name__ == "__main__":
    # Sample customer test
    sample_calls = 50
    sample_data = 3500
    prediction = predict_churn(sample_calls, sample_data)
    print("========================================")
    print(" Telecom Customer Churn Prediction Demo")
    print("========================================")
    print(f"Calls Made : {sample_calls}")
    print(f"Data Used  : {sample_data} MB")
    print(f"Prediction : {prediction}")
    print("========================================")
