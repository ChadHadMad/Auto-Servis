from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import os
import pandas as pd
import psycopg2

REPORT_DIR = "/opt/airflow/data/reports"
REPORT_PATH = f"{REPORT_DIR}/monthly_report.csv"

def generate_report():
    os.makedirs(REPORT_DIR, exist_ok=True)

    conn = psycopg2.connect(host="db", dbname="servis", user="user", password="pass")
    try:
        df = pd.read_sql("SELECT * FROM orders;", conn)
    finally:
        conn.close()

    df.to_csv(REPORT_PATH, index=False)
    print(f"Report generated at {REPORT_PATH}")

default_args = {
    "owner": "autoservis",
    "start_date": days_ago(1),
    "depends_on_past": False,
}

with DAG(
    dag_id="monthly_service_report",
    schedule_interval="@monthly",
    default_args=default_args,
    catchup=False,
) as dag:
    PythonOperator(
        task_id="generate_monthly_report",
        python_callable=generate_report,
    )
