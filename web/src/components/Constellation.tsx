"use client";

import { useMemo } from "react";
import type { Constellation as Data } from "@/lib/api";

// Deterministic star positions from the id, so the picture is stable between visits.
function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967295;
}

export function Constellation({ data }: { data: Data }) {
  const pts = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    for (const s of data.stars)
      m.set(s.id, { x: 24 + hash(`x${s.id}`) * 272, y: 24 + hash(`y${s.id}`) * 152 });
    return m;
  }, [data]);
  const n = data.stars.length;
  return (
    <figure className="m-0">
      <svg
        viewBox="0 0 320 200"
        role="img"
        aria-label={
          n === 0
            ? "Your constellation is empty so far. Each thing you confirm becomes a star."
            : `Your constellation: ${n} ${n === 1 ? "star" : "stars"}, one for each thing you have confirmed.`
        }
        className="w-full rounded-2xl bg-night"
      >
        {data.lines.map((l) => {
          const a = pts.get(l.source);
          const b = pts.get(l.target);
          if (!a || !b) return null;
          return (
            <line
              key={`${l.source}-${l.target}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#F2B544"
              strokeOpacity={0.55}
              strokeWidth={1.2}
            />
          );
        })}
        {data.stars.map((s, i) => {
          const p = pts.get(s.id);
          if (!p) return null;
          return (
            <g key={s.id} className="cx-star" style={{ animationDelay: `${Math.min(i, 12) * 90}ms` }}>
              <circle cx={p.x} cy={p.y} r={7} fill="#F2B544" opacity={0.18} />
              <circle cx={p.x} cy={p.y} r={3.2} fill="#F2B544" />
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 text-sm text-muted">
        {n === 0
          ? "Each thing you confirm becomes a star. Stars join when they belong to the same part of the body."
          : "Each star is something you've confirmed. Lines join stars from the same part of the body. This picture doesn't say what's causing anything."}
      </figcaption>
      {n > 0 ? (
        <ul className="sr-only">
          {data.stars.map((s) => (
            <li key={s.id}>{s.label}</li>
          ))}
        </ul>
      ) : null}
    </figure>
  );
}
