ARG OLLAMA_VERSION
FROM ollama/ollama:${OLLAMA_VERSION}

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
