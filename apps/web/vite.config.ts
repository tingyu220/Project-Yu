import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发时把 /api 代理到本地 Yu API（python -m yu.api，默认 127.0.0.1:8787）。
// 生产构建由 FastAPI 静态托管 apps/web/dist，无需代理。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
