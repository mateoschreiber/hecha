"use client";

import { useState } from "react";

export function SyncButton() {
  const [state, setState] = useState<"idle" | "loading" | "queued" | "error">("idle");
  const synchronize = async () => {
    setState("loading");
    try {
      const response = await fetch("/api/v1/sync", { method: "POST" });
      setState(response.ok ? "queued" : "error");
    } catch {
      setState("error");
    }
  };
  return <div className="flex flex-wrap items-center gap-3"><button type="button" onClick={synchronize} disabled={state === "loading" || state === "queued"} className="rounded-lg border border-white/30 px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60">{state === "loading" ? "Solicitando…" : state === "queued" ? "Sincronización en cola" : "Sincronizar datos públicos"}</button>{state === "queued" && <span className="text-sm text-slate-200">Se actualizarán las fuentes públicas disponibles.</span>}{state === "error" && <span className="text-sm text-red-200">No se pudo solicitar la sincronización.</span>}</div>;
}
