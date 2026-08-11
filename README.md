# hecha

Portal público de datos legislativos paraguayos. El navegador utiliza únicamente servicios del proyecto; PostgreSQL conserva el último dato público válido y SILpy sólo es consultado por el worker al solicitar una sincronización.

## Inicio rápido

El único requisito de ejecución es Docker con Compose v2. No se necesitan credenciales, claves de SILpy, Node.js ni Python instalados en el equipo anfitrión.

Linux/macOS:

```bash
git clone git@github.com:mateoschreiber/hecha.git
cd hecha
cp .env.example .env
docker compose up --build -d
curl --fail http://localhost:8080/api/v1/health/ready
```

Windows PowerShell:

```powershell
git clone git@github.com:mateoschreiber/hecha.git
Set-Location hecha
Copy-Item .env.example .env
docker compose up --build -d
Invoke-WebRequest http://localhost:8080/api/v1/health/ready | Select-Object -Expand Content
```

Abrí `http://localhost:8080` y usá **Sincronizar datos públicos**. El trabajo queda en cola y se puede seguir desde el portal o en `http://localhost:8080/api/v1/sync/progress`.

## Documentación

- [Arquitectura](docs/architecture.md): límites de red, flujos de lectura y sincronización.
- [Despliegue y operación](docs/deployment.md): guía detallada para Linux, Windows/Docker Desktop y VPS, con actualización, backup, restauración y diagnóstico.
- [Contrato SILpy](docs/silpy-contract.md): fuente, selectores y límites del adaptador público.
- [Decisiones de arquitectura](docs/decisions): stack, tiempo, identificadores y bajas lógicas.

## Calidad

Para desarrollo local con Python 3.13 y `uv`:

```bash
uv run ruff check .
uv run mypy backend apps
uv run pytest
uv run python scripts/check_openapi.py
```

La comprobación mínima en cualquier equipo es:

```bash
docker compose config --quiet
docker compose build
```

Sólo Caddy publica un puerto (`8080`) en la instalación local. API, worker y PostgreSQL están en redes Docker internas y no deben exponerse directamente.
