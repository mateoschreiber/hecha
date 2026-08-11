import Link from "next/link";
import { FreshnessBadge } from "../components/freshness";
import { Expedient, Freshness, getApi } from "../lib";
import { ExpedientCard } from "../components/expedient-card";
import { ExpedientAutocomplete } from "../components/expedient-autocomplete";

type Listing = {data: Expedient[];meta:{total:number;page:number;limit:number}};
type Catalog = {data:string[]};
type Params = {q?:string;chamber?:string;status?:string;type?:string;period?:string;page?:string;filed_from?:string;filed_to?:string};
const periods = ["2023-2028", "2018-2023"];
export default async function Expedients({searchParams}:{searchParams:Promise<Params>}) {
  const params=await searchParams; const query=new URLSearchParams(Object.entries(params).filter(([,v])=>v) as [string,string][]); const path=`/expedients?limit=20&${query}`;
  const selectedPeriod=params.period ?? "2023-2028";
  const [listing, freshness, statuses]=await Promise.all([getApi<Listing>(path), getApi<{data:Freshness}>("/meta/freshness"), getApi<Catalog>(`/catalogs/statuses?period=${selectedPeriod}`)]);
  const current=listing?.meta.page ?? 1; const total=listing?.meta.total ?? 0; const hasNext=current * 20 < total;
  const href=(page:number)=>`/expedientes?${new URLSearchParams({...params,page:String(page)} as Record<string,string>)}`;
  return <main><h1 className="text-4xl font-black">Explorar expedientes</h1><div className="my-5"><FreshnessBadge value={freshness?.data}/></div><form className="card my-6 grid gap-3 md:grid-cols-5"><ExpedientAutocomplete initial={params.q}/><select className="rounded border p-3" name="period" defaultValue={selectedPeriod} aria-label="Período legislativo">{periods.map(period=><option key={period} value={period}>{period}</option>)}</select><select className="rounded border p-3" name="chamber" defaultValue={params.chamber ?? ""} aria-label="Cámara"><option value="">Cámara</option><option value="CAMARA DE DIPUTADOS">Diputados</option><option value="CAMARA DE SENADORES">Senadores</option></select><select className="rounded border p-3" name="status" defaultValue={params.status ?? ""} aria-label="Estado"><option value="">Estado</option>{(statuses?.data ?? []).map(status=><option key={status} value={status}>{status}</option>)}</select><button className="rounded bg-ink p-3 font-bold text-white">Aplicar filtros</button></form><p className="mb-4 text-slate-600">{total} resultados</p>{total === 0 ? <section className="card"><h2 className="text-xl font-bold">No hay expedientes para mostrar</h2><p className="mt-2 text-slate-600">Probá otro filtro o ejecutá la carga inicial de SILpy.</p></section> : <><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{listing?.data.map(item=><ExpedientCard key={item.id} item={item}/>)}</div><nav className="mt-8 flex gap-3"><Link className={`rounded border px-4 py-2 ${current === 1 ? "pointer-events-none opacity-40" : ""}`} href={href(current - 1)}>Anterior</Link><Link className={`rounded border px-4 py-2 ${!hasNext ? "pointer-events-none opacity-40" : ""}`} href={href(current + 1)}>Siguiente</Link></nav></>}</main>;
}
