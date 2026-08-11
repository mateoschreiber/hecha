import { Distribution } from "../lib";

export function DistributionChart({title, items}:{title:string;items:Distribution[]}) {
  const max = Math.max(...items.map((item)=>item.count), 1);
  return <section className="card"><h2 className="text-xl font-bold">{title}</h2><div className="mt-4 space-y-3">{items.slice(0, 6).map((item)=><div key={item.label}><div className="flex justify-between gap-3 text-sm"><span className="truncate">{item.label}</span><b>{item.count}</b></div><div className="mt-1 h-2 rounded bg-slate-100"><div className="h-2 rounded bg-paraguay" style={{width:`${item.count / max * 100}%`}}/></div></div>)}{items.length === 0 && <p className="text-sm text-slate-500">Sin datos disponibles.</p>}</div></section>;
}
