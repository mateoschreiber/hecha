export type Expedient = { id:string; source_id:string; number?:string; title:string; type?:string; chamber?:string; status?:string; stage?:string; filed_on?:string; synced_at?:string; source_url?:string; authors?:{name:string;party?:string}[]; attachments?:{id:string;url?:string;info?:string}[]; committees?:string[] };
export type Freshness = { expedients?:string; count:number; state:"fresh"|"stale"|"empty"; last_success_at?:string; last_error_at?:string; last_error?:string };
export type Distribution = {label:string;count:number};
export type Dashboard = {kpis:{total:number;in_progress:number};by_chamber:Distribution[];by_status:Distribution[];by_type:Distribution[];evolution:{month:string;count:number}[];recent:Expedient[]};
const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
export async function getApi<T>(path:string): Promise<T | null> { try { const response = await fetch(`${api}/api/v1${path}`, { next:{revalidate:60} }); return response.ok ? response.json() : null; } catch { return null; } }
export function formatDate(value?:string) { return value ? new Intl.DateTimeFormat("es-PY", {dateStyle:"medium", timeZone:"America/Asuncion"}).format(new Date(value)) : "Sin fecha"; }
export function formatDateTime(value?:string) { return value ? new Intl.DateTimeFormat("es-PY", {dateStyle:"medium", timeStyle:"short", timeZone:"America/Asuncion"}).format(new Date(value)) : "Sin datos"; }
