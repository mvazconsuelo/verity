# Install

## You need

- **Docker** (with Docker Compose v2 — bundled with Docker Desktop).
- **uv** (only if you'll use DVC or run the tests outside Docker) — [install it](https://docs.astral.sh/uv/getting-started/installation/).
- No cloud, no accounts, no credentials. Everything runs on your machine.
- Free RAM: Ollama's models (`qwen2.5:1.5b` + `bge-m3`) weigh ~2.5 GB combined and get downloaded
  the first time you bring the stack up.

## 1. Clone and bring the bot up

```bash
git clone <your-fork-or-the-repo> verity && cd verity
make local
```

`make local` (which calls [`app/run/run.sh`](../app/run/run.sh)) does, in this order:

1. If `.dvc/` is initialized, runs `dvc pull` (if you haven't set up DVC yet, it just uses whatever
   is already in `app/knowledge/` — see step 3).
2. Validates the documents (`rag/validate_knowledge`): format, size, not empty.
3. Builds the images and brings up the stack (`ollama`, `indexer`, `gateway`) — the first time
   downloads the models, takes a few minutes.
4. Lets you choose: run the golden-set exam, view the built index, or chat directly.

At the end, the bot is up at `http://localhost:8000`.

## 2. Try it

```bash
make chat
```

Or straight with `curl`:

```bash
curl -X POST http://localhost:8000/ask \
  -H "content-type: application/json" \
  -H "x-api-key: anything" \
  -d '{"question": "how long does standard shipping take?"}'
```

(If you didn't set `API_KEYS` in your environment, `run.sh` already ran with `AUTH_DISABLED=true` —
see [Lab 02: Guardrails](labs/02-guardrails.md) for why that's safe only locally.)

## 3. (Optional) Version your own documents with DVC

If you're going to edit `app/knowledge/` and want to keep its history beyond git (useful once there
are too many documents, or they're too heavy, to version as plain text):

```bash
make dvc-setup   # once: brings up SeaweedFS and configures it as the remote
# ... edit app/knowledge/ ...
make dvc-push    # publishes your changes
make dvc-pull    # fetches them back (e.g. on another machine)
```

Browse what got saved at `http://localhost:8888/buckets/knowledge/` — a web UI included, nothing
extra to configure. Full detail: [Lab 04](labs/04-dvc-seaweedfs.md).

## 4. Adapt it to your own business

1. Replace the `.md` files in `app/knowledge/` with your real documentation (see
   [Lab 01](labs/01-rag.md) for the format the chunker expects).
2. Write 2-3 questions per document in `app/eval/golden.jsonl` (see [Lab 05](labs/05-evaluation.md)).
3. Adjust `config.env` if needed (`MIN_SIMILARITY`, `TOP_K`, the `EVAL_MIN_*` thresholds).
4. `make local` again and look at the exam report before trusting the bot's answers.

## If something doesn't start

- **The gateway won't start**: check you have `API_KEYS` in your environment, or `AUTH_DISABLED=true`
  (only for trying it out — never in anything exposed). See [Break the Platform](break.md#1-the-gateway-wont-start).
- **The exam takes forever / times out**: the first run downloads the models; run
  `docker compose logs ollama` to see the progress.
- More real scenarios, provoked on purpose: [Break the Platform](break.md).

---

**[Español](../es/install.md)**
