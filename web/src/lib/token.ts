// Family token: URL fragment on first visit, then localStorage (spec §17). Every storage access is
// wrapped: the app must work (for the current tab) when storage is blocked.

const mem = new Map<string, string>();

function get(key: string): string | null {
  try {
    return window.localStorage.getItem(key) ?? mem.get(key) ?? null;
  } catch {
    return mem.get(key) ?? null;
  }
}

function set(key: string, value: string): void {
  mem.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage blocked: keep in memory */
  }
}

export function saveToken(familyId: string, token: string): void {
  set(`cx:token:${familyId}`, token);
}

/** Reads `#t=<token>` once, stores it and removes it from the address bar. */
export function readToken(familyId: string): string | null {
  const m = /[#&]t=([^&]+)/.exec(window.location.hash);
  if (m?.[1]) {
    saveToken(familyId, decodeURIComponent(m[1]));
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }
  return get(`cx:token:${familyId}`);
}

export function forgetToken(familyId: string): void {
  mem.delete(`cx:token:${familyId}`);
  try {
    window.localStorage.removeItem(`cx:token:${familyId}`);
  } catch {
    /* nothing to remove */
  }
}

export function rememberLast(familyId: string): void {
  set("cx:last", familyId);
}

export function lastFamily(): string | null {
  return get("cx:last");
}

export function flag(name: string): boolean {
  return get(`cx:flag:${name}`) === "1";
}

export function setFlag(name: string): void {
  set(`cx:flag:${name}`, "1");
}

export function resetFlag(name: string): void {
  mem.delete(`cx:flag:${name}`);
  try {
    window.localStorage.removeItem(`cx:flag:${name}`);
  } catch {
    /* ignore */
  }
}

// The extraction to confirm is returned once, by the story or document call; keep it for the confirm
// page in this tab only (sessionStorage), never in localStorage.
const memEx = new Map<string, string>();

export function stashExtraction(familyId: string, value: unknown): void {
  const s = JSON.stringify(value);
  memEx.set(familyId, s);
  try {
    window.sessionStorage.setItem(`cx:ex:${familyId}`, s);
  } catch {
    /* kept in memory */
  }
}

export function readExtraction<T>(familyId: string): T | null {
  let s: string | null = null;
  try {
    s = window.sessionStorage.getItem(`cx:ex:${familyId}`);
  } catch {
    s = null;
  }
  s = s ?? memEx.get(familyId) ?? null;
  return s ? (JSON.parse(s) as T) : null;
}

export function clearExtraction(familyId: string): void {
  memEx.delete(familyId);
  try {
    window.sessionStorage.removeItem(`cx:ex:${familyId}`);
  } catch {
    /* ignore */
  }
}
