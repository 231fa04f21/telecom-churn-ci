FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY telecom_churn_model.pkl .
COPY metrics.json .
COPY telecom_churn.csv .
COPY drift ./drift

EXPOSE 5000

CMD ["python", "app.py"]

