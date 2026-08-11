# Reglas del repositorio

- Leer `docs/silpy-contract.md` antes de modificar la ingesta; no inventar campos o endpoints.
- Toda sincronización debe ser idempotente, guardar payload crudo y avanzar checkpoints sólo después del commit.
- Nunca llamar SILpy desde una ruta pública ni borrar datos por una única ausencia de fuente.
- No publicar puertos de base/Redis, usar `latest`, imprimir secretos o ejecutar operaciones destructivas de Docker.
- Validar cambios de Compose con `docker compose config`; cambios backend con Ruff, pruebas y migración; cambios web con lint, tipos y build.
