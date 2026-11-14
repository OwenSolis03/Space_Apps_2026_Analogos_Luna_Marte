/**
 * Minimal hash router.
 *
 * Hash routing keeps the experience portable: it works on static hosting and
 * from any sub-path without server rewrites. The Home route renders the Solar
 * System; every other known route opens the section panel whose content is
 * still pending.
 */

import { SECTIONS, SECTION_BY_PATH } from './celestialData.js';

const KNOWN_PATHS = new Set(['/', ...SECTIONS.map((section) => section.path)]);

function normalise(rawHash) {
  const raw = rawHash.replace(/^#/, '') || '/';
  let path = raw.startsWith('/') ? raw : `/${raw}`;
  if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
  return path;
}

export class HashRouter {
  constructor(onRoute) {
    this.onRoute = onRoute;
    this.current = null;
    this.handleHashChange = this.handleHashChange.bind(this);
  }

  start() {
    window.addEventListener('hashchange', this.handleHashChange);
    this.resolve(true);
  }

  handleHashChange() {
    this.resolve(false);
  }

  resolve(initial) {
    let path = normalise(window.location.hash);
    if (!KNOWN_PATHS.has(path)) {
      path = '/';
      if (!initial) window.history.replaceState(null, '', '#/');
    }

    const changed = this.current !== path;
    this.current = path;
    if (!changed && initial) {
      this.emit(path);
      return;
    }
    this.emit(path);
  }

  emit(path) {
    this.onRoute({
      path,
      section: SECTION_BY_PATH.get(path) || null,
    });
  }

  navigate(path) {
    const target = `#${path}`;
    if (window.location.hash === target) {
      // Clicking Home while already on Home should still provide feedback.
      this.current = path;
      this.emit(path);
      return;
    }
    window.location.hash = target;
  }
}
