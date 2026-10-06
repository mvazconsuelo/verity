# Lab 06 — GitHub Actions / CI

**Aprendés:** qué valida un PR acá, y por qué —a propósito— no hay ningún paso de despliegue.

## Lo que hace `ci.yml`

[`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml), dos jobs, en cada Pull Request:

**`validate`:**
- `docker compose config` — el compose es válido, solo y combinado con `compose.ci.yml`
- `gitleaks` — ningún secreto en el historial completo de git
- `hadolint` — cada Dockerfile
- `actionlint` — los propios workflows y acciones
- `shellcheck -x -P SCRIPTDIR` — cada script bash del repo

**`test`:**
- `uv lock --check` — que `uv.lock` corresponda a `pyproject.toml` (si editaste dependencias y te
  olvidaste de regenerar el lock, esto lo atrapa antes que un `uv sync` roto en otro lado)
- `pytest` — los tests del gateway y del troceador de documentos

**Probalo vos:**
```bash
cd app && uv run --group test --python 3.11 pytest -q
shellcheck -x -P SCRIPTDIR run/*.sh ../dvc-setup.sh
```

## Lo que NO hace, a propósito

No hay ningún job de `deploy`. No es que falte — es que no hay a dónde desplegar desde una pipeline
en la nube: el bot corre en tu máquina, y GitHub Actions no tiene forma de llegar ahí (ni debería:
sería una superficie de ataque rara para ganar poco). Por eso el diagrama de
[Arquitectura](../architecture.md) dibuja la caja de CI aislada, sin ninguna flecha hacia el resto.

Tampoco corre el examen con el golden set real: necesita documentos reales (vía DVC/SeaweedFS, que
vive solo en tu máquina) y Ollama con los modelos descargados — ninguno de los dos existe en el
runner de GitHub. El examen real es manual: `app/run/run.sh` (o `make local`).

## El historial: por qué cambió

Este proyecto tuvo, en un momento, una pipeline completa: `release.yml` (build + examen + publicar
a ECR + desplegar vía SSM a una instancia EC2), `rollback.yml`, roles de OIDC contra AWS, Terraform
para la infraestructura. Se sacó todo enterito cuando el proyecto pasó a correr 100% local — no
porque esa arquitectura estuviera mal, sino porque mantenerla sin un despliegue real que la
justificara era la clase de complejidad que vale la pena cargarse solo cuando hay un problema real
detrás. El principio que guió ese recorte (y sigue guiando qué se agrega de acá en más): **resolvé
el problema de hoy con la arquitectura mínima que lo resuelve** — no la que podría hacer falta
"por si acaso".

## Si algún día vuelve a hacer falta una pipeline de despliegue

El patrón para decidirlo no cambia: ¿hay un entorno real al que desplegar? ¿quién lo necesita, y
para qué? Si la respuesta es concreta, se construye entonces — contra ese caso real, no
especulativamente. Ver [Break the Platform](../break.md) para el estilo de pensar "qué pasa si esto
falla" antes de agregar una pieza nueva.
