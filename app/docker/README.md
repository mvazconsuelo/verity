# Qué va acá (y qué no)

Esta carpeta tiene un Dockerfile por servicio, pero **solo para los que lo necesitan**: código
propio (`gateway/`, `evaluator/`) o una imagen pública a la que hay que agregarle algo
(`ollama/`, que le suma `entrypoint.sh` para descargar los modelos al arrancar).

Un servicio que usa una imagen pública **sin ningún agregado propio** no tiene carpeta acá — se
declara directo en `../docker-compose.yml` con `image: <imagen>:<versión fijada>`, sin Dockerfile de
por medio. Hoy el único caso es **`seaweedfs`** (el almacén S3 de DVC): mirá su definición en el
compose, no busques `docker/seaweedfs/`.

Si en algún momento `seaweedfs` (o cualquier otro) necesita algo propio (un script de arranque, un
archivo de configuración horneado en la imagen), ahí sí pasa a tener su carpeta acá, igual que
`ollama`.
