"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import { PARENT_DISCLAIMER } from "@/copy";

export function Header() {
  const path = usePathname() ?? "/";
  const nav = [
    ["/demo", "Example families"],
    ["/help", "Help"],
    ["/about", "About"],
  ] as const;
  return (
    <header className="no-print border-b border-line bg-card">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
        <Link href="/" className="flex min-h-11 items-center gap-2 font-serif text-xl font-bold no-underline">
          <Sparkles aria-hidden="true" size={22} className="text-night" />
          Constellation
        </Link>
        <nav aria-label="Main" className="ml-auto flex flex-wrap items-center gap-x-4">
          {nav.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={path.startsWith(href) ? "page" : undefined}
              className="flex min-h-11 items-center"
            >
              {label}
            </Link>
          ))}
          <button
            type="button"
            className="min-h-11 cursor-pointer font-bold underline underline-offset-4"
            onClick={() => window.dispatchEvent(new Event("cx:open-tour"))}
          >
            How it works
          </button>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="no-print mt-12 border-t border-line bg-card">
      <div className="mx-auto max-w-4xl space-y-3 px-4 py-6 text-sm text-muted">
        <p>{PARENT_DISCLAIMER}</p>
        <p>
          Built on the Human Phenotype Ontology, Orphanet and the GA4GH Phenopacket Store.{" "}
          <Link href="/about">Sources, limits and AI use</Link>
        </p>
      </div>
    </footer>
  );
}
