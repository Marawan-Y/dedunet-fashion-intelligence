/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

/* The API base is baked in at BUILD time, exactly as the classic client did it.
 *
 * Not at run time: the web container runs with a read-only root filesystem, so nothing may
 * write into the served directory after start. `ADR-0004` keeps that guarantee — the build
 * stage is new, the runtime posture is not. `VITE_API_BASE_URL` is the build argument the
 * Dockerfile passes through, and an empty value means "the page host on the development
 * API port", which is what a bare local checkout and docker-compose.yml both want. */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  /* Unit tests, scoped to src/ ON PURPOSE.
   *
   * Vitest's default include pattern reaches every directory, so it would sweep up the
   * Playwright specs under `e2e/` — they import @playwright/test and cannot run under
   * Vitest, so the suite would fail for reasons that have nothing to do with the
   * application.
   *
   * `node` environment, not jsdom. ADR-0004 is explicit that jsdom did not catch the
   * defects that mattered and that browser-level acceptance is what evidences rendering.
   * What lives here is pure domain logic — the money rule — where a unit test is the right
   * instrument and a browser is not. Rendering stays in the Playwright suite. */
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },

  build: {
    outDir: "dist",
    sourcemap: true,
    target: "es2022",
    rollupOptions: {
      output: {
        /* Split the router and React runtime out of the app chunk so a view change does not
           re-download the framework. Route-level splitting is done with lazy() in the
           router itself, which is where it belongs. */
        manualChunks: {
          react: ["react", "react-dom"],
          router: ["react-router-dom"],
        },
      },
    },
  },
  /* The dev server proxies /api to the real backend.
   *
   * Not a convenience: it means development and E2E run SAME-ORIGIN, so no CORS entry has
   * to be added for a port that only exists on a developer's machine. The deployed client
   * is cross-origin and configured through VITE_API_BASE_URL at image build, exactly as
   * the classic client was — so this proxy is the dev-only half of one seam, not a second
   * way of reaching the API.
   *
   * DEDUNET_DEV_API points it somewhere else when the backend is not on the default port. */
  server: {
    /* Bind all interfaces rather than the default localhost.
     *
     * On Windows "localhost" resolves to ::1 first, so a dev server bound only to it
     * refuses connections on 127.0.0.1 — which is what Playwright and most tooling reach
     * for. Binding both is the difference between a suite that runs and 126 connection
     * refusals that look like application failures. */
    host: true,
    port: 13600,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.DEDUNET_DEV_API ?? "http://127.0.0.1:18080",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true,
    port: 13600,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.DEDUNET_DEV_API ?? "http://127.0.0.1:18080",
        changeOrigin: true,
      },
    },
  },
});
