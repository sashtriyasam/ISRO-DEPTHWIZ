import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    port: 1420,
    strictPort: false,
  },
  build: {
    target: "es2022",
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      external: ["child_process"],
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}", "electron/**/*.{test,spec}.{ts,tsx}"],
    // Backend-spawning integration tests run real Python subprocesses;
    // the default 5s budget flakes under parallel load.
    testTimeout: 60000,
  },
});
