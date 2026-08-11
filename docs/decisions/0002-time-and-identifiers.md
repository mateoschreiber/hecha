# ADR 0002: tiempo, IDs y bajas

Las fechas se almacenan UTC y se presentan en `America/Asuncion`. Los registros usan UUID interno y `(source_system, source_id)` único. Una ausencia de SILpy no elimina datos: las bajas son lógicas y requieren reconciliaciones corroboradas.
