"use client";

import { useRouter, usePathname } from "next/navigation";
import { Home, Clock, Settings, type LucideIcon } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  match: (path: string) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: Home, match: (p) => p === "/" },
  { href: "/jobs", label: "Jobs", icon: Clock, match: (p) => p.startsWith("/jobs") },
  { href: "/settings", label: "Settings", icon: Settings, match: (p) => p.startsWith("/settings") },
];

/**
 * Navigation mobile en bas d'écran.
 * Visible uniquement < 768px (CSS .bottom-nav).
 */
export function BottomNav() {
  const router = useRouter();
  const pathname = usePathname() || "/";

  return (
    <nav className="bottom-nav" aria-label="Main navigation">
      {NAV_ITEMS.map((item) => {
        const isActive = item.match(pathname);
        const Icon = item.icon;
        return (
          <button
            key={item.href}
            type="button"
            className={`bottom-nav-item ${isActive ? "bottom-nav-active" : ""}`}
            onClick={() => router.push(item.href)}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon size={20} />
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export default BottomNav;
