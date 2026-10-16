import type { components } from "@/api/schema";

export type Schemas = components["schemas"];
export type State = Schemas["ParentState"];
export type Round = Schemas["ParentRound"];
export type Extraction = Schemas["ParentExtractionOut"];
export type Pack = Schemas["ParentPack"];
export type Timeline = Schemas["ParentTimeline"];
export type Constellation = Schemas["ParentConstellation"];
export type AnswersOut = Schemas["ParentAnswersOut"];
export type ClinicianView = Schemas["ClinicianView"];
export type DemoStep = Schemas["DemoStep"];
export type DemoJourney = Schemas["DemoJourney"];

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Plain-words message for every failure: what happened and what to do next (spec §4.7). */
export function friendly(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403)
      return "We couldn't open this page with the link you used. Use the saved link from your first visit, or start again.";
    if (e.status === 404)
      return "We couldn't find that. It may have been deleted. You can start again from the home page.";
    if (e.status === 409)
      return "That step isn't available yet. Go back to the main page to see what comes next.";
    if (e.status === 429)
      return "Lots of people are using this right now. Please wait a minute and try again.";
  }
  return "Something went wrong on our side. Your answers are safe. Please try again in a moment.";
}

type Opts = { token?: string | null; clinicianCode?: string; method?: string; body?: unknown };

export async function call<T>(path: string, o: Opts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (o.token) headers.Authorization = `Bearer ${o.token}`;
  if (o.clinicianCode) headers["X-Clinician-Code"] = o.clinicianCode;
  if (o.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method: o.method ?? (o.body !== undefined ? "POST" : "GET"),
      headers,
      body: o.body !== undefined ? JSON.stringify(o.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network");
  }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const fam = (id: string) => `/families/${id}`;
