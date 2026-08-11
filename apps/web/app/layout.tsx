import Link from "next/link";

import "./globals.css";

export const metadata = {
  title: "Hecha | Datos legislativos",
  description: "Portal de expedientes legislativos de Paraguay",
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body><header className="border-b bg-white"><nav className="mx-auto flex max-w-[1180px] items-center justify-between gap-4 p-4"><Link href="/" className="text-xl font-bold text-ink">hecha<span className="text-paraguay">.</span></Link><div className="flex flex-wrap gap-4 text-sm font-semibold"><Link href="/expedientes">Expedientes</Link><Link href="/sesiones">Sesiones</Link><Link href="/votaciones">Votaciones</Link><Link href="/legisladores">Legisladores</Link><Link href="/comisiones">Comisiones</Link></div></nav></header>{children}</body></html>;
}
