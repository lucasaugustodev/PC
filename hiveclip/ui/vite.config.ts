import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  build: { target: "esnext" },
  optimizeDeps: { esbuildOptions: { target: "esnext" } },
  server: {
    port: 5173,
    proxy: {
      "/api/vnc": { target: "ws://localhost:3100", ws: true, changeOrigin: true },
      "/api/launcher-ws": { target: "ws://localhost:3100", ws: true, changeOrigin: true },
      "/api/launcher": { target: "http://localhost:3100", ws: true, changeOrigin: true },
      "/api": { target: "http://localhost:3100", changeOrigin: true },
    },
  },
});
