# Lab 05 — Evaluación

**Aprendés:** cómo se mide objetivamente si el bot responde bien, qué es una puerta de calidad, y
por qué cada respuesta lleva un `prompt_hash` pegado.

## El golden set

[`app/eval/golden.jsonl`](../../../app/eval/golden.jsonl), una pregunta por línea:

```json
{"id": "q01", "question": "¿Cuánto tarda el envío estándar?", "expected": "De 3 a 5 días hábiles.", "keywords": ["3 a 5"], "source": "envios.md", "answerable": true}
```

- `answerable: true` → pasa si la respuesta contiene **todas** las `keywords` (no es un match
  exacto de texto — el modelo puede redactarlo distinto, lo que importa es que el dato esté).
- `answerable: false` → pasa si la respuesta *admite que no sabe* (una lista fija de frases en
  [`run_eval.py`](../../../app/eval/run_eval.py): "no tengo", "no dispongo"...). Son preguntas
  inventadas a propósito, sin respuesta en ningún documento — miden si el bot inventa cuando no
  sabe, que es el error más caro de un bot de atención al cliente.

Se escriben a mano — hubo un generador automático con `qwen2.5:1.5b` que se descartó: con un modelo
tan chico, las preguntas que inventaba necesitaban tanta revisión manual que no ahorraba tiempo real.

## Las métricas

`run_eval.py` calcula, sobre todo el set:

| Métrica | Qué mide |
| --- | --- |
| `accuracy` | % de todas las preguntas que pasaron (contestables + no contestables) |
| `accuracy_answerable` | % de las contestables que sí se contestaron bien |
| `refusal_rate` | % de las NO contestables que el bot rechazó correctamente |
| `retrieval_recall` | De las contestables, % donde el documento correcto apareció entre los recuperados (más estricto que `accuracy`: podés "acertar por casualidad" sin este) |

## La puerta de calidad

`config.env`:
```
EVAL_MIN_ACCURACY_ANSWERABLE=0.90
EVAL_MIN_REFUSAL_RATE=0.90
EVAL_MIN_RETRIEVAL_RECALL=0.90
```

Vacío = no exigido (ver `# EVAL_MIN_ACCURACY=0.90`, comentada: hoy no se exige la métrica global, solo
las tres específicas). Si alguna métrica configurada no llega al mínimo, `run_eval.py` termina con
código de salida `1` — útil si algún día lo volvés a enganchar a algo automatizado.

**Probalo vos — bajá el umbral artificialmente y mirá pasar algo que antes fallaba:**
```bash
EVAL_MIN_RETRIEVAL_RECALL=0.0 docker compose run --rm evaluator python eval/run_eval.py
```

## `prompt_hash` y `release`

Cada respuesta del `/ask` (ver [`gateway/endpoints.py`](../../../app/gateway/endpoints.py)) incluye:

- **`prompt_hash`**: hash SHA-256 (8 caracteres) de `system.md` + `template.md`. Cambia si cambia el
  *texto* del prompt, aunque el nombre del archivo siga igual — no hay forma de tocar el prompt sin
  que se note en cada respuesta.
- **`release`**: el tag de la imagen que está respondiendo (`APP_VERSION`).

El reporte del examen (`eval/report/eval-result.json` + `.md`) guarda ambos junto con el commit de
git — así un reporte viejo siempre dice exactamente qué código, qué prompt y qué documentos estaba
usando, sin tener que reconstruirlo de memoria.

## Correr el examen

```bash
make local   # elegí "Examine" en el menú
```

El reporte completo queda en `app/eval/report/eval-result.md` (legible) y `.json` (para leer por
script). Mirá la tabla `<details>` con el detalle pregunta por pregunta — incluye si la recuperación
trajo el documento correcto (✅/❌/➖), no solo si la respuesta final pasó.

---

**[English](../../labs/05-evaluation.md)**
