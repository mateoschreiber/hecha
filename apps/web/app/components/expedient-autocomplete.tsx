"use client";

import { useEffect, useState } from "react";

type Item = { source_id:string; number?:string; title:string };

export function ExpedientAutocomplete({initial = ""}:{initial?:string}) {
  const [value, setValue] = useState(initial); const [items, setItems] = useState<Item[]>([]);
  useEffect(() => { if (!value) return void setItems([]); const timer=setTimeout(async()=>{ const r=await fetch(`/api/v1/search?q=${encodeURIComponent(value)}`); const body=await r.json(); setItems(body.data ?? []); }, 120); return ()=>clearTimeout(timer); }, [value]);
  return <div className="relative"><input className="w-full rounded border p-3" name="q" value={value} onChange={e=>setValue(e.target.value)} placeholder="Texto, número o autor" autoComplete="off" />{items.length>0 && <ul className="absolute z-10 mt-1 max-h-80 w-full overflow-auto rounded border bg-white shadow">{items.slice(0,10).map(item=><li key={item.source_id}><a className="block p-3 text-sm hover:bg-slate-50" href={`/expedientes/${item.source_id}`}>{item.number ?? item.source_id} · {item.title}</a></li>)}</ul>}</div>;
}
