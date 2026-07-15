FROM python:3.12-slim

RUN pip install mlflow>=2.13.0 psycopg2-binary boto3 azure-storage-blob

EXPOSE 5000

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000",
     "--backend-store-uri", "postgresql://app:dev_password@postgres:5432/readmission",
     "--default-artifact-root", "/mlflow/artifacts"]