# The stack

Every piece is there because it solves a concrete problem in this project — not because it's
trendy. Where a more "obvious" alternative got ruled out, the reason is spelled out.

## Application

| Piece | What for | Why this one and not another |
| --- | --- | --- |
| **FastAPI** | The bot's API (`gateway/`) | Native async (matters: every `/ask` waits on Ollama), input validation via Pydantic for free |
| **Ollama** | Serves the chat model and the embedding model, locally | No dependency on an external model API — no per-token cost, and your documents never leave your machine |
| **qwen2.5:1.5b** | Chat model | Small on purpose: runs on CPU, no GPU, on a Mac or a small instance. The trade-off is quality — see [Lab 05](labs/05-evaluation.md) for how that's measured |
| **bge-m3** | Embedding model | Multilingual, solid MTEB performance for its size, runs on the same Ollama as chat (one service, not two) |
| **sqlite-vec** | Vector index (`index.db`) | A single file, no separate server — for the few thousand chunks of a small business, more than enough. See [Lab 01](labs/01-rag.md) |

## Data

| Piece | What for | Why this one and not another |
| --- | --- | --- |
| **DVC** | Versions `app/knowledge/` beyond what git handles well | git versions text very well, but doesn't give you "push/pull a full snapshot against a separate storage, without bloating the repo" — useful once the documents stop being just 4 small `.md` files |
| **SeaweedFS** | DVC's S3 remote, self-hosted | Single official image (no third-party mirrors, no login) and ships a web file browser out of the box. MinIO (lost public image distribution in 2025) and Garage (no web UI) were evaluated first — see [Lab 04](labs/04-dvc-seaweedfs.md) |

## Platform

| Piece | What for | Why this one and not another |
| --- | --- | --- |
| **Docker Compose** | Orchestrates the whole stack on a single machine | No Kubernetes to justify: everything runs on one node, yours. See [Lab 03](labs/03-docker.md) |
| **GitHub Actions** | CI — validates every PR | Lint + pytest only, no deploy: there's no cloud to deploy to. See [Lab 06](labs/06-github-actions-ci.md) |

## Security

| Piece | What for |
| --- | --- |
| **API key + rate limit** | `gateway/auth.py` — closes the gateway entirely if `API_KEYS` is missing, no way to "forget" to set it |
| **`ORIGIN_VERIFY_SECRET`** (optional) | If you ever put a proxy/tunnel in front, this header stops anyone from talking to the gateway by going around it |
| **Semantic guardrails** | `gateway/guardrails.py` — see [Lab 02](labs/02-guardrails.md) |

## What's explicitly NOT there

- **Cloud**: nothing runs outside your machine. Not because it couldn't, but because adding it
  without a real need behind it is exactly the kind of complexity this project has been cutting on
  purpose (see the decision history in the commits and the root README).
- **Kubernetes, service mesh, autoscaling**: for a single bot on a single machine, they'd solve a
  problem that doesn't exist here.
- **Fine-tuning**: the model is used as-is; everything business-specific lives in the documents
  (RAG) and the prompt, not in retrained weights.

---

**[Español](../es/stack.md)**
