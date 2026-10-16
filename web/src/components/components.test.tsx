import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Constellation } from "./Constellation";
import { Tour, TOURS } from "./Tour";
import { saveToken, readToken } from "@/lib/token";
import { friendly, ApiError } from "@/lib/api";
import { useState } from "react";

describe("Constellation", () => {
  it("announces the star count and lists labels for screen readers only", () => {
    render(
      <Constellation
        data={{
          stars: [
            { id: "a", label: "Walks late", system: "nervous" },
            { id: "b", label: "Small head", system: "nervous" },
          ],
          lines: [{ source: "a", target: "b" }],
        }}
      />,
    );
    expect(screen.getByRole("img")).toHaveAccessibleName(/2 stars/);
    expect(screen.getByText("Walks late").closest("ul")).toHaveClass("sr-only");
    expect(document.querySelectorAll("line")).toHaveLength(1);
  });
  it("explains an empty sky", () => {
    render(<Constellation data={{ stars: [], lines: [] }} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/empty/);
  });
});

function Harness({ role }: { role: "parent" | "clinician" | "centre" }) {
  const [open, setOpen] = useState(true);
  return <Tour role={role} open={open} onClose={() => setOpen(false)} />;
}

describe("Tour", () => {
  it("steps forward and back, and skip closes it", () => {
    render(<Harness role="parent" />);
    expect(screen.getByText(`Step 1 of ${TOURS.parent.length}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText(`Step 2 of ${TOURS.parent.length}`)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText(`Step 1 of ${TOURS.parent.length}`)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
  });
  it("has 4, 3 and 3 steps for parents, clinicians and the centre", () => {
    expect([TOURS.parent.length, TOURS.clinician.length, TOURS.centre.length]).toEqual([4, 3, 3]);
  });
});

describe("token storage", () => {
  it("reads a fragment token once, stores it and clears the address bar", () => {
    window.history.replaceState(null, "", "/j/abc#t=secret%2Fvalue");
    expect(readToken("abc")).toBe("secret/value");
    expect(window.location.hash).toBe("");
    expect(readToken("abc")).toBe("secret/value");
  });
  it("keeps working when storage throws", () => {
    const orig = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("blocked");
      },
    });
    saveToken("xyz", "tok");
    expect(readToken("xyz")).toBe("tok");
    if (orig) Object.defineProperty(window, "localStorage", orig);
  });
});

describe("friendly errors", () => {
  it("always say what happened and what to do", () => {
    for (const s of [0, 401, 404, 409, 429, 500]) {
      const m = friendly(new ApiError(s, "x"));
      expect(m.length).toBeGreaterThan(30);
      expect(m).not.toMatch(/stack|trace|undefined|\[object/i);
    }
  });
});
