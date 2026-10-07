# Lab 01 — RAG

**Aprendés:** troceo por secciones, embeddings, búsqueda por similitud, y por qué existe un umbral
de confianza antes de responder.

## El documento de ejemplo

[`app/knowledge/envios.md`](../../../app/knowledge/envios.md):

```markdown
# Envíos

## Plazos
El envío estándar tarda de 3 a 5 días hábiles. El envío express tarda de 24 a 48 horas.

## Costos
El envío estándar cuesta $4.99, gratis en pedidos desde $50...

## Cobertura
Enviamos a todo el territorio nacional...
```

## Cómo se trocea

[`rag/loaders.py`](../../../app/rag/loaders.py), función `chunk_md()`: parte el texto por cada
`## ` (los `###` NO cuentan como corte — son subtítulos dentro de la misma sección). El título
(`# Envíos`) se antepone a cada chunk, así cada uno se entiende sin el resto del documento.
`envios.md` da 3 chunks: uno por `Plazos`, `Costos` y `Cobertura`.

Si una sección es más larga que `CHUNK_MAX_CHARS` (1200 por default), se parte en varios con
`CHUNK_OVERLAP_CHARS` (150) de solape — para que una frase no quede cortada justo en el límite entre
dos chunks sin contexto de ninguno de los dos.

**Probalo vos:**
```bash
docker run --rm -v "$PWD/app":/work -w /work python:3.11-slim python3 -m rag.validate_knowledge knowledge
```

## Cómo se embeben e indexan

[`rag/build_index.py`](../../../app/rag/build_index.py) (el servicio `indexer`, corre una vez al
arrancar): le pide a Ollama un vector por chunk (`bge-m3`), y los guarda en `index.db`
([`rag/index_store.py`](../../../app/rag/index_store.py), sobre `sqlite-vec`) junto con metadata
(`embedding_model`, `n_chunks`, `knowledge_hash`).

## Cómo se busca

[`gateway/retrieval.py`](../../../app/gateway/retrieval.py), `retrieve()`: embebe la pregunta con el
mismo modelo, y trae los `TOP_K` (3 por default) chunks más parecidos por similitud coseno.

## El umbral de confianza

El chunk más parecido tiene un *score* entre 0 y 1. Si no llega a `MIN_SIMILARITY` (0.5 por
default), el bot **no llama al modelo de chat** — responde "No tengo esa información." directo
(`gateway/guardrails.py`, `is_confident()`). Esto evita que, ante una pregunta fuera de tema, el
modelo "invente" una respuesta con el contexto equivocado que sí encontró.

**Probalo vos:** preguntale algo que no tiene nada que ver con tu negocio (`"¿cuál es la capital de
Francia?"`) y mirá que la respuesta no gasta ni una llamada al LLM — compará la latencia contra una
pregunta real.

## Ver qué quedó indexado

```bash
make local   # elegí "View the index" en el menú
```

Te muestra, chunk por chunk, exactamente lo que el gateway tiene disponible para buscar — útil para
depurar "¿por qué el bot no encontró esto?" sin adivinar.

---

**[English](../../labs/01-rag.md)**
