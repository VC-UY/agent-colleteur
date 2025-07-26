#!/bin/bash

DB_NAME="machine_monitoring"
OUTPUT_DIR="./exports"

# Créer le répertoire de sortie s'il n'existe pas
mkdir -p "$OUTPUT_DIR"

# Obtenir la liste des collections
collections=$(mongo --quiet --eval "db.getCollectionNames()" "$DB_NAME" | sed -e 's/[][]//g' -e 's/ //g' -e 's/"//g' -e 's/,/ /g')

# Exporter chaque collection
for collection in $collections
do
  echo "Exporting collection: $collection"
  mongoexport --db="$DB_NAME" --collection="$collection" --type=csv --out="$OUTPUT_DIR/${collection}.csv"
done