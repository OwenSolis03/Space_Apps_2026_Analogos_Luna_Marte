import { defineConfig } from 'vite';

/**
 * Relative asset paths keep the built site portable: hash routing handles
 * navigation, and `base: './'` lets the same `dist/` run from a sub-directory
 * on any static host (including GitHub Pages) without rewrite rules.
 */
export default defineConfig({
  base: './',
});
