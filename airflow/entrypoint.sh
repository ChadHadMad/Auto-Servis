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

INIT_FLAG="/opt/airflow/data/initialized"

if [ ! -f "$INIT_FLAG" ]; then
  echo "Airflow DB init..."
  airflow db init

  echo "Kreiranje admin korisnika..."
  airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@autoservis.com || true

  touch "$INIT_FLAG"
fi

echo "Provjera Airflow baze (airflow db check)..."
for i in {1..30}; do
  if airflow db check; then
    echo "DB OK"
    break
  fi
  echo "DB još nije spremna... ($i/30)"
  sleep 2
done

exec airflow "$@"
