import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const API = "http://127.0.0.1:8017";
const backendProxy = {
  "/api": API,
  "/media": API,
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: backendProxy },
  preview: { proxy: backendProxy },
});
