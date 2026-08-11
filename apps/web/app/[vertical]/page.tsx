import Link from "next/link";

import { getApi } from "../lib";

const resources = {
  sesiones: { api: "sessions", title: "Sesiones plenarias" },
  votaciones: { api: "votes", title: "Votaciones" },
  legisladores: { api: "legislators", title: "Legisladores" },
  comisiones: { api: "commissions", title: "Comisiones" },
} as const;

type Resource = { id: string; source_id: string; title: string; chamber?: string; period?: string; source_url?: string };
type Listing = { data: Resource[]; meta: { total: number } };

export default async function PublicVertical({ params }: { params: Promise<{ vertical: string }> }) {
  const { vertical } = await params;
  const resource = resources[vertical as keyof typeof resources];
  if (!resource) return <main><h1 className="text-3xl font-black">Sección no encontrada</h1></main>;
  const response = await getApi<Listing>(`/${resource.api}?period=2023-2028`);
  const rows = response?.data ?? [];
  return <main><h1 className="text-4xl font-black">{resource.title}</h1><p className="mt-3 text-slate-600">Datos públicos sincronizados desde SILpy para el período 2023-2028.</p><p className="mt-6 text-sm text-slate-500">{response?.meta.total ?? 0} resultados</p>{rows.length ? <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{rows.map(row=><article className="card" key={row.id}><p className="font-mono text-sm text-paraguay">{row.source_id}</p><h2 className="mt-2 font-bold">{row.title}</h2><p className="mt-2 text-sm text-slate-600">{row.chamber ?? "Sin cámara"}</p>{row.source_url && <a className="mt-3 inline-block text-sm font-semibold text-paraguay" href={row.source_url}>Ver fuente SILpy ↗</a>}</article>)}</div> : <section className="card mt-6"><h2 className="text-xl font-bold">Aún sin datos sincronizados</h2><p className="mt-2 text-slate-600">Usá el botón «Sincronizar datos públicos» desde el inicio. Esta sección mostrará información cuando SILpy publique resultados verificables.</p><Link className="mt-4 inline-block font-semibold text-paraguay" href="/">Ir al inicio</Link></section>}</main>;
}
