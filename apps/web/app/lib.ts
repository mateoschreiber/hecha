export type Expedient = { id:string; source_id:string; number?:string; title:string; type?:string; chamber?:string; status?:string; stage?:string; filed_on?:string; synced_at?:string; source_url?:string; authors?:{name:string;party?:string}[]; attachments?:{id:string;url?:string;info?:string}[]; committees?:string[] };
const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
export async function getApi<T>(path:string): Promise<T | null> { try { const response = await fetch(`${api}/api/v1${path}`, { next:{revalidate:60} }); return response.ok ? response.json() : null; } catch { return null; } }
export function formatDate(value?:string) { return value ? new Intl.DateTimeFormat("es-PY", {dateStyle:"medium", timeZone:"America/Asuncion"}).format(new Date(value)) : "Sin fecha"; }
