# Contrato observado de SILpy

Fecha de observación: 2026-08-11. Fuente pública: `https://datos.congreso.gov.py/opendata/api`.

| Recurso | Ruta | Observación |
|---|---|---|
| Listado | `/data/proyecto?offset={page}&limit={size}` | Array JSON; documentación pública indica `limit` máximo 50. |
| Detalle | `/data/proyecto/{idProyecto}/detalle` | Añade autores, adjuntos y texto de comisiones. |

El listado expone `idProyecto`, `expedienteCamara`, `acapite`, cámara, tipo, estado, etapa y `fechaIngresoExpediente` en formato `DD/MM/YYYY`. No se observaron `updated_at`, ETag ni cursor estable. Por ello el worker rota páginas en sincronizaciones parciales y realiza una reconciliación completa diaria. Las respuestas guardadas en `tests/fixtures/silpy` son la base contractual de CI; cambios incompatibles deben añadir una fixture y una regla de parser antes de modificar el dominio.
