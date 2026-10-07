# 💥 Break the Platform

Fallas reales, provocadas a propósito. El patrón de cada una: **provocar → qué ves → dónde mirar →
causa → arreglo → lección.** Nada acá es hipotético: todas se reprodujeron corriendo el proyecto tal
cual está en el repo.

---

## 1. El gateway no arranca

**Provocar:**
```bash
cd app && unset API_KEYS && docker compose up gateway
```

**Qué ves:** el contenedor `gateway` sale inmediatamente, sin quedar en `Restarting`. En los logs:
```
RuntimeError: Set API_KEYS (export it yourself before bringing up the stack; or AUTH_DISABLED=true for testing only)
```

**Dónde mirar:** [`gateway/auth.py`](../../app/gateway/auth.py) — la comprobación corre al *importar*
el módulo, no al recibir la primera petición.

**Causa:** es a propósito: cerrado por default. No existe una versión del gateway que acepte
tráfico sin clave "por accidente" — o la tenés, o directamente no arranca.

**Arreglo:** `export API_KEYS=lo-que-sea` (o `AUTH_DISABLED=true`, **solo para probar en local**)
antes de `docker compose up`.

**Lección:** fail-fast en el arranque es más barato que fail-open en producción. El costo lo pagás
una vez, al levantar el stack — no cada vez que alguien manda una petición sin clave.

---

## 2. Cambié un documento y el bot sigue respondiendo lo viejo

**Provocar:** editá `app/knowledge/envios.md`, guardá, y preguntale al bot sobre eso sin reconstruir
nada.

**Qué ves:** la respuesta sigue basada en el contenido anterior.

**Dónde mirar:** [`app/docker/gateway/Dockerfile`](../../app/docker/gateway/Dockerfile) — tiene
`COPY knowledge ./knowledge`.

**Causa:** `knowledge/` se hornea en la imagen al construirla, no se monta en vivo desde el disco.
Editar el archivo en tu filesystem no cambia nada dentro del contenedor que ya está corriendo.

**Arreglo:** `docker compose build && docker compose up -d` (o, más simple, `make local` de nuevo —
`run.sh` ya hace el build).

**Lección:** la imagen entera es la unidad de versión. Un *tag* de imagen fija código + prompt +
documentos a la vez — por diseño, no por descuido (ver [Arquitectura](architecture.md)).

---

## 3. El índice fue construido con otro modelo de embeddings

**Provocar:** levantá el stack, después cambiá `EMBEDDING_MODEL` en `config.env` a otra cosa (por
ejemplo `nomic-embed-text`) y reiniciá solo el `gateway` sin reconstruir el índice.

**Qué ves:** `500` en cualquier pregunta que use RAG:
```
The index was built with 'bge-m3' and the gateway uses 'nomic-embed-text': rebuild it with make up
```

**Dónde mirar:** [`gateway/retrieval.py`](../../app/gateway/retrieval.py), función `load_index()`.

**Causa:** los vectores de dos modelos distintos no son comparables entre sí — mezclarlos daría
resultados de búsqueda sin sentido, silenciosamente, sin ningún error visible. Este chequeo existe
para convertir ese silencio en un error ruidoso.

**Arreglo:** reconstruí el índice con el mismo modelo que usa el gateway (`docker compose up` —
el `indexer` corre de nuevo si cambió la config).

**Lección:** un modelo mal emparejado es peor que un error: responde *algo*, solo que mal. Mejor
romper fuerte y temprano que degradar en silencio.

---

## 4. El golden set está vacío

**Provocar:**
```bash
cd app && mv eval/golden.jsonl /tmp/golden.bak && echo -n > eval/golden.jsonl
docker compose run --rm evaluator python eval/run_eval.py
```

**Qué ves:**
```
### ❌ REJECTED

_eval/golden.jsonl has no questions: add at least 2-3 per document_
```
y el proceso termina con código de salida 1.

**Dónde mirar:** [`app/eval/run_eval.py`](../../app/eval/run_eval.py), función `examine()`.

**Causa:** sin preguntas no hay nada que pruebe que el bot responde bien — rechazar es la puerta de
calidad haciendo su trabajo, no un bug.

**Arreglo:** `mv /tmp/golden.bak eval/golden.jsonl`. En la vida real: escribí 2-3 preguntas por
documento antes de confiar en una respuesta (ver [Lab 05](labs/05-evaluation.md)).

**Lección:** un conjunto de evaluación vacío no es "sin opinión" — acá es un rechazo explícito.

---

## 5. SeaweedFS: "the specified bucket does not exist"

**Provocar:** `docker compose --profile dvc up -d seaweedfs` (SeaweedFS limpio, sin bucket) y
después `dvc push` directo, sin pasar por `app/dvc-setup.sh`.

**Qué ves:**
```
ERROR: unexpected error - The specified bucket does not exist: An error occurred (NoSuchBucket)
when calling the ListObjectsV2 operation: The specified bucket does not exist
```

**Dónde mirar:** [`app/dvc-setup.sh`](../../app/dvc-setup.sh) — el paso que corre
`s3.bucket.create -name knowledge` contra `weed shell`.

**Causa:** a diferencia de otros S3 self-hosted, SeaweedFS **no crea el bucket solo** en el primer
`PutObject`. Hay que crearlo a mano (o con un script) antes de poder escribir.

**Arreglo:** corré `make dvc-setup` — es idempotente, podés correrlo las veces que quieras.

**Lección:** "S3-compatible" no significa "idéntico en cada detalle a S3" — la autocreación de
buckets es justamente uno de los puntos donde difiere. Vale la pena probar el camino completo
(crear → subir → bajar) antes de asumirlo, en vez de copiar instrucciones de otro proyecto.

---

## 6. Rate limit: `429` con `Retry-After`

**Provocar:**
```bash
for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/config -H "x-api-key: tu-clave"; done
```

**Qué ves:** los primeros `RATE_LIMIT_PER_MINUTE` (30 por default) dan `200`; el siguiente da `429`
con la cabecera `retry-after: 60`.

**Dónde mirar:** [`gateway/auth.py`](../../app/gateway/auth.py), `rate_limit()` — una ventana
deslizante por clave de API, en memoria (sin Redis: para una sola réplica, alcanza).

**Causa:** el límite es **por clave, no por IP**. Una petición inválida (por ejemplo, una pregunta
vacía que da `422`) también cuenta — es una decisión a propósito, para que no sea gratis mandar
basura a mayor velocidad que preguntas reales.

**Arreglo:** esperá el `Retry-After`, o usá otra clave (`API_KEYS` acepta varias, separadas por coma).

**Lección:** un límite "por IP" es fácil de esquivar (varias IPs). Por clave es más difícil de
esquivar y más fácil de auditar (sabés exactamente quién pidió qué).

---

## 7. `ORIGIN_VERIFY_SECRET`: por default, no hace nada

**Provocar:** mandá una petición sin ninguna cabecera especial, con el stack recién levantado
(`config.env` sin tocar).

**Qué ves:** funciona normal — no hace falta ninguna cabecera `x-origin-verify`.

**Dónde mirar:** [`gateway/auth.py`](../../app/gateway/auth.py), `verify_origin()`: `if ORIGIN_VERIFY_SECRET:`.

**Causa:** en este setup 100% local no hay ningún proxy/CDN delante que inyecte una cabecera
secreta — exigirla igual rompería el caso de uso normal. La comprobación se desactiva sola cuando
la variable está vacía (que es el default).

**Arreglo:** no hace falta ninguno — es el comportamiento esperado. Si alguna vez ponés un túnel o
proxy delante, poné `ORIGIN_VERIFY_SECRET` a lo que ese proxy inyecte, y ahí sí empieza a exigirse.

**Lección:** una variable de seguridad "opcional por default, estricta si la configurás" es más
segura en la práctica que una que *siempre* exige algo — porque la segunda tienta a poner un valor
fijo y trivial en todos lados "para que ande", que es peor que no tener nada.

---

¿Encontraste una falla real que no está acá? Agregala con el mismo formato — es la forma más
honesta de documentar un sistema: mostrando cómo se rompe, no solo cómo se supone que funciona.

---

**[English](../break.md)**
