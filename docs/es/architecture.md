# Arquitectura

![Arquitectura de Verity](../images/architecture.es.svg)

## El camino de una pregunta

1. **`usuario → gateway`** (`POST /ask`): el gateway valida la clave de API, el rate limit y el
   tamaño de la pregunta antes de tocar nada más (`gateway/auth.py`).
2. **`gateway → ollama`**: la pregunta se embebe con `bge-m3` (mismo modelo que indexó los
   documentos — `retrieval.py` rechaza arrancar si no coinciden, ver abajo).
3. **Guardrails, antes de gastar una llamada al modelo de chat** (`gateway/guardrails.py`):
   - ¿El vector de la pregunta se parece más a un saludo que a cualquier chunk? → responde fijo,
     sin RAG ni LLM.
   - ¿El mejor chunk encontrado no llega al umbral de similitud (`MIN_SIMILARITY`)? → responde
     "no tengo esa información", sin LLM.
4. Si pasó los guardrails: el contexto recuperado se arma en el prompt y recién ahí se llama al
   modelo de chat (`qwen2.5:1.5b`).

## Lo que NO está en el camino de una pregunta

- **`indexer`**: corre una vez al arrancar el stack (`depends_on: service_completed_successfully`
  en `docker-compose.yml`) y termina. El gateway nunca reindexa en caliente — si cambiás
  `knowledge/`, hay que reconstruir la imagen.
- **`evaluator`**: nunca arranca con `docker compose up` (tiene `profiles: ["evaluator"]`). Se
  invoca a mano, contra un gateway que ya está arriba.
- **`DVC` + `SeaweedFS`**: perfil `"dvc"`, tampoco arranca con `up`. Resuelve un problema distinto
  (versionar los documentos fuente) que no tiene nada que ver con responder preguntas.
- **`GitHub Actions`**: ni siquiera corre en tu máquina — y **nunca llega a tocar el runtime**. No
  hay flecha de CI hacia ningún contenedor del diagrama, a propósito: ver
  [Lab 06](labs/06-github-actions-ci.md) para por qué.

## Por qué el índice es de solo lectura desde el gateway

`rag/build_index.py` (el `indexer`) es el único que escribe `index.db`. El gateway (`retrieval.py`)
lo abre una vez (`@lru_cache`) y nunca más escribe ahí. Esto hace que el gateway pueda tener
múltiples réplicas sin coordinarse entre sí — ninguna le escribe nada a otra. (Hoy corre una sola
réplica; la propiedad queda gratis si algún día hiciera falta más de una.)

## Por qué `knowledge/` se hornea en la imagen, no se monta en caliente

El Dockerfile del gateway hace `COPY knowledge ./knowledge` — es parte de la imagen, no un volumen.
Esto significa que **la imagen entera es la unidad de versión**: el tag de una imagen fija a la vez
el código, el prompt y los documentos que va a usar para responder. Cambiar un documento sin
reconstruir la imagen no tiene efecto (ver [Lab 03](labs/03-docker.md) para el detalle, y
[Break the Platform #2](break.md#2-cambi%C3%A9-un-documento-y-el-bot-sigue-respondiendo-lo-viejo)
para verlo fallar en vivo).

---

**[English](../architecture.md)**
