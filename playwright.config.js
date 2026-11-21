// @ts-check
const { defineConfig } = require("@playwright/test");

const PORT = 4173;

module.exports = defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://127.0.0.1:" + PORT + "/",
    trace: "on-first-retry",
  },
  // Serve the site over http:// like GitHub Pages does (see tests/serve.js)
  webServer: {
    command: "node tests/serve.js",
    url: "http://127.0.0.1:" + PORT + "/index.html",
    reuseExistingServer: !process.env.CI,
    env: { PORT: String(PORT) },
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        channel: process.env.CI ? undefined : "msedge",
      },
    },
  ],
});
