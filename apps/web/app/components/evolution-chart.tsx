export function EvolutionChart({items}:{items:{month:string;count:number}[]}) {
  const max = Math.max(...items.map((item)=>item.count), 1);
  return <section className="card"><h2 className="text-xl font-bold">Evolución por ingreso</h2><div className="mt-5 flex h-40 items-end gap-2">{items.slice(-12).map((item)=><div className="flex min-w-0 flex-1 flex-col items-center gap-1" key={item.month}><span className="text-xs font-bold">{item.count}</span><div className="w-full rounded-t bg-sun" style={{height:`${item.count / max * 100}%`}}/><span className="truncate text-[10px] text-slate-500">{item.month.slice(0,7)}</span></div>)}</div>{items.length === 0 && <p className="mt-3 text-sm text-slate-500">Sin fechas de ingreso disponibles.</p>}</section>;
}
