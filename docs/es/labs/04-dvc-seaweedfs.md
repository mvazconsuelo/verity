# Lab 04 — DVC + SeaweedFS

**Aprendés:** cómo versionar datos más allá de lo que git maneja bien, sin depender de ningún
proveedor de nube — y un par de diferencias reales entre "S3-compatible" y S3 que solo se descubren
probando.

## Por qué DVC, si git ya versiona `knowledge/`

git versiona texto plano muy bien. Lo que no te da gratis es "subir/bajar un snapshot completo
contra un storage aparte, sin inflar el repo" — útil el día que los documentos dejan de ser 4
archivos `.md` chicos (PDFs, imágenes, un dataset de verdad). DVC separa esas dos cosas: git guarda
un *puntero* (`knowledge.dvc`, un hash), y el contenido real vive en un *remoto* configurable.

## Por qué SeaweedFS como remoto, y no MinIO

Se evaluaron tres opciones reales (no en teoría — cada una se probó con `docker manifest inspect` o
levantándola de verdad):

| Opción | Resultado |
| --- | --- |
| **MinIO** | Su imagen pública ya no se puede bajar sin login (Docker Hub borró el repo en 2025, Quay exige cuenta) |
| **Garage** | Se baja sin login, pero no tiene interfaz web — solo API |
| **SeaweedFS** | Se baja sin login **y** trae un navegador de archivos web de fábrica (puerto 8888) |

## El bootstrap

[`app/dvc-setup.sh`](../../../app/dvc-setup.sh), idempotente (correrlo de nuevo salta lo que ya
está hecho):

```bash
docker compose --profile dvc up -d seaweedfs
echo "s3.configure -user=dvc -access_key=... -secret_key=... -actions=Read,Write,List,Tagging -apply" \
  | docker compose exec -T seaweedfs weed shell
echo "s3.bucket.create -name knowledge" \
  | docker compose exec -T seaweedfs weed shell
```

`weed shell` acepta comandos por `stdin`, sin necesitar una terminal interactiva (`-T` en `exec`) —
útil para scriptearlo sin depender de que alguien tipee algo a mano.

## Una diferencia real con S3: el bucket no se autocrea

Probá esto vos mismo:

```bash
cd app && docker compose --profile dvc up -d seaweedfs
uv run --group dvc dvc init --subdir   # si no lo hiciste ya
uv run --group dvc dvc remote add -d test s3://no-existe --endpointurl http://localhost:8333
uv run --group dvc dvc push
```

Vas a ver `NoSuchBucket`. En AWS S3 real, según el cliente, a veces el comportamiento difiere —
pero **nunca asumas que un storage "S3-compatible" se comporta idéntico en cada detalle**. Por eso
`dvc-setup.sh` crea el bucket explícitamente, en vez de confiar en que el primer `push` lo resuelva
solo. Detalle completo de cómo se descubrió esto: [Break the Platform #5](../break.md#5-seaweedfs-the-specified-bucket-does-not-exist).

## El flujo completo

```bash
make dvc-setup              # una vez
# ... editás app/knowledge/ ...
make dvc-push                # dvc add knowledge && dvc push
make dvc-pull                # en otra máquina, o después de borrar knowledge/ local
```

**Probalo vos — el round-trip completo:**
```bash
make dvc-push
mv app/knowledge /tmp/backup
make dvc-pull
diff -r app/knowledge /tmp/backup && echo "idéntico"
```

Y mirá lo que quedó guardado, sin usar ningún comando de DVC, en
`http://localhost:8888/buckets/knowledge/` — la interfaz web lista los archivos tal cual los subió
`dvc push`.

## Las credenciales nunca se commitean

`.dvc/config` (committeado) tiene la URL del remoto y la región. Las claves de acceso van en
`.dvc/config.local` — DVC lo agrega a `.gitignore` solo, al correr `dvc remote modify --local`.

---

**[English](../../labs/04-dvc-seaweedfs.md)**
