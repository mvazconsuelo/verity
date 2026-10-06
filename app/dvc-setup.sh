#!/usr/bin/env bash
# One-time setup: brings up SeaweedFS (self-hosted S3-compatible storage, with a built-in web file
# browser), creates an S3 user and a bucket, and points DVC at it as the remote for knowledge/. Only
# needs to run once per machine (its state persists in a Docker volume). Safe to re-run: skips
# whatever is already done.
#
#   app/dvc-setup.sh
#
# After this: "make dvc-push" publishes app/knowledge/ to SeaweedFS, "make dvc-pull" fetches it
# (app/run/run.sh calls dvc pull automatically if .dvc/ exists). Browse what's stored at
# http://localhost:8888/buckets/knowledge/ (web UI, read-only is fine — not meant for production use).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/app"

DVC() { uv run --group dvc dvc "$@"; }

# ── 1/4 DVC itself ────────────────────────────────────────────────────────────
if [ ! -d .dvc ]; then
  echo "── 1/4 dvc init ──"
  DVC init --subdir
else
  echo "── 1/4 DVC already initialized, skipping ──"
fi

# ── 2/4 Start SeaweedFS ─────────────────────────────────────────────────────────
echo "── 2/4 Starting SeaweedFS ──"
docker compose --profile dvc up -d seaweedfs

ready=false
for _ in $(seq 1 30); do
  curl -sf "http://localhost:${SEAWEEDFS_UI_PORT:-8888}/" > /dev/null 2>&1 && { ready=true; break; }
  sleep 2
done
$ready || { echo "SeaweedFS didn't start in time."; docker compose logs --tail 60 seaweedfs; exit 1; }

# ── 3/4 + 4/4 Access key, bucket, and the DVC remote itself ───────────────────
if ! DVC remote list | grep -q '^seaweed'; then
  echo "── 3/4 Creating the S3 user and the bucket ──"
  ACCESS_KEY="SW$(openssl rand -hex 10)"
  SECRET_KEY="$(openssl rand -hex 32)"
  echo "s3.configure -user=dvc -access_key=${ACCESS_KEY} -secret_key=${SECRET_KEY} -actions=Read,Write,List,Tagging -apply" \
    | docker compose exec -T seaweedfs weed shell > /dev/null
  echo "s3.bucket.create -name knowledge" \
    | docker compose exec -T seaweedfs weed shell > /dev/null

  echo "── 4/4 Configuring the DVC remote ──"
  DVC remote add -d seaweed s3://knowledge
  DVC remote modify seaweed endpointurl "http://localhost:${SEAWEEDFS_S3_PORT:-8333}"
  DVC remote modify seaweed region us-east-1   # SeaweedFS ignores the value, but the S3 client requires one
  DVC remote modify --local seaweed access_key_id "$ACCESS_KEY"
  DVC remote modify --local seaweed secret_access_key "$SECRET_KEY"
else
  echo "── 3/4, 4/4 Already configured, skipping (the credentials are in .dvc/config.local) ──"
fi

echo
echo "Done. The credentials (.dvc/config.local) are local-only — never committed."
echo "Browse what's stored: http://localhost:${SEAWEEDFS_UI_PORT:-8888}/buckets/knowledge/"
echo "Next: dvc add knowledge && make dvc-push   (or just: make dvc-push)"
