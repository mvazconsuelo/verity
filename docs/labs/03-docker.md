# Lab 03 — Docker

**You learn:** why there's a single `docker-compose.yml` with no environment variants, what
profiles are, and why `knowledge/` ends up *inside* the image instead of mounted as a volume.

## The services, and why each one exists

Look at [`app/docker-compose.yml`](../../app/docker-compose.yml) alongside this:

| Service | Starts with `up`? | What for |
| --- | --- | --- |
| `ollama` | Yes | Serves chat and embeddings. Its `healthcheck` waits until **every** model in `MODELS` is downloaded before reporting healthy |
| `indexer` | Yes (and exits) | Builds `index.db` once; `gateway` doesn't serve until it finishes (`depends_on: service_completed_successfully`) |
| `gateway` | Yes | The only door to the outside — everything else listens only on `127.0.0.1` |
| `evaluator` | **No** (`profiles: ["evaluator"]`) | Runs the golden set by hand, against a gateway that's already up |
| `seaweedfs` | **No** (`profiles: ["dvc"]`) | DVC's S3 remote — has nothing to do with answering questions |

A profile is, literally, "this service doesn't start unless you ask for it." `docker compose up`
(no flags) brings up only what has no profile. `docker compose --profile evaluator run evaluator
...` or `--profile dvc up -d seaweedfs` are explicit opt-ins.

**Try it yourself:**
```bash
cd app && docker compose up -d && docker compose ps
# you'll see ollama, indexer (Exited, 0) and gateway — nothing from evaluator or seaweedfs
```

## `image:` + `build:` together, on purpose

`ollama` and `gateway` declare **both keys at once**. `docker compose build` builds the local image
and tags it with the `image:` name; `docker compose up` (without a prior `build`) uses it as-is, or
pulls it if the tag exists in a registry. This lets the same file serve both local development
(always builds) and, down the line, publishing that same image to a registry (GHCR) so someone can
use it with just `docker compose pull`.

## Why `seaweedfs` has NO Dockerfile of its own

Unlike `ollama` (which does have one — see
[`app/docker/README.md`](../../app/docker/README.md)), `seaweedfs` uses the public image exactly as
it is, nothing added. A one-line Dockerfile (`FROM image:tag`) wouldn't serve any purpose — the
project's convention is: a Dockerfile only for what needs its own code or a custom entrypoint.

## `knowledge/` inside the image, not mounted

```dockerfile
COPY knowledge ./knowledge
```

This is the single most important piece for understanding the whole project: **the image is the
unit of version**. The same tag always answers with the same code, the same prompt and the same
documents — there's no way for a running container to "update itself" if you edit a file on the
host. See this fail live: [Break the Platform #2](../break.md#2-i-edited-a-document-and-the-bot-keeps-answering-the-old-one).

**Try it yourself:**
```bash
cd app && docker compose exec gateway ls /srv/knowledge
# the same files that were already in the image when it was built — not whatever's on disk right now
```

---

**[Español](../es/labs/03-docker.md)**
