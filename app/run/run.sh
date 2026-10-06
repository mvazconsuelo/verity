#!/usr/bin/env bash
# THE way to run the bot: there's no cloud deploy, this is it. Pulls the documents (DVC ← SeaweedFS, if
# configured — see app/dvc-setup.sh), validates them, brings up the bot with Docker Compose (Ollama
# runs on your own CPU) and either examines the golden set against it or lets you look at the index
# or chat with it by hand. Leaves the stack up when it's done.
#
#   app/run/run.sh
#
# Documents: ALWAYS the ones in app/knowledge/ (the official folder). If you haven't run
# "make dvc-setup" / "make dvc-pull" yet, whatever is already on disk is used as-is — this script
# doesn't require DVC, it just uses it when it's there.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -d .dvc ]; then
  echo "── Pulling documents (DVC ← SeaweedFS) ──"
  (cd app && uv run --group dvc dvc pull) || echo "dvc pull failed or has nothing new; continuing with what's on disk."
  echo
fi

[ -d app/knowledge ] || { echo "app/knowledge/ doesn't exist. Create it and put your documents there."; exit 1; }
if [ -z "$(find app/knowledge -type f -not -name .gitkeep)" ]; then
  echo "app/knowledge/ is empty. Add at least one document before examining."
  exit 1
fi

# select is bash's own builtin (no Docker, no external binary): prints the numbered list and waits
# for you to type a number. Nothing to install, nothing that can fail over TTY/Docker.
PS3="Number: "
echo "What do you want to do?"
select action in "Examine (run the golden set against the bot)" "View the index (which documents and chunks got indexed)" "Chat with the bot (one-off questions, by hand)" "Exit"; do
  [ -n "${action:-}" ] && break
  echo "Pick a number from the list."
done
[ "$action" = "Exit" ] && { echo "Nothing to do, done."; exit 0; }

echo
echo "── 1/3 Validating the documents ──"
docker run --rm -v "$ROOT/app":/work -w /work python:3.11-slim python3 -m rag.validate_knowledge knowledge

# Without API_KEYS the gateway won't start (it refuses on purpose). No need to generate a key
# locally: AUTH_DISABLED exists just for this ("testing only", see app/gateway/auth.py).
export AUTH_DISABLED=true

# The commit is computed here (with the full repo in front): the exam's container only sees app/,
# not the root .git. See git_info() in app/eval/run_eval.py.
export GIT_COMMIT GIT_DIRTY
GIT_COMMIT="$(git rev-parse --short HEAD 2> /dev/null || true)"
GIT_DIRTY=""
[ -n "$(git status --porcelain --untracked-files=no 2> /dev/null || true)" ] && GIT_DIRTY="true"

echo
echo "── 2/3 Building and starting the stack (the first time downloads the models) ──"
cd app
docker compose --profile evaluator build
docker compose up -d
ready=false
for _ in $(seq 1 60); do
  curl -sf http://localhost:"${GATEWAY_PORT:-8000}"/health > /dev/null && { ready=true; break; }
  sleep 5
done
if ! $ready; then
  echo "The gateway didn't start in time. Last logs:"
  docker compose logs --tail 100 gateway
  exit 1
fi

echo
if [ "$action" = "View the index (which documents and chunks got indexed)" ]; then
  echo "── 3/3 Index (index.db, the one the indexer builds and the gateway reads) ──"
  # No manual SQL, no touching the index: read-only, with the project's own code
  # (rag/index_store.py). --no-deps because everything is already up from the previous step; -T
  # because no terminal is needed, the script is piped in through stdin.
  docker compose run --rm --no-deps -T gateway python3 <<'PY'
from pathlib import Path
from rag.index_store import open_index, read_meta

con = open_index(Path("/srv/artifacts/index"))
meta = read_meta(con)
print(f"Embedding model: {meta.get('embedding_model')}")
print(f"Documents: {meta.get('n_documents')} · Chunks: {meta.get('n_chunks')} · Vector dimension: {meta.get('dimension')}")

for source, section, text in con.execute("SELECT source, section, text FROM chunks ORDER BY source, section"):
    print(f"\n📄 {source} — {section}")
    for line in text.splitlines():
        print(f"   {line}")

print(f"\n── Semantic routing (gateway/guardrails.py — reference phrases, never a document source) ──")
for category, phrase in con.execute("SELECT category, phrase FROM phrases ORDER BY category, phrase"):
    print(f"🧭 [{category}] {phrase}")
PY
  result=0
elif [ "$action" = "Chat with the bot (one-off questions, by hand)" ]; then
  echo "── 3/3 Chat (blank Enter or Ctrl+D to exit) ──"
  "$ROOT/app/run/chat.sh"
  result=0
else
  echo "── 3/3 Exam (against the gateway that just came up on your machine) ──"
  set +e
  docker compose run --rm evaluator python eval/run_eval.py
  result=$?
  set -e
  echo
  echo "Full report in app/eval/report/eval-result.json and app/eval/report/eval-result.md."
fi

echo
echo "The stack is up: http://localhost:${GATEWAY_PORT:-8000}"
if [ -n "${PUBLIC_IP:-}" ]; then
  echo "Public link (nip.io, no DNS setup needed): http://${PUBLIC_IP}.nip.io:${GATEWAY_PORT:-8000}"
  echo "(only reachable if you forwarded that port on your router to this machine)"
fi
echo "To stop it:  cd app && docker compose --profile evaluator down"
exit "$result"
