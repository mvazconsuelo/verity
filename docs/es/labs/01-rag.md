# Lab 01 — RAG

**Aprendés:** qué es RAG en realidad y por qué existe, qué es un chunk y un vector de embedding,
troceo por secciones, búsqueda por similitud, y por qué existe un umbral de confianza antes de
responder.

## ¿Qué es RAG, en realidad?

Un LLM a secas solo sabe lo que vio durante su entrenamiento — no tiene ni idea de qué dice *tu*
política de envíos, porque ese texto nunca formó parte de su entrenamiento. Podrías intentar pegar
toda tu base de conocimiento en cada prompt, pero eso no escala: hay un límite de cuánto texto puede
procesar un modelo de una vez, cuesta más cuanto más mandás, y cuanto más texto irrelevante incluís,
peor y más lenta tiende a ser la respuesta.

**R**etrieval-**A**ugmented **G**eneration (generación aumentada por recuperación) separa el problema
en dos pasos en vez de uno:

1. **Retrieval (recuperación)**: antes de preguntarle nada al modelo, buscar en tus propios
   documentos las pocas piezas que son realmente relevantes para esta pregunta puntual.
2. **Generation (generación)**: darle al modelo *solo* esas piezas relevantes, como contexto, junto
   con la pregunta.

El modelo nunca "sabe" tus documentos de antemano — en cada pedido, le volvés a contar la parte
relevante, de cero. Por eso también es posible responder honestamente "no tengo esa información": si
la recuperación no encuentra nada con suficiente confianza, no hay contexto del cual inventar una
respuesta en primer lugar (ver [el umbral de confianza](#el-umbral-de-confianza) más abajo).

### ¿Por qué trocear documentos, para empezar?

No podés preguntar útilmente "¿esto es relevante para la pregunta?" sobre un documento entero de una
— un documento largo puede tener un párrafo relevante y muchos que no lo son, y comparar todo el
bloque junto diluiría ese único buen match en ruido. Por eso los documentos se cortan en pedazos más
chicos — **chunks** — lo bastante chicos como para que cada uno hable de más o menos *un solo* tema,
así una búsqueda puede distinguir "esta parte es relevante" de "esta parte no lo es" con precisión
real.

### ¿Qué hay realmente adentro de un vector?

Un **modelo de embeddings** (`bge-m3` acá) lee un pedazo de texto y devuelve una lista de números de
largo fijo — en este proyecto, 1024 de ellos. Esa lista es el **vector** (o "embedding"). No es
arbitraria: el modelo se entrenó para que textos con *significado* parecido terminen con vectores que
quedan cerca entre sí en ese espacio de 1024 dimensiones, y textos con significado distinto terminen
lejos — sin importar las palabras exactas que se usaron. "¿Cuánto tarda el envío?" y "¿cuándo llega mi
pedido?" quedan cerca aunque casi no comparten palabras.

"Cerca" se mide con **similitud coseno**: un número (0 a 1, para estos vectores normalizados) que
dice qué tan alineados están dos vectores — 1 significa prácticamente el mismo significado, 0
significa sin relación. Ese es el `score` que vas a ver más abajo, y el número contra el que se
compara `MIN_SIMILARITY`.

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
