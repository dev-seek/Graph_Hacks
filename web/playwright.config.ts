import { defineConfig, devices } from "@playwright/test";

// Own backend (LLM_MODE=off: deterministic, no network) and own production web build, on ports that
// do not collide with the docker stack. FalkorDB must be up (`make up`).
const API = "http://127.0.0.1:8010";
const WEB = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: WEB, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `cd .. && LLM_MODE=off CREATE_LIMIT_PER_HOUR=1000 FALKORDB_HOST=localhost uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010`,
      url: `${API}/api/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `API_ORIGIN=${API} pnpm build && API_ORIGIN=${API} pnpm start -p 3100`,
      url: WEB,
      reuseExistingServer: true,
      timeout: 300_000,
    },
  ],
});
