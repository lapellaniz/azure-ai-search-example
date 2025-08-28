

## Dev Containers (VS Code)

This repo ships a Compose-based dev container that includes **Azure CLI** and **Docker + Compose v2** tools.

**Prereqs**: Docker Desktop (Linux containers) and the VS Code **Dev Containers** extension.

**Use it**:
1. Open the folder in VS Code.
2. Press `F1` → **Dev Containers: Reopen in Container**.
3. First boot will create `.venv`, install deps, and install the package in editable mode.

Inside the container:
```bash
az version
docker version
docker compose version
make test
```
