"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { call, friendly } from "./api";
import { readToken } from "./token";

const noSubscribe = () => () => {};

/** Family token for this browser (fragment first, then storage). `ready` is false until hydrated. */
export function useToken(id: string): { token: string | null; ready: boolean } {
  const t = useSyncExternalStore(
    noSubscribe,
    () => readToken(id),
    () => undefined,
  );
  return { token: t ?? null, ready: t !== undefined };
}

export type Load<T> = { data: T | null; error: string | null; loading: boolean; reload: () => void };

export function useLoad<T>(path: string | null, token: string | null, clinicianCode?: string): Load<T> {
  const [res, setRes] = useState<{ key: string; data: T | null; error: string | null } | null>(null);
  const [n, setN] = useState(0);
  const key = `${path}|${token}|${clinicianCode}|${n}`;
  useEffect(() => {
    if (!path) return;
    let live = true;
    call<T>(path, { token, clinicianCode })
      .then((d) => live && setRes({ key, data: d, error: null }))
      .catch((e) => live && setRes({ key, data: null, error: friendly(e) }));
    return () => {
      live = false;
    };
  }, [path, token, clinicianCode, key]);
  const reload = useCallback(() => setN((x) => x + 1), []);
  const cur = res && res.key === key ? res : null;
  return { data: cur?.data ?? null, error: cur?.error ?? null, loading: path !== null && !cur, reload };
}

/** False during server render and hydration, true afterwards (for browser-only values). */
export function useMounted(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
}
