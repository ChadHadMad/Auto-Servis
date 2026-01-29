#!/bin/bash
set -e

USER=airflow
GROUP=50000

DIRS=(
  /opt/airflow/logs
  /opt/airflow/dags
  /opt/airflow/plugins
  /opt/airflow/data
)

echo "Postavljanje vlasništva na foldere..."
for dir in "${DIRS[@]}"; do
  if [ -d "$dir" ]; then
    chown -R ${USER}:${GROUP} "$dir" || echo "Upozorenje: Ne mogu promijeniti vlasništvo za $dir"
  else
    echo "Folder $dir ne postoji, preskačem..."
  fi
done

if [ ! -f /opt/airflow/airflow.db ] && [ ! -f /opt/airflow/initialized ]; then
  echo "Inicijalizacija baze..."
  airflow db init

  echo "Kreiranje admin korisnika..."
  airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@autoservis.com

  touch /opt/airflow/initialized
fi

exec airflow "$@"