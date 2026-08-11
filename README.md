# hecha

Portal público de datos legislativos paraguayos. El navegador sólo consulta la API local; PostgreSQL es la fuente de verdad y SILpy se consulta exclusivamente desde el worker cuando una persona pulsa **Sincronizar datos públicos**.

## Inicio local

Requisito único: Docker Engine con Compose.

```bash
cp .env.example .env
docker compose up --build -d
```

Abrí `http://localhost:8080` y pulsá **Sincronizar datos públicos**. Hay una única cola global: solicitudes simultáneas se deduplican y no disparan conexiones paralelas contra SILpy.

Comprobaciones:

```bash
docker compose config --quiet
curl --fail http://localhost:8080/api/v1/health/ready
curl http://localhost:8080/api/v1/sync/progress
```

Las fuentes SILpy son públicas y no requieren claves. Caddy es el único servicio con puerto publicado; API, worker y PostgreSQL permanecen en redes Docker internas. PostgreSQL usa autenticación `trust` exclusivamente en esa red aislada; no debe publicarse su puerto.

## Desarrollo y calidad

```bash
uv run ruff check .
uv run mypy backend apps
uv run pytest
uv run python scripts/check_openapi.py
```

El contrato de SILpy está en [`docs/silpy-contract.md`](docs/silpy-contract.md) y la guía local/VPS en [`docs/deployment.md`](docs/deployment.md).
