"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Agentic AI"],
  ["/cf", "CF"],
  ["/comparison", "Comparison"],
] as const;

export function TopNav() {
  const pathname = usePathname();
  const currentLabel = links.find(([href]) => href === pathname)?.[1] ?? "Agentic AI";

  return (
    <>
      <div className="nav-status">
        <span className="eyebrow">Current Page</span>
        <strong>{currentLabel}</strong>
      </div>
      <nav className="nav" aria-label="Primary">
        {links.map(([href, label]) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={isActive ? "nav-link nav-link-active" : "nav-link"}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
