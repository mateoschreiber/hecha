import Link from "next/link";

import "./globals.css";

export const metadata = {
  title: "Hecha | Datos legislativos",
  description: "Portal de expedientes legislativos de Paraguay",
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body><header className="border-b bg-white"><nav className="mx-auto flex max-w-[1180px] items-center justify-between p-4"><Link href="/" className="text-xl font-bold text-ink">hecha<span className="text-paraguay">.</span></Link><Link className="text-sm font-semibold" href="/expedientes">Explorar expedientes</Link></nav></header>{children}</body></html>;
}
