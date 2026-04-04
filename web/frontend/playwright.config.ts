import * as path from "path";
import { defineConfig, devices } from "@playwright/test";

const backendDir = path.resolve(__dirname, "..", "backend");
const frontendDir = __dirname;

/** If a dev server is already on the port, reuse it (avoids bind errors when CI=false is set in env). */
const reuseExistingServer = process.env.PLAYWRIGHT_FORCE_START !== "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: backendDir,
      url: "http://localhost:8000/api/health",
      timeout: 120_000,
      reuseExistingServer,
    },
    {
      command: "npm run dev -- -p 3000",
      cwd: frontendDir,
      env: {
        ...process.env,
        NEXT_PUBLIC_API_URL: "http://localhost:8000",
      },
      url: "http://localhost:3000",
      timeout: 120_000,
      reuseExistingServer,
    },
  ],
});
