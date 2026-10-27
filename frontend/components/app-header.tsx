"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

import { useSession } from "@/lib/session";

import { Logo } from "./logo";

function NavLinks({ links }: { links: { href: string; label: string }[] }) {
  const pathname = usePathname();
  return links.map((link) => (
    <Link key={link.href} href={link.href} aria-current={pathname.startsWith(link.href) ? "page" : undefined}>
      {link.label}
    </Link>
  ));
}

export function AppHeader() {
  const { user, canReview, signOut } = useSession();
  const links = [
    { href: "/vendors", label: "Vendors" },
    ...(canReview ? [{ href: "/review", label: "Review queue" }] : []),
  ];

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/vendors" className="brand">
          <Logo />
        </Link>
        <nav className="nav" aria-label="Main">
          {/* The fallback is the same links without the current-page highlight. */}
          <Suspense
            fallback={links.map((link) => (
              <Link key={link.href} href={link.href}>
                {link.label}
              </Link>
            ))}
          >
            <NavLinks links={links} />
          </Suspense>
        </nav>
        {user && (
          <div className="account">
            <span>
              <strong>{user.name}</strong>, {user.role} at {user.tenant.name}
            </span>
            <button type="button" className="btn btn-quiet" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
