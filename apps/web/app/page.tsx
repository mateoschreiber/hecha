import Link from "next/link";
import { BarChart, DonutChart } from "./components/distribution-chart";
import { EvolutionChart } from "./components/evolution-chart";
import { FreshnessBadge } from "./components/freshness";
import { ExpedientCard } from "./components/expedient-card";
import { SyncButton } from "./components/sync-button";
import { Dashboard, Freshness, getApi } from "./lib";

export default async function Home() {
  const [dashboardResponse, freshnessResponse] = await Promise.all([getApi<{data:Dashboard}>("/dashboard/summary"), getApi<{data:Freshness}>("/meta/freshness")]);
  const dashboard = dashboardResponse?.data;
  const period = "2023-2028";
  const recentMonth = dashboard?.evolution.slice(-1)[0];
  const monthHref = recentMonth ? `/expedientes?${new URLSearchParams({period, filed_from: recentMonth.month.slice(0, 10)})}` : `/expedientes?period=${period}`;
  return <main className="space-y-7"><section className="hero-dashboard"><div><p className="mb-3 text-sm font-bold uppercase tracking-[.2em] text-paraguay">Observatorio legislativo</p><h1>El Congreso, <em>en datos.</em></h1><p>Seguimiento visual de la actividad legislativa paraguaya, actualizado desde fuentes públicas.</p><div className="mt-7 flex flex-wrap gap-3"><Link className="hero-action" href={`/expedientes?period=${period}`}>Explorar expedientes</Link><SyncButton /></div></div><Link href={`/expedientes?period=${period}`} className="hero-stat"><span>Período vigente</span><strong>2023—2028</strong><small>{dashboard?.kpis.total ?? 0} expedientes analizados</small></Link></section><FreshnessBadge value={freshnessResponse?.data}/><section className="metric-grid"><Link href={`/expedientes?period=${period}`} className="metric-card metric-action"><span>Total indexado</span><strong>{dashboard?.kpis.total ?? 0}</strong><small>Ver expedientes públicos →</small></Link><Link href={`/expedientes?${new URLSearchParams({period,status:"EN TRAMITE"})}`} className="metric-card metric-red metric-action"><span>En trámite</span><strong>{dashboard?.kpis.in_progress ?? 0}</strong><small>Ver documentos en curso →</small></Link><Link href={monthHref} className="metric-card metric-action"><span>Actividad reciente</span><strong>{recentMonth?.count ?? 0}</strong><small>Ver ingresos del último mes →</small></Link></section><section className="dashboard-charts"><DonutChart title="Por cámara" items={dashboard?.by_chamber ?? []} period={period}/><BarChart title="Expedientes por estado" items={dashboard?.by_status ?? []} period={period}/><EvolutionChart items={dashboard?.evolution ?? []} period={period}/></section><section><div className="mb-4 flex justify-between"><h2 className="text-2xl font-bold">Expedientes recientes</h2><Link href={`/expedientes?period=${period}`} className="font-semibold text-paraguay">Ver todos</Link></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{dashboard?.recent.map((item)=><ExpedientCard key={item.id} item={item}/>)}</div></section></main>;
}
