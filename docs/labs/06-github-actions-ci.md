# Lab 06 — GitHub Actions / CI

**You learn:** what a PR actually validates here, and why — on purpose — there's no deploy step.

## What `ci.yml` does

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), two jobs, on every Pull Request:

**`validate`:**
- `docker compose config` — the compose file is valid, alone and combined with `compose.ci.yml`
- `gitleaks` — no secrets anywhere in the full git history
- `hadolint` — every Dockerfile
- `actionlint` — the workflows and actions themselves
- `shellcheck -x -P SCRIPTDIR` — every bash script in the repo

**`test`:**
- `uv lock --check` — that `uv.lock` matches `pyproject.toml` (if you edited a dependency and
  forgot to regenerate the lock, this catches it before a broken `uv sync` somewhere else)
- `pytest` — the gateway's tests and the document chunker's tests

**Try it yourself:**
```bash
cd app && uv run --group test --python 3.11 pytest -q
shellcheck -x -P SCRIPTDIR run/*.sh ../dvc-setup.sh
```

## What it does NOT do, on purpose

There's no `deploy` job at all. It's not missing — there's nowhere to deploy to from a cloud
pipeline: the bot runs on your machine, and GitHub Actions has no way to reach it (and shouldn't:
it'd be an odd attack surface for little gain). That's why the [Architecture](../architecture.md)
diagram draws the CI box isolated, with no arrow toward anything else.

It also doesn't run the exam with the real golden set: that needs real documents (via DVC/SeaweedFS,
which only lives on your machine) and Ollama with the models downloaded — neither exists on
GitHub's runner. The real exam is manual: `app/run/run.sh` (or `make local`).

## The history: why it changed

This project once had a full pipeline: `release.yml` (build + exam + publish to ECR + deploy via SSM
to an EC2 instance), `rollback.yml`, OIDC roles against AWS, Terraform for the infrastructure. All of
it got cut when the project moved to running 100% locally — not because that architecture was wrong,
but because maintaining it without a real deployment to justify it was exactly the kind of
complexity worth dropping only once a real problem calls for it. The principle that guided that cut
(and keeps guiding what gets added from here on): **solve today's problem with the minimum
architecture that solves it** — not the one that might be needed "just in case."

## If a deploy pipeline is ever needed again

The pattern for deciding doesn't change: is there a real environment to deploy to? who needs it, and
for what? If the answer is concrete, build it then — against that real case, not speculatively. See
[Break the Platform](../break.md) for the style of thinking "what happens if this fails" before
adding a new piece.

---

**[Español](../es/labs/06-github-actions-ci.md)**
