from prometheus_client import start_http_server, Gauge
import requests
import time
import os

AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

# Primjer metrike: broj zadataka u statusu "running"
running_tasks_gauge = Gauge('airflow_running_tasks', 'Number of running tasks in Airflow')

def fetch_running_tasks():
    try:
        # Primjer API poziva za dohvat trenutnih taskova iz Airflow API-ja
        response = requests.get(
            f"{AIRFLOW_BASE_URL}/api/v1/dags?only_active=true",
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        running_tasks = 0
        for dag in data.get('dags', []):
            # Pošto Airflow API nije uniforman za sve verzije, ovdje je primjer kako bi se moglo dohvatiti info o taskovima
            # Ovdje možeš prilagoditi API poziv za tvoj Airflow setup (npr. /dags/{dag_id}/dagRuns)
            # Za sad ćemo samo broj aktivnih DAG-ova koristiti kao proxy za metriku
            running_tasks += 1

        running_tasks_gauge.set(running_tasks)
    except Exception as e:
        print(f"Error fetching airflow metrics: {e}")

def main():
    start_http_server(9112)
    print("Airflow Exporter started on port 9112")
    while True:
        fetch_running_tasks()
        time.sleep(15)

if __name__ == "__main__":
    main()
