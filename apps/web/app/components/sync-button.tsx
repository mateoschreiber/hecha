"use client";

import { useState } from "react";

export function SyncButton() {
  const [state, setState] = useState<"idle" | "loading" | "queued" | "cooldown" | "error">("idle");
  const synchronize = async () => {
    setState("loading");
    try {
      const response = await fetch("/api/v1/sync", { method: "POST" });
      const body = response.ok ? await response.json() : null;
      setState(response.ok && body?.data?.status === "cooldown" ? "cooldown" : response.ok ? "queued" : "error");
    } catch {
      setState("error");
    }
  };
  return <div className="flex flex-wrap items-center gap-3"><button type="button" onClick={synchronize} disabled={state === "loading" || state === "queued"} className="sync-action">{state === "loading" ? "Solicitando…" : state === "queued" ? "Sincronización en cola" : state === "cooldown" ? "Actualizado recientemente" : "Sincronizar datos públicos"}</button><span aria-live="polite" className="text-sm text-slate-200">{state === "queued" ? "Solicitud recibida: el progreso aparecerá debajo del estado de frescura." : state === "cooldown" ? "Ya existe una actualización reciente; podés volver a solicitarla en unos minutos." : state === "error" ? "No se pudo solicitar la sincronización. Intentá de nuevo." : ""}</span></div>;
}
