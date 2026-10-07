# Documentación de Verity

Guía completa, en orden sugerido de lectura. Si venís del README raíz, probablemente ya viste
[Instalación](install.md) y [El stack](stack.md) — el resto es para cuando quieras entender el
porqué de cada pieza, no solo el cómo.

| Documento | Para qué sirve |
| --- | --- |
| [Instalación](install.md) | Levantar el bot en tu máquina, paso a paso, desde cero |
| [Uso](usage.md) | La referencia de la API (`curl` + `chat.sh`), y qué escribir realmente en `knowledge/` |
| [El stack](stack.md) | Qué hace cada pieza (gateway, Ollama, DVC, SeaweedFS...) y por qué esa y no otra |
| [Arquitectura](architecture.md) | El diagrama completo, explicado caja por caja y flecha por flecha |
| [Break the Platform](break.md) | Fallas provocadas a propósito: qué ves, dónde mirar, por qué pasa |
| [Referencias](references.md) | Documentación oficial de cada tecnología usada, por si querés profundizar |

## 🧪 Labs

Cada uno toma una decisión real del proyecto y la explica con el código de al lado — no son
tutoriales genéricos, son este repo.

| # | Lab | Aprendés |
| --- | --- | --- |
| 01 | [RAG](labs/01-rag.md) | Troceo por secciones, embeddings, búsqueda por similitud, el umbral de confianza |
| 02 | [Guardrails](labs/02-guardrails.md) | Enrutado semántico (saludo vs. pregunta real) sin un modelo extra |
| 03 | [Docker](labs/03-docker.md) | Servicios, perfiles, por qué `knowledge/` se hornea en la imagen |
| 04 | [DVC + SeaweedFS](labs/04-dvc-seaweedfs.md) | Versionar documentos con un remoto S3 self-hosted que corre al lado |
| 05 | [Evaluación](labs/05-evaluation.md) | El golden set, la puerta de calidad, `prompt_hash` y `release` |

Todo el código citado existe en el repo tal cual se muestra — si algo no coincide con lo que ves en
tu checkout, el código manda, no este documento.

---

**[English](../README.md)**
