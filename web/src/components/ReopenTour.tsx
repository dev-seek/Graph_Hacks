"use client";

import { Button } from "./ui";

export function ReopenTour() {
  return (
    <Button tone="secondary" onClick={() => window.dispatchEvent(new Event("cx:open-tour"))}>
      Take the short tour
    </Button>
  );
}
