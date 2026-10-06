#!/bin/sh
set -e

# Arranca el servidor en segundo plano
ollama serve &
server_pid=$!

# Espera a que la API responda
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Descarga cada modelo de la lista (separados por comas) si aún no está en el volumen
for modelo in $(echo "${MODELS}" | tr ',' ' '); do
  echo "Descargando modelo: ${modelo}"
  ollama pull "${modelo}"
done
echo "Modelos listos: ${MODELS}"

# Mantiene el contenedor vivo mientras corra el servidor
wait "$server_pid"
