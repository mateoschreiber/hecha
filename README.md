# hecha

Portal público de expedientes legislativos de Paraguay. La web nunca consulta SILpy en una solicitud: FastAPI y Next.js sirven el último dato válido de PostgreSQL, mientras el worker sincroniza la fuente pública cada 15 minutos.

## Arranque local

Requisitos: Docker Engine con Compose plugin. Copiá `.env.example` a `.env`, elegí una contraseña local y ejecutá:

```bash
docker compose up --build
```

Abrí `http://localhost:8080`. El worker llena PostgreSQL desde SILpy; durante una caída de la fuente, el portal conserva datos previamente sincronizados. Para validación local sin contenedores se requiere Python 3.13+ y un gestor de dependencias compatible con `pyproject.toml`.

Para poblar una instalación nueva con SILpy, ejecutá una carga completa (no hay un endpoint público para ello):

```bash
docker compose run --rm worker python -m apps.worker.main --mode seed
```

Si una carga completa se interrumpe después de haber confirmado al menos un lote, se puede
continuar desde el último checkpoint confirmado sin repetir las páginas ya completadas:

```bash
docker compose run --rm worker python -m apps.worker.main --mode seed --resume
```

El servicio programado sincroniza páginas rotativas cada 15 minutos y realiza una reconciliación completa diaria a las 02:15 de `America/Asuncion`.

## Comprobaciones

```bash
docker compose config
pytest
ruff check .
python scripts/check_openapi.py
```

El contrato observado y fixtures de SILpy están en [`docs/silpy-contract.md`](docs/silpy-contract.md). No ejecutar operaciones destructivas sobre volúmenes de PostgreSQL.
