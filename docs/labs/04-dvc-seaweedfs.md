# Lab 04 — DVC + SeaweedFS

**You learn:** how to version data beyond what git handles well, without depending on any cloud
provider — and a couple of real differences between "S3-compatible" and S3 that you only discover
by testing.

## Why DVC, if git already versions `knowledge/`

git versions plain text very well. What it doesn't give you for free is "push/pull a full snapshot
against a separate storage, without bloating the repo" — useful the day the documents stop being 4
small `.md` files (PDFs, images, a real dataset). DVC separates those two things: git stores a
*pointer* (`knowledge.dvc`, a hash), and the actual content lives in a configurable *remote*.

## Why SeaweedFS as the remote, and not MinIO

Three real options got evaluated (not in theory — each one tested with `docker manifest inspect` or
by actually bringing it up):

| Option | Result |
| --- | --- |
| **MinIO** | Its public image can no longer be pulled without login (Docker Hub deleted the repo in 2025, Quay requires an account) |
| **Garage** | Pulls without login, but has no web UI — API only |
| **SeaweedFS** | Pulls without login **and** ships a web file browser out of the box (port 8888) |

## The bootstrap

[`app/dvc-setup.sh`](../../app/dvc-setup.sh), idempotent (running it again skips whatever's already
done):

```bash
docker compose --profile dvc up -d seaweedfs
echo "s3.configure -user=dvc -access_key=... -secret_key=... -actions=Read,Write,List,Tagging -apply" \
  | docker compose exec -T seaweedfs weed shell
echo "s3.bucket.create -name knowledge" \
  | docker compose exec -T seaweedfs weed shell
```

`weed shell` accepts commands over `stdin`, no interactive terminal needed (`-T` on `exec`) — handy
for scripting it without relying on someone typing something by hand.

## A real difference from S3: the bucket doesn't auto-create

Try this yourself:

```bash
cd app && docker compose --profile dvc up -d seaweedfs
uv run --group dvc dvc init --subdir   # if you haven't already
uv run --group dvc dvc remote add -d test s3://does-not-exist --endpointurl http://localhost:8333
uv run --group dvc dvc push
```

You'll get `NoSuchBucket`. On real AWS S3, behavior can differ depending on the client — but **never
assume an "S3-compatible" storage behaves identically in every detail**. That's why `dvc-setup.sh`
creates the bucket explicitly, instead of trusting the first `push` to handle it. Full detail on how
this got discovered: [Break the Platform #5](../break.md#5-seaweedfs-the-specified-bucket-does-not-exist).

## The full flow

```bash
make dvc-setup               # once
# ... edit app/knowledge/ ...
make dvc-push                 # dvc add knowledge && dvc push
make dvc-pull                 # on another machine, or after deleting local knowledge/
```

**Try it yourself — the full round trip:**
```bash
make dvc-push
mv app/knowledge /tmp/backup
make dvc-pull
diff -r app/knowledge /tmp/backup && echo "identical"
```

And look at what got saved, without using any DVC command at all, at
`http://localhost:8888/buckets/knowledge/` — the web UI lists the files exactly as `dvc push`
uploaded them.

## Credentials never get committed

`.dvc/config` (committed) has the remote's URL and region. Access keys go in
`.dvc/config.local` — DVC adds it to `.gitignore` on its own, when you run `dvc remote modify --local`.

---

**[Español](../es/labs/04-dvc-seaweedfs.md)**
