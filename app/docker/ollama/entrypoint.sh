#!/bin/sh
set -e

# Starts the server in the background
ollama serve &
server_pid=$!

# Waits for the API to respond
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Downloads each model in the list (comma-separated) if it's not already in the volume
for model in $(echo "${MODELS}" | tr ',' ' '); do
  echo "Downloading model: ${model}"
  ollama pull "${model}"
done
echo "Models ready: ${MODELS}"

# Keeps the container alive while the server runs
wait "$server_pid"
