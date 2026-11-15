import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Relative base to enable deployment to GitHub Pages without modifying paths
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
});
