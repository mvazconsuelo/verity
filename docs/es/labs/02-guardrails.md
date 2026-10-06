# Lab 02 — Guardrails

**Aprendés:** cómo reconocer un saludo por significado (no por palabras) sin gastar una llamada
extra al modelo, y dónde termina el trabajo de este módulo a propósito.

## El problema que resuelve

Si alguien escribe "buenas tardes", "qué tal" o "hey", ninguno de esos comparte una sola palabra con
"hola" — un `if "hola" in pregunta` no los reconoce a todos. Pero el *significado* es el mismo, y
los embeddings ya capturan eso.

## Enrutado semántico, no por palabras clave

[`rag/build_index.py`](../../../app/rag/build_index.py) define una lista fija de referencias
(`GREETING_REFERENCES`: "hola", "buenos días", "qué tal"...) y las embebe **una sola vez**, al
construir el índice — se guardan en la tabla `phrases` de `index.db`.

[`gateway/guardrails.py`](../../../app/gateway/guardrails.py), `is_greeting()`: compara el vector de
la pregunta (el mismo que ya se calculó para RAG, cero llamadas extra) contra esos vectores de
referencia. Si el máximo de similitud supera `MIN_SIMILARITY_GREETING` (0.75 — más estricto que el
umbral de RAG, porque acá un falso positivo es más raro de notar), responde directo:

```python
GREETING_ANSWER = "¡Hola! ¿En qué te puedo ayudar?"
```

**Probalo vos:** preguntale "buenas tardes" y despues "hola" — ninguna de las dos gasta una llamada
al modelo de chat (mirá la latencia, o `docker compose logs ollama` mientras preguntás: no debería
aparecer ningún request de `/api/chat` para esas dos).

## Por qué el umbral es más alto que el de RAG

`MIN_SIMILARITY_GREETING = 0.75` contra `MIN_SIMILARITY = 0.5`. Un saludo mal detectado como
pregunta real solo cuesta una llamada de más al LLM (barato). Una pregunta real mal detectada como
saludo nunca llega a responderse de verdad — el costo de equivocarse es más alto en esa dirección,
así que el umbral es más conservador.

## El límite del módulo, a propósito

> "Scope, on purpose: this module is for SMALL, deterministic decisions — not a place to represent
> business topics or actions."

`guardrails.py` decide exactamente dos cosas: ¿hay confianza suficiente? ¿es un saludo? Nada de
"si pregunta por envíos, respondé con la plantilla de envíos" — **eso siempre pasa por RAG real**,
nunca por una respuesta fija en este módulo. La frontera es deliberada: mezclar "decisiones chicas y
deterministas" con "lógica de negocio" en el mismo lugar es, con el tiempo, cómo un módulo chico se
vuelve inmantenible.

## Agregar una categoría nueva

Si algún día necesitás reconocer otra intención (por ejemplo, "quiero hablar con una persona"), el
patrón ya existe: `index_store.py`'s `phrases` table es genérica por `category` — hoy solo tiene
`"greeting"` poblada, pero `save_phrases()`/`read_phrases()` no son específicas de saludos. Antes de
construirlo: ¿hace falta de verdad, o alcanza con que RAG conteste "no tengo esa información" y un
humano lo revise después? No agregues la categoría hasta tener esa respuesta.
