#!/bin/bash
set -e

# Postavi vlasnike na foldere
chown -R airflow:50000 /opt/airflow/logs
chown -R airflow:50000 /opt/airflow/dags
chown -R airflow:50000 /opt/airflow/plugins
chown -R airflow:50000 /opt/airflow/data

# Inicijaliziraj bazu ako nije inicijalizirana
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

    # Kreiraj fajl koji označava da je inicijalizacija gotova
    touch /opt/airflow/initialized
fi

# Pokreni airflow s argumentima iz docker-compose
exec airflow "$@"

