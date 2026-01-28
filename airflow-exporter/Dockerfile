FROM python:3.8-slim

WORKDIR /app

COPY airflow_exporter.py .

RUN pip install prometheus_client requests

EXPOSE 9112

CMD ["python", "airflow_exporter.py"]