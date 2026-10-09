# El stack

Cada pieza está porque resuelve un problema concreto de este proyecto — no porque sea la opción de
moda. Donde se descartó una alternativa más "obvia", se explica por qué.

## Aplicación

| Pieza | Para qué | Por qué esta y no otra |
| --- | --- | --- |
| **FastAPI** | La API del bot (`gateway/`) | Async nativo (importa: cada `/ask` espera a Ollama), validación de entrada con Pydantic gratis |
| **Ollama** | Sirve el modelo de chat y el de embeddings, local | Sin depender de una API externa de modelos — ni costo por token, ni tus documentos saliendo de tu máquina |
| **qwen2.5:1.5b** | Modelo de chat | Chico a propósito: corre en CPU, sin GPU, en un Mac o Linux. El trade-off es calidad |
| **bge-m3** | Modelo de embeddings | Multilingüe, buen desempeño en MTEB para su tamaño, corre en el mismo Ollama que el chat (un solo servicio, no dos) |
| **sqlite-vec** | Índice vectorial (`index.db`) | Un archivo, sin servidor aparte — para los pocos miles de chunks de un negocio chico, de sobra |

## Datos

| Pieza | Para qué | Por qué esta y no otra |
| --- | --- | --- |
| **DVC** | Versiona `app/knowledge/` más allá de git | git versiona bien texto, pero no te da "subir/bajar un snapshot completo" contra un storage aparte — útil si los documentos crecen o dejan de ser solo texto |
| **SeaweedFS** | El remoto S3 de DVC, self-hosted | Imagen oficial, sin login, trae interfaz web de archivos de fábrica |

## Plataforma

| Pieza | Para qué | Por qué esta y no otra |
| --- | --- | --- |
| **Docker Compose** | Orquesta todo el stack en una sola máquina | No hay Kubernetes que justificar: todo corre en un solo nodo, el tuyo |

## Seguridad

| Pieza | Para qué |
| --- | --- |
| **Clave de API + rate limit** | `gateway/auth.py` — cierra el gateway por completo si no hay `API_KEYS`, no hay forma de "olvidarse" de ponerlas |
| **`ORIGIN_VERIFY_SECRET`** (opcional) | Si algún día ponés un proxy/túnel delante, esta cabecera evita que alguien le hable al gateway salteándolo |
| **Guardrails semánticos** | `gateway/guardrails.py` |

## Lo que explícitamente NO hay

- **Nube**: nada corre fuera de tu máquina. No porque no se pueda, sino porque agregarla sin un
  caso real que lo pida es la clase de complejidad que este proyecto viene recortando a propósito
  (ver el historial de decisiones en los commits y en el README raíz).
- **Kubernetes, service mesh, autoescalado**: para un solo bot en una sola máquina, resolverían un
  problema que no existe acá.
- **Fine-tuning**: el modelo se usa tal cual viene; todo el comportamiento específico del negocio
  vive en los documentos (RAG) y el prompt, no en pesos reentrenados.

---

**[English](../stack.md)**
