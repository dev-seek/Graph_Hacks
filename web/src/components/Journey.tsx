"use client";

import Link from "next/link";
import { type ReactNode } from "react";
import { ErrorBox, Loading, Notice } from "./ui";
import { useToken, useLoad, type Load } from "@/lib/hooks";

/** Resolves the token, then renders children with it; no token → plain-words recovery. */
export function WithToken({
  id,
  children,
}: {
  id: string;
  children: (token: string) => ReactNode;
}) {
  const { token, ready } = useToken(id);
  if (!ready) return <Loading />;
  if (!token)
    return (
      <Notice title="We can't open this page on this device">
        <p>Use the saved link from your first visit, which has your key in it. Or start again.</p>
        <p className="mt-3">
          <Link href="/start">Start with your story</Link>
        </p>
      </Notice>
    );
  return <>{children(token)}</>;
}

export function Loaded<T>({
  load,
  what,
  children,
}: {
  load: Load<T>;
  what?: string;
  children: (d: T) => ReactNode;
}) {
  if (load.error) return <ErrorBox message={load.error} onRetry={load.reload} />;
  if (!load.data) return <Loading what={what} />;
  return <>{children(load.data)}</>;
}

export { useLoad };
