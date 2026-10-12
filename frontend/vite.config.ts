/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    // Host/Origin stay as 127.0.0.1:5173, which the backend allows (app/core/security.py).
    proxy: { "/api": { target: backend, ws: true } },
    fs: { allow: [".."] }, // shared/ lives one level up
  },
  build: { outDir: "dist", sourcemap: true },
  test: { environment: "jsdom", globals: true },
});
