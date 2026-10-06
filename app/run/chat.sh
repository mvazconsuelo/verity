#!/usr/bin/env bash
# Interactive chat with the bot once it's up (with "make local" or "docker compose up" in app/).
# Not part of the pipeline or the exam: just for asking it one-off questions by hand, without
# writing curl every time.
#
#   app/run/chat.sh
#
# If the gateway asks for an API key (it wasn't started with AUTH_DISABLED=true), pass it like this:
#   API_KEY=your-key app/run/chat.sh
set -euo pipefail

PORT="${GATEWAY_PORT:-8000}"
URL="http://localhost:${PORT}"

if ! curl -sf "$URL/health" > /dev/null; then
  echo "No gateway running at $URL."
  echo "Bring it up first: make local (or cd app && docker compose up -d)."
  exit 1
fi

echo "Chat with the bot ($URL). Blank Enter or Ctrl+D to exit."
echo

while true; do
  printf "You: "
  IFS= read -r question || { echo; break; }
  [ -z "$question" ] && break

  headers=(-H "Content-Type: application/json")
  [ -n "${API_KEY:-}" ] && headers+=(-H "x-api-key: ${API_KEY}")

  body="$(python3 -c 'import json, sys; print(json.dumps({"question": sys.argv[1]}))' "$question")"
  response="$(curl -s "${headers[@]}" -X POST "$URL/ask" -d "$body")"

  python3 -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
except ValueError:
    print("Bot: (odd response, not JSON)", sys.argv[1])
    sys.exit()
if "answer" in d:
    print("Bot:", d["answer"])
    sources = d.get("sources")
    if sources:
        print("      (source:", ", ".join(sources) + ")")
else:
    print("Error:", d.get("detail", d))
' "$response"
  echo
done

echo "Done."
