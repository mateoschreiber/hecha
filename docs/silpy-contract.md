# Contrato vigente de SILpy

Fecha de observación: 2026-08-11. Fuente canónica: `https://silpy.congreso.gov.py`.

| Paso | Ruta/campo | Contrato observado |
|---|---|---|
| Formulario | `GET /web/expedientesavanzado` | Formulario `formMain`, cookie de sesión, `action` con `jsessionid` y `jakarta.faces.ViewState`. |
| Búsqueda | `POST` al `action` | `formMain:j_idt56=A`, `formMain:desde_input`, `formMain:hasta_input`, `formMain:cmdBuscar` y el `ViewState`. |
| Resultados | `formResult:dtExpediente` | Filas con ID, acápite, número, fecha, estado, tipo, iniciativa, etapa, origen y enlace `/web/expediente/{id}`. |
| Detalle | `/web/expediente/{id}` | Fuente para relaciones cuando estén presentes y verificables. |

El portal limita el listado de la interfaz a 100 filas. El adaptador divide cada período en ventanas mensuales, conserva la sesión HTTP dentro de la consulta y confirma cada ventana antes de informar avance. Así se evita depender del paginador JSF y se puede reanudar una carga sin publicar datos inválidos. Open Data se conserva únicamente como complemento histórico: no se usa para determinar la vigencia ni la completitud de los períodos actuales.

Las fixtures JSON históricas en `tests/fixtures/silpy` cubren la normalización del dominio. Antes de cambiar selectores o campos del portal se debe añadir una fixture HTML anonimizada de formulario, resultado, detalle o error JSF y actualizar este contrato.
