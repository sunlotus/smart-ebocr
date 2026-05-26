import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 120000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd .. && python -m backend.app',
      port: 5000,
      reuseExistingServer: true,
      timeout: 10000,
    },
    {
      command: 'npm run dev',
      port: 3000,
      reuseExistingServer: true,
      timeout: 10000,
    },
  ],
})
