# hecha

Portal público de expedientes legislativos de Paraguay. La web nunca consulta SILpy en una solicitud: FastAPI y Next.js sirven el último dato válido de PostgreSQL, mientras el worker sincroniza la fuente pública cada 15 minutos.

## Arranque local

Requisitos: Docker Engine con Compose plugin. Copiá `.env.example` a `.env`, elegí una contraseña local y ejecutá:

```bash
docker compose up --build
```

Abrí `http://localhost:8080`. El worker llena PostgreSQL desde SILpy; durante una caída de la fuente, el portal conserva datos previamente sincronizados. Para validación local sin contenedores se requiere Python 3.13+ y un gestor de dependencias compatible con `pyproject.toml`.

## Comprobaciones

```bash
docker compose config
pytest
ruff check .
```

El contrato observado y fixtures de SILpy están en [`docs/silpy-contract.md`](docs/silpy-contract.md). No ejecutar operaciones destructivas sobre volúmenes de PostgreSQL.
