/**
 * Interactive Solar System — application entry point.
 *
 * Responsibilities:
 *  - size the canvas and compute the responsive scene layout;
 *  - drive a single requestAnimationFrame loop;
 *  - draw the background, orbits, Sun, planets and navigation connectors;
 *  - synchronise canvas hit-testing with DOM labels and the router;
 *  - render the pending-section panel for routes that are not built yet.
 */

import {
  BODIES,
  BODY_BY_ID,
  NAV_PLANETS,
  NAV_SECTIONS,
  SECTIONS,
  ROUTE_COPY,
} from './celestialData.js';
import { getLayout, getSceneBodies, getOrbitGeometry, clamp } from './layout.js';
import {
  createStarfield,
  drawBackground,
  drawOrbit,
  drawSun,
  drawPlanet,
} from './renderer.js';
import { NavigationManager } from './navigation.js';
import { HashRouter } from './router.js';

const canvas = document.getElementById('space-canvas');
const context = canvas.getContext('2d', { alpha: false });
const navSvg = document.getElementById('nav-connections');
const navEl = document.getElementById('planet-nav');
const readout = document.getElementById('focus-readout');
const focusName = document.getElementById('focus-name');
const focusMeta = document.getElementById('focus-meta');

const routeView = document.getElementById('route-view');
const routePanel = document.getElementById('route-panel');
const routeEyebrow = document.getElementById('route-eyebrow');
const routeTitle = document.getElementById('route-title');
const routeSummary = document.getElementById('route-summary');
const routeIndex = document.getElementById('route-index');
const routeBack = document.getElementById('route-back');

const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
const reduceMotionQuery = () => motionQuery.matches;

let width = 0;
let height = 0;
let dpr = 1;
let layout = null;
let stars = [];
let sceneBodies = [];
let elapsed = 0;
let reduceMotion = reduceMotionQuery();
let paused = true;
let running = false;
let rafId = 0;
let lastFrame = 0;
let currentPath = '/';
let firstRoute = true;

let canvasHoverId = null;
let navHoverId = null;
let activeNavId = null;
let routeHideTimer = 0;

const navIdSet = new Set(NAV_PLANETS.map((planet) => planet.id));

const navigation = new NavigationManager(navSvg, navEl);

const router = new HashRouter(handleRoute);

/* ------------------------------------------------------------------ */
/* Sizing                                                              */
/* ------------------------------------------------------------------ */

function handleResize() {
  width = Math.max(1, window.innerWidth);
  height = Math.max(1, window.innerHeight);
  dpr = clamp(window.devicePixelRatio || 1, 1, 2);

  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.imageSmoothingEnabled = true;

  layout = getLayout(width, height);
  const starCount = Math.round(clamp((width * height) / 4800, 110, 300));
  stars = createStarfield(starCount, width, height);

  navigation.setLayout(layout);

  if (paused || reduceMotion) render(reduceMotion ? 0 : elapsed);
}

let resizeFrame = 0;
function scheduleResize() {
  window.cancelAnimationFrame(resizeFrame);
  resizeFrame = window.requestAnimationFrame(handleResize);
}

/* ------------------------------------------------------------------ */
/* Rendering                                                           */
/* ------------------------------------------------------------------ */

function render(time) {
  if (!layout) return;

  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);

  const sun = layout.sun;
  drawBackground(context, width, height, sun.x, sun.y, sun.r, stars, time, reduceMotion);

  sceneBodies = getSceneBodies(BODIES, time, layout);
  const planetBodies = sceneBodies.filter((entry) => entry.body.type !== 'star');
  const positions = new Map();

  // Orbits: inactive first, active last so its highlight sits above the rest.
  const ordered = [...planetBodies].sort((a, b) => {
    const aActive = a.body.id === activeNavId ? 1 : 0;
    const bActive = b.body.id === activeNavId ? 1 : 0;
    return aActive - bActive;
  });

  for (const entry of ordered) {
    const { rx, ry } = getOrbitGeometry(entry.body, layout);
    drawOrbit(
      context,
      sun.x,
      sun.y,
      rx,
      ry,
      time,
      entry.body.id === activeNavId,
      reduceMotion,
    );
  }

  drawSun(context, sun.x, sun.y, sun.r, time, reduceMotion, width, height);

  const sorted = [...planetBodies].sort((a, b) => a.y - b.y);
  for (const entry of sorted) {
    positions.set(entry.body.id, { x: entry.x, y: entry.y, r: entry.r });
    drawPlanet(
      context,
      entry.x,
      entry.y,
      entry.r,
      entry.body,
      time,
      reduceMotion,
      entry.body.id === activeNavId,
      sun,
    );
  }

  navigation.update(positions, layout);
}

/* ------------------------------------------------------------------ */
/* Frame loop                                                          */
/* ------------------------------------------------------------------ */

function tick(now) {
  if (!running) return;
  const delta = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;

  if (!reduceMotion) elapsed += delta;
  render(reduceMotion ? 0 : elapsed);

  rafId = window.requestAnimationFrame(tick);
}

function startLoop() {
  if (running || reduceMotion || paused) return;
  running = true;
  lastFrame = performance.now();
  rafId = window.requestAnimationFrame(tick);
}

function stopLoop() {
  running = false;
  window.cancelAnimationFrame(rafId);
}

function refreshPausedState() {
  paused = document.hidden || currentPath !== '/';
  if (paused) stopLoop();
  else startLoop();
}

/* ------------------------------------------------------------------ */
/* Focus / readout                                                     */
/* ------------------------------------------------------------------ */

function updateReadout(id) {
  const body = id ? BODY_BY_ID.get(id) : null;
  readout.classList.toggle('is-active', Boolean(body));

  if (!body) {
    focusName.textContent = 'Solar System';
    focusMeta.textContent = 'Select a planet to navigate';
    return;
  }

  focusName.textContent = body.name;
  focusMeta.textContent = body.nav ? `Navigate to ${body.nav}` : 'No section assigned';
}

function syncFocus() {
  const focusId = navHoverId || canvasHoverId;
  const nextActive = navHoverId || (canvasHoverId && navIdSet.has(canvasHoverId) ? canvasHoverId : null);

  if (nextActive !== activeNavId) {
    activeNavId = nextActive;
    navigation.setActive(activeNavId);
    if (reduceMotion && !paused) render(0);
  }

  updateReadout(focusId);
}

function clearHover() {
  canvasHoverId = null;
  navHoverId = null;
  syncFocus();
  canvas.style.cursor = 'default';
}

/* ------------------------------------------------------------------ */
/* Canvas interaction                                                  */
/* ------------------------------------------------------------------ */

function hitTest(clientX, clientY) {
  let best = null;
  const touch = window.matchMedia('(pointer: coarse)').matches;
  const bonus = touch ? 18 : 10;

  for (const entry of sceneBodies) {
    if (entry.body.type === 'star') continue;
    const distance = Math.hypot(clientX - entry.x, clientY - entry.y);
    const hitRadius = Math.max(entry.r + bonus, touch ? 24 : 16);
    if (distance <= hitRadius && (!best || distance < best.distance)) {
      best = { ...entry, distance };
    }
  }
  return best;
}

function onPointerMove(event) {
  if (event.pointerType === 'touch') return;
  if (currentPath !== '/') return;

  const hit = hitTest(event.clientX, event.clientY);
  if (hit) {
    canvasHoverId = hit.body.id;
    canvas.style.cursor = hit.body.nav ? 'pointer' : 'default';
  } else {
    canvasHoverId = null;
    canvas.style.cursor = 'default';
  }
  syncFocus();
}

function onCanvasClick(event) {
  if (currentPath !== '/') return;
  const hit = hitTest(event.clientX, event.clientY);
  if (!hit || !hit.body.nav) return;
  const route = NAV_SECTIONS[hit.body.nav];
  if (route) router.navigate(route);
}

/* ------------------------------------------------------------------ */
/* Routing / route panel                                               */
/* ------------------------------------------------------------------ */

function buildRouteIndex(path) {
  routeIndex.innerHTML = '';
  for (const section of SECTIONS) {
    const link = document.createElement('a');
    link.href = `#${section.path}`;
    link.className = 'route-index-link';
    link.dataset.route = section.path;
    link.innerHTML = `<span class="route-index-number" aria-hidden="true">${String(section.index).padStart(
      2,
      '0',
    )}</span><span>${section.label}</span>`;
    if (section.path === path) {
      link.classList.add('is-current');
      link.setAttribute('aria-current', 'page');
    }
    link.addEventListener('click', (event) => {
      event.preventDefault();
      router.navigate(section.path);
    });
    routeIndex.appendChild(link);
  }
}

function showRoute(path, section) {
  window.clearTimeout(routeHideTimer);

  const title = section?.label || 'Section';
  const number = section?.index ? String(section.index).padStart(2, '0') : '—';
  const total = String(SECTIONS.length).padStart(2, '0');
  const copy = ROUTE_COPY[path];

  routeEyebrow.textContent = copy?.eyebrow || `Destination ${number} / ${total}`;
  routeTitle.textContent = title;
  routeSummary.textContent =
    copy?.summary ||
    'This section is being prepared. Its content will be connected to the planet navigation once it is ready.';
  buildRouteIndex(path);

  document.body.classList.add('is-route');
  navEl.setAttribute('inert', '');
  navEl.setAttribute('aria-hidden', 'true');

  routeView.hidden = false;
  window.requestAnimationFrame(() => {
    routeView.classList.add('is-open');
    routePanel.focus({ preventScroll: true });
  });
}

function hideRoute() {
  document.body.classList.remove('is-route');
  navEl.removeAttribute('inert');
  navEl.removeAttribute('aria-hidden');
  routeView.classList.remove('is-open');
  window.clearTimeout(routeHideTimer);
  routeHideTimer = window.setTimeout(() => {
    if (currentPath === '/') routeView.hidden = true;
  }, 240);
}

function pulseHome() {
  document.body.classList.remove('is-pulsing');
  // Force a style flush so a repeated click restarts the animation.
  void document.body.offsetWidth;
  document.body.classList.add('is-pulsing');
  window.setTimeout(() => document.body.classList.remove('is-pulsing'), 950);
}

function handleRoute({ path, section }) {
  const wasHome = currentPath === '/';
  currentPath = path;
  navigation.setCurrentRoute(path);

  if (path === '/') {
    if (!wasHome) {
      clearHover();
    } else if (!firstRoute) {
      pulseHome();
    }
    hideRoute();
    refreshPausedState();
    if (reduceMotion) render(0);
  } else {
    showRoute(path, section);
    clearHover();
    refreshPausedState();
    render(elapsed);
  }

  firstRoute = false;
}

/* ------------------------------------------------------------------ */
/* Boot                                                                */
/* ------------------------------------------------------------------ */

function boot() {
  navigation.init(NAV_PLANETS);
  navigation.onHover = (planetId) => {
    navHoverId = planetId;
    syncFocus();
  };
  navigation.onNavigate = (path) => {
    if (path === '/' && currentPath === '/') pulseHome();
    router.navigate(path);
  };

  handleResize();

  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerleave', () => {
    canvasHoverId = null;
    syncFocus();
    canvas.style.cursor = 'default';
  });
  canvas.addEventListener('click', onCanvasClick);

  routeBack.addEventListener('click', (event) => {
    event.preventDefault();
    router.navigate('/');
  });

  window.addEventListener('resize', scheduleResize);
  window.addEventListener('orientationchange', scheduleResize);

  document.addEventListener('visibilitychange', refreshPausedState);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && currentPath !== '/') {
      event.preventDefault();
      router.navigate('/');
    }
  });

  const onMotionChange = (event) => {
    reduceMotion = event.matches;
    if (reduceMotion) {
      stopLoop();
      elapsed = 0;
      render(0);
    } else {
      refreshPausedState();
    }
  };
  if (motionQuery.addEventListener) motionQuery.addEventListener('change', onMotionChange);
  else if (motionQuery.addListener) motionQuery.addListener(onMotionChange);

  router.start();
  refreshPausedState();
  if (reduceMotion) render(0);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
