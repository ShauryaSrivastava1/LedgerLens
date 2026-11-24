import type { Metadata } from "next";
import { Source_Serif_4, Inter, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import AuthStatus from "@/components/AuthStatus";

const displayFont = Source_Serif_4({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});
const bodyFont = Inter({ subsets: ["latin"], variable: "--font-body" });
const monoFont = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Intelligent Equity Analysis Platform",
  description: "Evidence-based equity research for Indian listed companies.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable}`}>
      <body>
        <AuthProvider>
          <div className="flex min-h-screen">
            <aside className="w-56 shrink-0 bg-ink text-paper/90 flex flex-col">
              <div className="px-5 py-6 border-b border-white/10">
                <Link href="/" className="block">
                  <div className="font-display text-lg leading-tight text-paper">Equity<br />Ledger</div>
                  <div className="text-[11px] tracking-wide text-paper/50 mt-1 uppercase">Evidence, not signals</div>
                </Link>
              </div>
              <nav className="flex-1 px-3 py-4 space-y-1 text-sm">
                <SidebarLink href="/">Companies</SidebarLink>
                <SidebarLink href="/compare">Compare</SidebarLink>
                <div className="pt-3 mt-3 border-t border-white/10">
                  <SidebarLink href="/portfolio">Portfolio</SidebarLink>
                  <SidebarLink href="/watchlist">Watchlist</SidebarLink>
                  <SidebarLink href="/alerts">Alerts</SidebarLink>
                </div>
              </nav>
              <AuthStatus />
              <div className="px-5 py-4 border-t border-white/10 text-[11px] text-paper/40 leading-relaxed">
                Every score cites its source.
                No recommendations to buy or sell.
              </div>
            </aside>
            <main className="flex-1 min-w-0">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

function SidebarLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="block rounded px-3 py-2 text-paper/70 hover:text-paper hover:bg-white/5 transition-colors"
    >
      {children}
    </Link>
  );
}
