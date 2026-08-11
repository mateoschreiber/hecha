import Link from "next/link";
import { DistributionChart } from "./components/distribution-chart";
import { EvolutionChart } from "./components/evolution-chart";
import { FreshnessBadge } from "./components/freshness";
import { ExpedientCard } from "./components/expedient-card";
import { SyncButton } from "./components/sync-button";
import { Dashboard, Freshness, getApi } from "./lib";

export default async function Home() {
  const [dashboardResponse, freshnessResponse] = await Promise.all([getApi<{data:Dashboard}>("/dashboard/summary"), getApi<{data:Freshness}>("/meta/freshness")]);
  const dashboard = dashboardResponse?.data;
  return <main className="space-y-8"><section className="rounded-3xl bg-ink p-8 text-white"><p className="mb-3 text-sm font-bold uppercase tracking-[.2em] text-sun">Congreso abierto</p><h1 className="max-w-3xl text-4xl font-black sm:text-6xl">Seguí los expedientes que mueven al Paraguay.</h1><p className="mt-5 max-w-2xl text-lg text-slate-200">Datos legislativos claros, comparables y actualizados desde fuentes públicas.</p><div className="mt-6 flex flex-wrap gap-3"><Link className="inline-block rounded-lg bg-sun px-5 py-3 font-bold text-ink" href="/expedientes">Buscar expedientes</Link><SyncButton /></div></section><FreshnessBadge value={freshnessResponse?.data}/><section className="grid gap-4 sm:grid-cols-3"><div className="card"><p className="text-sm text-slate-500">Expedientes indexados</p><strong className="text-3xl">{dashboard?.kpis.total ?? 0}</strong></div><div className="card"><p className="text-sm text-slate-500">En trámite</p><strong className="text-3xl">{dashboard?.kpis.in_progress ?? 0}</strong></div><div className="card"><p className="text-sm text-slate-500">Cobertura</p><strong className="text-lg">SILpy · PostgreSQL</strong></div></section><section className="grid gap-6 lg:grid-cols-2"><DistributionChart title="Expedientes por cámara" items={dashboard?.by_chamber ?? []}/><DistributionChart title="Expedientes por estado" items={dashboard?.by_status ?? []}/><EvolutionChart items={dashboard?.evolution ?? []}/></section><section><div className="mb-4 flex justify-between"><h2 className="text-2xl font-bold">Expedientes recientes</h2><Link href="/expedientes" className="font-semibold text-paraguay">Ver todos</Link></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{dashboard?.recent.map((item)=><ExpedientCard key={item.id} item={item}/>)}</div></section></main>;
}
