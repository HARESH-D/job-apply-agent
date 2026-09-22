"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Profile" },
  { href: "/jobs", label: "Jobs" },
  { href: "/scraper", label: "Scraper" },
] as const;

export function SideNav() {
  const pathname = usePathname();

  return (
    <nav className="side-nav" aria-label="Primary">
      {LINKS.map(({ href, label }) => {
        const current =
          href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
