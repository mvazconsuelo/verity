# Lab 03 — Docker

**Aprendés:** por qué hay un solo `docker-compose.yml` sin variantes de entorno, qué son los
perfiles, y por qué `knowledge/` termina *dentro* de la imagen en vez de montada como volumen.

## Los servicios, y por qué cada uno existe

Mirá [`app/docker-compose.yml`](../../../app/docker-compose.yml) con esto al lado:

| Servicio | Arranca con `up`? | Para qué |
| --- | --- | --- |
| `ollama` | Sí | Sirve el chat y los embeddings. `healthcheck` espera a que **todos** los modelos de `MODELS` estén descargados antes de reportarse sano |
| `indexer` | Sí (y termina) | Construye `index.db` una vez; el `gateway` no atiende hasta que termina (`depends_on: service_completed_successfully`) |
| `gateway` | Sí | La única puerta hacia afuera — todo lo demás escucha solo en `127.0.0.1` |
| `evaluator` | **No** (`profiles: ["evaluator"]`) | Corre el golden set a mano, contra un gateway ya levantado |
| `seaweedfs` | **No** (`profiles: ["dvc"]`) | Remoto S3 de DVC — no tiene nada que ver con responder preguntas |

Un perfil es, literalmente, "este servicio no arranca salvo que se lo pidas". `docker compose up`
(sin flags) levanta solo lo que no tiene perfil. `docker compose --profile evaluator run evaluator
...` o `--profile dvc up -d seaweedfs` son opt-in explícitos.

**Probalo vos:**
```bash
cd app && docker compose up -d && docker compose ps
# vas a ver ollama, indexer (Exited, 0) y gateway — nada de evaluator ni seaweedfs
```

## `image:` + `build:` juntos, a propósito

`ollama` y `gateway` declaran **las dos claves a la vez**. `docker compose build` construye la
imagen local y la etiqueta con el nombre de `image:`; `docker compose up` (sin `build` antes) la usa
tal cual quedó, o la descarga si el tag existe en un registro. Esto deja el mismo archivo servir
tanto para desarrollo local (siempre se construye) como para, el día de mañana, publicar esa misma
imagen a un registro (GHCR) y que alguien la use con solo `docker compose pull`.

## Por qué `seaweedfs` NO tiene Dockerfile propio

A diferencia de `ollama` (que sí tiene uno — ver
[`app/docker/README.md`](../../../app/docker/README.md)), `seaweedfs` usa la imagen pública tal
cual, sin ningún agregado. Un Dockerfile de una sola línea (`FROM imagen:tag`) no cumpliría ninguna
función — la convención del proyecto es: Dockerfile solo para lo que necesita código propio o un
entrypoint custom.

## `knowledge/` dentro de la imagen, no montada

```dockerfile
COPY knowledge ./knowledge
```

Esto es la pieza más importante para entender el proyecto entero: **la imagen es la unidad de
versión**. El mismo tag siempre responde con el mismo código, el mismo prompt y los mismos
documentos — no hay forma de que un contenedor viejo "se actualice solo" si editás un archivo en el
host. Ver esto fallar en vivo: [Break the Platform #2](../break.md#2-cambi%C3%A9-un-documento-y-el-bot-sigue-respondiendo-lo-viejo).

**Probalo vos:**
```bash
cd app && docker compose exec gateway ls /srv/knowledge
# los mismos archivos que ya estaban en la imagen cuando se construyó — no los que tengas ahora en el disco
```

---

**[English](../../labs/03-docker.md)**
