import { Freshness, formatDateTime } from "../lib";
import { SyncProgress } from "./sync-progress";

export function FreshnessBadge({value}:{value?:Freshness}) {
  if (!value || value.state === "empty") return <><p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Aún no hay expedientes sincronizados. Ejecutá la carga inicial desde SILpy para poblar el portal.</p><SyncProgress /></>;
  const stale = value.state === "stale";
  return <><p className={`rounded-lg p-3 text-sm ${stale ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900"}`}>{stale ? "Datos desactualizados" : "Datos actualizados"} · última sincronización: {formatDateTime(value.expedients)}{stale && value.last_error ? ` · ${value.last_error}` : ""}</p><SyncProgress /></>;
}
