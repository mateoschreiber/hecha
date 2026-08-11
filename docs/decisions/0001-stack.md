# ADR 0001: monolito modular

Se adopta un repositorio único con Next.js, FastAPI, PostgreSQL y Docker Compose. La cola de sincronización se persiste en PostgreSQL; no se incorpora Redis hasta que exista una necesidad de caché medible. Se evita una cola distribuida o microservicios hasta que las métricas justifiquen su operación.
