import { Distribution } from "../lib";
import Link from "next/link";

const palette = ["#d52b1e", "#0038a8", "#ef8179", "#5c89df", "#aa2018", "#002776"];

function filterHref(key: "chamber" | "status", value: string, period: string) {
  return `/expedientes?${new URLSearchParams({ period, [key]: value })}`;
}

export function DonutChart({ title, items, period }: { title: string; items: Distribution[]; period: string }) {
  const total = items.reduce((sum, item) => sum + item.count, 0);
  let offset = 0;
  return <section className="chart-card"><div><p className="chart-eyebrow">Distribución</p><h2>{title}</h2></div><div className="donut-layout"><Link href="/expedientes?period=2023-2028" className="chart-hit-area" aria-label="Ver todos los expedientes"><svg viewBox="0 0 180 180" className="donut" role="img" aria-label={title}>{total ? items.slice(0, 6).map((item, index) => { const length = item.count / total * 100; const circle = <circle key={item.label} cx="90" cy="90" r="62" pathLength="100" fill="none" stroke={palette[index]} strokeWidth="22" strokeDasharray={`${length} ${100 - length}`} strokeDashoffset={-offset} transform="rotate(-90 90 90)" />; offset += length; return circle; }) : <circle cx="90" cy="90" r="62" fill="none" stroke="#e5e7eb" strokeWidth="22" /> }<text x="90" y="84" textAnchor="middle" className="donut-total">{total.toLocaleString("es-PY")}</text><text x="90" y="104" textAnchor="middle" className="donut-caption">ver todos</text></svg></Link><ul className="chart-legend">{items.slice(0, 6).map((item, index)=><li key={item.label}><span style={{background:palette[index]}}/><Link href={filterHref("chamber", item.label, period)}>{item.label.replace("CAMARA DE ", "")}</Link><Link href={filterHref("chamber", item.label, period)}><b>{Math.round(item.count / Math.max(total, 1) * 100)}%</b></Link></li>)}</ul></div></section>;
}

export function BarChart({ title, items, period }: { title: string; items: Distribution[]; period: string }) {
  const visible = items.slice(0, 5); const max = Math.max(...visible.map(item => item.count), 1);
  return <section className="chart-card"><div><p className="chart-eyebrow">Estado de tramitación</p><h2>{title}</h2></div><div className="horizontal-bars">{visible.map((item,index)=><Link className="bar-row chart-link" key={item.label} href={filterHref("status", item.label, period)} aria-label={`Ver ${item.count} expedientes ${item.label}`}><div className="bar-label"><span>{item.label}</span><b>{item.count.toLocaleString("es-PY")}</b></div><div className="bar-track"><div className="bar-fill" style={{width:`${item.count/max*100}%`,background:palette[index]}}/></div></Link>)}</div>{!visible.length && <p className="empty-chart">Sin datos disponibles.</p>}</section>;
}
