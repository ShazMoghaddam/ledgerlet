/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the app runs on :5173 and forwards API calls to FastAPI on :8000,
// so the browser sees one origin (no CORS) exactly as it will in production.
const API = process.env.LEDGERLET_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": API, "/health": API },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: true,
    globals: true,
  },
});
