# Usar el bot

Dos formas de hablarle una vez que está arriba (`make local`, o `docker compose up` en `app/`): el
script interactivo, o la API directa con `curl`. Las dos hablan con el mismo gateway — no hay
ninguna diferencia en lo que podés hacer, solo en cómo lo hacés.

## Opción 1: `chat.sh`

```bash
make chat
# o directo: app/run/chat.sh
```

Un bucle simple alrededor de `/ask`: escribís una pregunta, te responde, repetís. Línea en blanco o
Ctrl+D para salir. Si el gateway arrancó con claves reales (no `AUTH_DISABLED=true`), pasá la tuya:

```bash
API_KEY=tu-clave app/run/chat.sh
```

Son [~50 líneas de bash](../../app/run/chat.sh) — leelo si querés ver el mínimo necesario para
hablarle a la API desde un script, sin más dependencia que `curl` y `python3`.

## Opción 2: la API directa

Tres endpoints. Todos (menos `/health`) necesitan la cabecera `x-api-key`; ninguno necesita nada más
**salvo** que hayas configurado `ORIGIN_VERIFY_SECRET` vos mismo (vacío por default — ver
[`gateway/auth.py`](../../app/gateway/auth.py)).

### `GET /health`

No necesita clave de API — es el único endpoint que cualquier cosa (un balanceador, un script, vos)
puede llamar sin credenciales, justamente para que los chequeos de disponibilidad no necesiten un
secreto.

```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "release": "local"}
```

### `GET /config`

Necesita `x-api-key`. La configuración efectiva del bot — lo que lee el evaluador antes de correr el
examen, y una forma rápida de chequear con qué estás hablando realmente.

```bash
curl http://localhost:8000/config -H "x-api-key: tu-clave"
```
```json
{
  "release": "local",
  "prompt_hash": "a1b2c3d4",
  "temperature": 0,
  "model": "qwen2.5:1.5b",
  "rag": true,
  "embedding_model": "bge-m3",
  "top_k": 3,
  "min_similarity": 0.5,
  "min_similarity_saludo": 0.75,
  "index": {"embedding_model": "bge-m3", "n_documents": 4, "n_chunks": 13, "dimension": 1024, "...": "..."}
}
```

### `POST /ask`

Necesita `x-api-key`. El único endpoint que gasta una llamada al modelo (salvo que un guardrail lo
corte antes — ver [Lab 02](labs/02-guardrails.md)).

```bash
curl -X POST http://localhost:8000/ask \
  -H "content-type: application/json" \
  -H "x-api-key: tu-clave" \
  -d '{"question": "¿cuánto tarda el envío estándar?"}'
```
```json
{
  "answer": "El envío estándar tarda de 3 a 5 días hábiles.",
  "model": "qwen2.5:1.5b",
  "tokens": 14,
  "release": "local",
  "prompt_hash": "a1b2c3d4",
  "temperature": 0,
  "sources": ["envios.md#Plazos"]
}
```

`sources` te dice exactamente qué documento y sección respaldó la respuesta (vacío si la pregunta se
cortó por un guardrail — un saludo, o "no tengo esa información"). `question` es obligatorio, de 1 a
`MAX_QUESTION_CHARS` (2000 por default) — cualquier cosa fuera de ese rango da `422` antes de que la
pregunta llegue siquiera a RAG.

### Errores que vas a ver de verdad

| Status | Cuándo | Ver |
| --- | --- | --- |
| `401` | Falta `x-api-key` o está mal | [`gateway/auth.py`](../../app/gateway/auth.py) |
| `403` | `ORIGIN_VERIFY_SECRET` está configurado y la cabecera no coincide (no aplica por default) | [Break the Platform #7](break.md#7-origin_verify_secret-por-default-no-hace-nada) |
| `422` | Pregunta vacía o demasiado larga | Validación de Pydantic en [`gateway/endpoints.py`](../../app/gateway/endpoints.py) |
| `429` | Límite de peticiones alcanzado | [Break the Platform #6](break.md#6-rate-limit-429-con-retry-after) |
| `502` | Ollama no respondió | `gateway/endpoints.py`, atrapa `httpx.HTTPError` |

## Qué poner en `app/knowledge/`

Esto es lo que realmente alimenta los embeddings — hacelo bien y la búsqueda funciona; hacelo mal y
el bot no encuentra nada, o devuelve chunks ruidosos sin relación. Mecánica completa en
[Lab 01](labs/01-rag.md); acá, qué hacer en la práctica al escribir un documento:

1. **Con un `.md` por área de tema alcanza** — no hace falta un archivo por cada dato suelto. El
   propio `app/knowledge/envios.md` del proyecto cubre plazos, costos y cobertura en un solo
   archivo, dividido en secciones.
2. **Estructurá con encabezados `## `, un subtema por sección.** Cada sección `##` se convierte en su
   propio chunk — una pregunta matchea una *sección*, no el documento entero. Un documento sin
   ningún `##` se trocea por cantidad de caracteres, mucho menos preciso (puede cortar una oración
   justo donde caiga `CHUNK_MAX_CHARS`).
3. **Mantené las secciones enfocadas y razonablemente cortas.** Si una sección supera
   `CHUNK_MAX_CHARS` (1200 caracteres por default), se parte en más con solape — no está mal, pero
   es señal de que probablemente cubre más de un tema y buscaría mejor si la dividís vos mismo en
   dos `##`.
4. **No enterrés la respuesta en un párrafo gigante de datos sin relación.** Compará:

   ```markdown
   <!-- bien: una pregunta sobre costo solo trae texto relevante a costo -->
   ## Costos
   El envío estándar cuesta $4.99, gratis en pedidos desde $50.

   <!-- peor: costo de envío, política de devoluciones y horario, todo junto -->
   ## Información general
   El envío estándar cuesta $4.99... Las devoluciones se aceptan hasta 30 días...
   El local abre de 9 a 18...
   ```

   La primera versión hace que una búsqueda por "costo de envío" traiga *solo* texto de costo de
   envío. La segunda arrastra contenido sin relación como parte del mismo chunk, diluyendo el match.
5. **Validá antes de confiar en que quedó bien tomado:**
   ```bash
   docker run --rm -v "$PWD/app":/work -w /work python:3.11-slim python3 -m rag.validate_knowledge knowledge
   ```
   Atrapa problemas de formato, archivos demasiado grandes (`MAX_FILE_KB`), y extensiones no
   soportadas (solo se lee `.md` — el resto se ignora en silencio, con un aviso).
6. **Reconstruí después de cada cambio** — `knowledge/` se hornea en la imagen al construirla, no se
   monta en vivo. Ver [Break the Platform #2](break.md#2-cambi%C3%A9-un-documento-y-el-bot-sigue-respondiendo-lo-viejo)
   si esto te agarra desprevenido.
7. **Escribí 2-3 preguntas del golden set por documento, a medida que avanzás** (ver
   [Lab 05](labs/05-evaluation.md)) — es mucho más fácil escribirlas mientras te acordás qué
   acabás de poner en el documento que reconstruirlo después.

---

**[English](../usage.md)**
