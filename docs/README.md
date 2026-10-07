# Verity documentation

Full guide, in suggested reading order. If you came from the root README, you probably already saw
[Install](install.md) and [The stack](stack.md) — the rest is for when you want the *why* behind
each piece, not just the *how*.

| Document | What it's for |
| --- | --- |
| [Install](install.md) | Get the bot running on your machine, step by step, from scratch |
| [The stack](stack.md) | What each piece does (gateway, Ollama, DVC, SeaweedFS...) and why that one, not another |
| [Architecture](architecture.md) | The full diagram, explained box by box and arrow by arrow |
| [Break the Platform](break.md) | Failures provoked on purpose: what you see, where to look, why it happens |
| [References](references.md) | Official docs for every technology used, in case you want to go deeper |

## 🧪 Labs

Each one takes a real decision from the project and explains it with the code right next to it —
these aren't generic tutorials, they're this repo.

| # | Lab | You learn |
| --- | --- | --- |
| 01 | [RAG](labs/01-rag.md) | Section-based chunking, embeddings, similarity search, the confidence threshold |
| 02 | [Guardrails](labs/02-guardrails.md) | Semantic routing (greeting vs. real question) without an extra model |
| 03 | [Docker](labs/03-docker.md) | Services, profiles, why `knowledge/` gets baked into the image |
| 04 | [DVC + SeaweedFS](labs/04-dvc-seaweedfs.md) | Versioning documents without AWS: the S3 remote runs right next to it |
| 05 | [Evaluation](labs/05-evaluation.md) | The golden set, the quality gate, `prompt_hash` and `release` |
| 06 | [GitHub Actions / CI](labs/06-github-actions-ci.md) | What every PR checks, and why there's no deploy pipeline |

All the code referenced exists in the repo exactly as shown — if anything doesn't match what you see
in your checkout, the code is the source of truth, not this document.

---

**[Español](../es/README.md)**
