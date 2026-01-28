import os
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import psycopg2

def generate_report():
    os.makedirs("/opt/airflow/reports", exist_ok=True)  # promenjeno ovde

    conn = psycopg2.connect(host="db", dbname="servis", user="user", password="pass")
    query = "SELECT * FROM orders;"
    df = pd.read_sql(query, conn)
    conn.close()

    report_path = "/opt/airflow/reports/monthly_report.csv"  # i ovde
    df.to_csv(report_path, index=False)
    print(f"Report generated at {report_path}")

dag = DAG('monthly_service_report', start_date=days_ago(1), schedule_interval='@monthly')

generate_task = PythonOperator(
    task_id='generate_monthly_report',
    python_callable=generate_report,
    dag=dag
)
