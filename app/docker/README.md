# What goes here (and what doesn't)

This folder has one Dockerfile per service, but **only for the ones that need it**: either their
own code (`gateway/`, `evaluator/`) or a public image that needs something added to it (`ollama/`,
which adds `entrypoint.sh` to download the models at startup).

A service that uses a public image **with nothing added of its own** doesn't get a folder here —
it's declared directly in `../docker-compose.yml` with `image: <image>:<pinned-version>`, no
Dockerfile in between. Today the only case is **`seaweedfs`** (DVC's S3 storage): check its
definition in the compose file, don't look for `docker/seaweedfs/`.

If `seaweedfs` (or any other service) ever needs something of its own (a startup script, a
configuration file baked into the image), that's when it gets its own folder here, same as
`ollama`.
