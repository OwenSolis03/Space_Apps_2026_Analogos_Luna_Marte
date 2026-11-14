import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base relativa para poder publicar en GitHub Pages sin tocar rutas
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
});
