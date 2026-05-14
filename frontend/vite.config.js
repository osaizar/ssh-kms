import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
      "/get_client": "http://127.0.0.1:5000",
      "/img": "http://127.0.0.1:5000"
    }
  }
});
