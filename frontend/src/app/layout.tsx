import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "AgentForge — Agent Observatory",
  description: "Autonomous multi-agent swarm with ERC-8004 trust-gated collaboration",
};

function Nav() {
  return (
    <nav className="border-b border-[#f0f0f0] bg-white/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="mx-auto max-w-5xl px-6 sm:px-12">
        <div className="flex items-center justify-between h-14">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#111] flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            </div>
            <span className="font-display text-[18px] text-[#111]">AgentForge</span>
          </Link>
          <div className="flex items-center gap-6">
            {[
              { href: "/", label: "Dashboard" },
              { href: "/agents", label: "Agents" },
              { href: "/tasks", label: "Tasks" },
              { href: "/logs", label: "Logs" },
              { href: "/trust", label: "Trust" },
              { href: "/budget", label: "Budget" },
            ].map((item) => (
              <Link key={item.href} href={item.href} className="text-[13px] text-[#999] hover:text-[#111] transition font-medium">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}>
        <div className="min-h-screen bg-[#1a1a1a] p-2.5 sm:p-4">
          <div className="grid-pattern relative mx-auto flex min-h-[calc(100vh-32px)] max-w-[1440px] flex-col overflow-hidden rounded-[20px] bg-white shadow-[0_0_0_1px_rgba(255,255,255,0.1),0_20px_60px_rgba(0,0,0,0.3)]">
            <Nav />
            <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-24 pt-8 sm:px-12">
              {children}
            </main>
            <footer className="border-t border-[#f0f0f0] px-8 py-5">
              <div className="mx-auto flex max-w-5xl items-center justify-between">
                <span className="text-[12px] text-[#bbb]">AgentForge</span>
                <span className="text-[12px] text-[#ccc]">ERC-8004 Trust-Gated Swarm</span>
              </div>
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
