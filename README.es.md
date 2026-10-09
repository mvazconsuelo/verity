<div align="center">

<img src="docs/images/brand/hero.es.svg" alt="Verity — asistente de atención al cliente que responde solo con tu documentación: redactar, trocear, embeber, buscar, responder, evaluar, versionar, aprender" width="100%">

<br>

![Python](https://img.shields.io/badge/python-3.11-0B0F14?style=for-the-badge&logo=python&logoColor=22D3EE&labelColor=0B0F14)
![Docker](https://img.shields.io/badge/docker-compose-0B0F14?style=for-the-badge&logo=docker&logoColor=22D3EE&labelColor=0B0F14)
![Ollama](https://img.shields.io/badge/ollama-qwen2.5_%2B_bge--m3-0B0F14?style=for-the-badge&logo=ollama&logoColor=22D3EE&labelColor=0B0F14)
![DVC](https://img.shields.io/badge/datos-DVC_%2B_SeaweedFS-0B0F14?style=for-the-badge&logo=dvc&logoColor=22D3EE&labelColor=0B0F14)

**[Instalación](docs/es/install.md)** · **[Uso](docs/es/usage.md)** · **[El stack](docs/es/stack.md)** · **[Arquitectura](docs/es/architecture.md)** · **[Referencias](docs/es/references.md)** · **[Toda la documentación](docs/es/README.md)**

[English](README.md) · **Español**

</div>

## ⚡ La idea

**Verity es un bot de atención al cliente que responde solo con tu propia documentación.** RAG con
umbral de confianza, guardrails semánticos, prompts versionados, evaluación con golden set y puerta
de calidad, y versionado de datos — **todo corriendo en tu propia máquina, sin nube, sin tarjeta de
crédito, sin cuentas que crear.**

> [!NOTE]
> Cada afirmación de este README apunta al archivo que la respalda.

## 🧱 Stack

**Aplicación**<br>
<img alt="Python" src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white">&nbsp;<img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">&nbsp;<img alt="Ollama" src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white">&nbsp;<img alt="sqlite-vec" src="https://img.shields.io/badge/sqlite--vec-003B57?style=for-the-badge&logo=sqlite&logoColor=white">

**Datos**<br>
<img alt="DVC" src="https://img.shields.io/badge/DVC-13ADC7?style=for-the-badge&logo=dvc&logoColor=white">&nbsp;<img alt="SeaweedFS" src="https://img.shields.io/badge/SeaweedFS-2E8B57?style=for-the-badge">

**Plataforma**<br>
<img alt="Docker" src="https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white">&nbsp;<img alt="uv" src="https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge">

Por qué cada una y no otra: [docs/es/stack.md](docs/es/stack.md).

## 🏗 Arquitectura

![Arquitectura de Verity: usuario, gateway, Ollama, indexer, índice, evaluador manual, y DVC con SeaweedFS versionando los documentos fuera del camino de las peticiones](docs/images/architecture.es.svg)

No hay pipeline de despliegue, porque no hay nube a la que desplegar — `docker compose up`, en tu
máquina, **es** el despliegue. Detalle caja por caja: [docs/es/architecture.md](docs/es/architecture.md).

## 🚀 Empezar

**Necesitás:** Docker (con Compose v2) y, si vas a usar DVC, [uv](https://docs.astral.sh/uv/). Nada
de nube, nada de cuentas.

```bash
git clone <tu-fork-o-el-repo> verity && cd verity
make local    # valida, construye, levanta — y te deja elegir qué hacer
```

<a href="docs/es/install.md"><img src="https://img.shields.io/badge/Guía_de_instalación-→-22D3EE?style=for-the-badge&labelColor=0B0F14"></a>
<a href="docs/es/README.md"><img src="https://img.shields.io/badge/Toda_la_documentación-→-1F2A37?style=for-the-badge&labelColor=0B0F14"></a>

<details>
<summary><b>Estructura del repositorio</b></summary>

```text
app/
├── gateway/        La API (FastAPI): auth, prompt, retrieval, guardrails, endpoints
├── rag/            Troceo de documentos + construcción e índice vectorial (sqlite-vec)
├── eval/           El examen: golden.jsonl, run_eval.py, el reporte
├── prompts/        system.md + template.md — versionados en git, con hash en cada respuesta
├── knowledge/       Tus documentos reales. Versionados con DVC (ver dvc-setup.sh)
├── docker/          Un Dockerfile por servicio que lo necesita (ver docker/README.md)
├── run/            run.sh (el único modo de correr el bot) · chat.sh
├── dvc-setup.sh     Bootstrap de un solo uso: SeaweedFS como remoto de DVC
└── docker-compose.yml

docs/
├── es/              Toda la documentación en español
├── (sin sufijo)     La misma documentación en inglés (default)
└── images/          Diagramas y el banner de arriba

config.env           La configuración del bot: el único archivo que editás
```

</details>

---

<div align="center">

**[Toda la documentación →](docs/es/README.md)**

</div>
