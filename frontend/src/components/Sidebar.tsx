"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dna", label: "Driver DNA", icon: "🧬" },
  { href: "/dna/compare", label: "Compare", icon: "⚡" },
  { href: "/telemetry", label: "Telemetry", icon: "📊" },
  { href: "/tyres", label: "Tyres", icon: "🔘" },
  { href: "/drivers", label: "Drivers", icon: "🏎️" },
  { href: "/races", label: "Races", icon: "🏁" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-card border-r border-border flex flex-col z-50">
      <Link href="/" className="px-5 py-5 border-b border-border">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-accent">F1</span> AI Platform
        </h1>
      </Link>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-accent/10 text-accent font-medium"
                  : "text-muted hover:text-foreground hover:bg-card-hover"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-border text-xs text-muted">
        2023–2024 Season Data
      </div>
    </aside>
  );
}
