import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// Relative base: the site can be deployed under any sub-path (GitHub Pages included).
export default defineConfig({
  base: "./",
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  // Lets the Algorithm page import ../pipeline/*.py?raw from the repository root.
  server: { fs: { allow: [".."] } },
});
