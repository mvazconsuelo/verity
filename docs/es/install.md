# Instalación

## Necesitás

- **Docker** (con Docker Compose v2 — viene incluido en Docker Desktop).
- **uv** (solo si vas a usar DVC o correr los tests fuera de Docker) — [instalarlo](https://docs.astral.sh/uv/getting-started/installation/).
- Nada de nube, nada de cuentas, nada de credenciales. Todo corre en tu máquina.
- RAM libre: los modelos de Ollama (`qwen2.5:1.5b` + `bge-m3`) pesan ~2.5 GB combinados y se
  descargan la primera vez que levantás el stack.

## 1. Cloná y levantá el bot

```bash
git clone <tu-fork-o-el-repo> verity && cd verity
make local
```

`make local` (que llama a [`app/run/run.sh`](../../app/run/run.sh)) hace, en este orden:

1. Si hay `.dvc/` inicializado, hace `dvc pull` (si todavía no configuraste DVC, sigue con lo que
   ya esté en `app/knowledge/` — ver paso 3).
2. Valida los documentos (`rag/validate_knowledge`): formato, tamaño, que no esté vacío.
3. Construye las imágenes y levanta el stack (`ollama`, `indexer`, `gateway`) — la primera vez
   descarga los modelos, tarda unos minutos.
4. Te deja elegir: examinar con el golden set, ver el índice construido, o chatear directo.

Al final, el bot queda arriba en `http://localhost:8000`.

## 2. Probalo

```bash
make chat
```

O con `curl` directo:

```bash
curl -X POST http://localhost:8000/ask \
  -H "content-type: application/json" \
  -H "x-api-key: cualquier-cosa" \
  -d '{"question": "¿cuánto tarda el envío estándar?"}'
```

(Si no pusiste `API_KEYS` en tu entorno, `run.sh` ya corrió con `AUTH_DISABLED=true` — ver
[Lab 02: Guardrails](labs/02-guardrails.md) para el detalle de por qué eso es seguro solo en local.)

## 3. (Opcional) Versionar tus propios documentos con DVC

Si vas a modificar `app/knowledge/` y querés guardar su historial más allá de git (útil si en algún
momento son demasiados o demasiado pesados para versionar como texto plano):

```bash
make dvc-setup   # una sola vez: levanta SeaweedFS y lo configura como remoto
# ... editás app/knowledge/ ...
make dvc-push    # publica tus cambios
make dvc-pull    # los trae de vuelta (por ejemplo, en otra máquina)
```

Mirá lo que quedó guardado en `http://localhost:8888/buckets/knowledge/` — interfaz web incluida,
sin configurar nada aparte. Detalle completo: [Lab 04](labs/04-dvc-seaweedfs.md).

## 4. Adaptalo a tu propio negocio

1. Reemplazá los `.md` de `app/knowledge/` por tu documentación real (ver
   [Lab 01](labs/01-rag.md) para el formato que espera el troceador).
2. Escribí 2-3 preguntas por documento en `app/eval/golden.jsonl` (ver [Lab 05](labs/05-evaluation.md)).
3. Ajustá `config.env` si hace falta (`MIN_SIMILARITY`, `TOP_K`, los umbrales `EVAL_MIN_*`).
4. `make local` de nuevo y mirá el reporte del examen antes de dar por buena la respuesta del bot.

## Si algo no arranca

- **El gateway no arranca**: revisá que tengas `API_KEYS` en tu entorno, o `AUTH_DISABLED=true`
  (solo para probar — nunca en un entorno expuesto). Ver [Break the Platform](break.md#1-el-gateway-no-arranca).
- **El examen tarda mucho / falla con timeout**: la primera corrida descarga los modelos; corré
  `docker compose logs ollama` para ver el progreso.
- Más escenarios reales, provocados a propósito: [Break the Platform](break.md).

---

**[English](../install.md)**
