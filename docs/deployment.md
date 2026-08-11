# Despliegue reproducible

## Local

1. Instalar Docker Engine y el plugin Compose.
2. Copiar `.env.example` a `.env`; no contiene secretos.
3. Ejecutar `docker compose up --build -d`.
4. Confirmar `curl --fail http://localhost:8080/api/v1/health/ready`.
5. Abrir el portal y pulsar **Sincronizar datos públicos**. Consultar el avance en `/api/v1/sync/progress`.

Para guardar un respaldo recuperable antes de una actualización:

```bash
docker compose exec -T db pg_dump -U hecha -d hecha -Fc > hecha-backup.dump
```

Para restaurarlo en una instalación detenida, crear la base y ejecutar `pg_restore -U hecha -d hecha --clean hecha-backup.dump` desde el contenedor PostgreSQL. Nunca borrar el volumen `postgres-data` hasta validar un respaldo.

## VPS con dominio

1. Instalar Docker Engine, Compose y configurar DNS del dominio hacia el VPS.
2. Cambiar `infra/caddy/Caddyfile` de `:80` al dominio público. Caddy obtiene y renueva TLS automáticamente.
3. Copiar el repositorio y ejecutar `docker compose up --build -d`.
4. Verificar salud, inicio, API y el botón de sincronización.
5. Para actualizar: crear backup, obtener el commit aprobado, ejecutar `docker compose up --build -d`, esperar salud y repetir smoke tests.

Sólo Caddy publica puertos. No abrir 5432, 8000 ni 3000 en firewall o Compose. El sistema no usa tokens de SILpy, usuarios privados ni secretos versionados; PostgreSQL confía únicamente en contenedores de la red interna.

## Diagnóstico y rollback

- `docker compose ps` muestra servicios y salud.
- `docker compose logs -f worker` muestra la fase de importación; `docker compose logs -f api` muestra errores de API.
- Si una sincronización falla, el portal sigue sirviendo el último dato válido y el error se ve en `/api/v1/sync/progress`.
- Para rollback de aplicación, volver al commit anterior y recrear los servicios. Para rollback de datos, restaurar el dump validado.
