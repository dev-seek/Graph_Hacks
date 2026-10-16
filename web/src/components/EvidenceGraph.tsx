"use client";

import { useEffect, useRef } from "react";
import type { GEdge, GNode } from "@/lib/demo";

const COLOR: Record<GNode["kind"], string> = {
  family: "#24305E",
  finding: "#F2B544",
  round: "#37705F",
  gate: "#B42318",
};

export function EvidenceGraph({ nodes, edges }: { nodes: GNode[]; edges: GEdge[] }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let cy: import("cytoscape").Core | undefined;
    let dead = false;
    void import("cytoscape").then(({ default: cytoscape }) => {
      if (dead || !el.current) return;
      cy = cytoscape({
        container: el.current,
        elements: [
          ...nodes.map((n) => ({ data: { id: n.id, label: n.label, color: COLOR[n.kind] } })),
          ...edges.map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target, label: e.label } })),
        ],
        layout: { name: "cose", animate: false, padding: 8 },
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(color)",
              label: "data(label)",
              "font-size": 9,
              color: "#1C2333",
              "text-wrap": "wrap",
              "text-max-width": "70px",
              "text-valign": "bottom",
              "text-margin-y": 3,
              width: 16,
              height: 16,
            },
          },
          {
            selector: "edge",
            style: { width: 1.2, "line-color": "#8A8475", "curve-style": "bezier", "target-arrow-shape": "triangle", "target-arrow-color": "#8A8475", "arrow-scale": 0.7 },
          },
        ],
        userZoomingEnabled: false,
        userPanningEnabled: false,
        boxSelectionEnabled: false,
      });
    });
    return () => {
      dead = true;
      cy?.destroy();
    };
  }, [nodes, edges]);
  const summary = `Evidence graph: ${nodes.length} nodes, ${edges.length} edges. ${nodes.map((n) => n.label).join(", ")}.`;
  return <div ref={el} role="img" aria-label={summary} className="h-64 w-full rounded-xl border border-line bg-card" />;
}
