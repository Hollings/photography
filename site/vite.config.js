import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],

  // dev‑server settings
  server: {
    host: true,
    port: 5173,
    watch: { usePolling: true },

    // NEW: proxy API calls to FastAPI
    proxy: {
      "/photos": {
        target: backend,
        changeOrigin: true,
      },
      "/photos.json": {
        target: backend,
        changeOrigin: true,
      },
    },
  },
});
