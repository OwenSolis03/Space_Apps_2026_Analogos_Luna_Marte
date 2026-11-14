/**
 * Planet-to-section navigation overlay.
 *
 * Each navigation planet receives:
 *   1. a diagonal SVG segment that starts at the planet's lit edge,
 *   2. a horizontal segment that lands in a fixed label lane,
 *   3. an HTML anchor at the end of that horizontal segment.
 *
 * The geometry is recalculated from live planet coordinates, so the connector
 * remains attached while the planet drifts along its orbital arc. In the mobile
 * rail layout the same anchors are reflowed into a two-column list while the
 * canvas remains interactive above it.
 */

import { NAV_SECTIONS } from './celestialData.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export class NavigationManager {
  constructor(svgEl, navEl) {
    this.svg = svgEl;
    this.navEl = navEl;
    this.entries = new Map();
    this.activeId = null;
    this.layout = null;
    this.onNavigate = null;
    this.onHover = null;
  }

  init(navPlanets) {
    this.svg.innerHTML = '';
    this.navEl.innerHTML = '';
    this.entries.clear();

    navPlanets.forEach((planet, index) => {
      const path = document.createElementNS(SVG_NS, 'path');
      path.classList.add('connection-line');
      path.setAttribute('pathLength', '100');
      path.dataset.planetId = planet.id;

      const pulse = document.createElementNS(SVG_NS, 'path');
      pulse.classList.add('connection-pulse');
      pulse.setAttribute('pathLength', '100');
      pulse.dataset.planetId = planet.id;

      const dot = document.createElementNS(SVG_NS, 'circle');
      dot.classList.add('connection-node');
      dot.setAttribute('r', '2.3');
      dot.dataset.planetId = planet.id;

      this.svg.append(path, pulse, dot);

      const route = NAV_SECTIONS[planet.nav] || '/';
      const label = document.createElement('a');
      label.className = 'nav-label';
      label.href = `#${route}`;
      label.dataset.planetId = planet.id;
      label.dataset.side = planet.navSide;
      label.dataset.route = route;
      label.title = `${planet.name} — Navigate to ${planet.nav}`;
      label.setAttribute('aria-label', `Navigate to ${planet.nav}`);
      label.innerHTML = `
        <span class="nav-swatch" aria-hidden="true"></span>
        <span class="nav-rule" aria-hidden="true"></span>
        <span class="nav-text">
          <span class="nav-line">
            <span class="nav-index" aria-hidden="true">${String(index + 1).padStart(2, '0')}</span>
            <span class="nav-title">${planet.nav}</span>
          </span>
          <span class="nav-planet" aria-hidden="true">${planet.name}</span>
        </span>
      `;

      const swatch = label.querySelector('.nav-swatch');
      swatch.style.setProperty('--swatch-light', planet.colors.light || planet.colors.base);
      swatch.style.setProperty('--swatch-base', planet.colors.base);
      swatch.style.setProperty('--swatch-dark', planet.colors.dark || '#101010');
      if (planet.rings) {
        swatch.classList.add('has-rings');
        swatch.style.setProperty('--swatch-ring', planet.colors.ringMid || 'rgba(235, 220, 175, 0.55)');
      }

      const notify = (id) => {
        if (this.onHover) this.onHover(id);
      };
      label.addEventListener('mouseenter', () => notify(planet.id));
      label.addEventListener('mouseleave', () => notify(null));
      label.addEventListener('focus', () => notify(planet.id));
      label.addEventListener('blur', () => notify(null));
      label.addEventListener('click', (event) => {
        event.preventDefault();
        if (this.onNavigate) this.onNavigate(route, planet);
      });

      this.navEl.appendChild(label);
      this.entries.set(planet.id, { path, pulse, dot, label, planet, route });
    });

    this.setActive(null);
  }

  setLayout(layout) {
    this.layout = layout;
    const rail = layout.rail;
    this.navEl.dataset.mode = rail ? 'rail' : 'canvas';
    this.svg.style.display = rail ? 'none' : '';

    if (rail) {
      for (const entry of this.entries.values()) {
        entry.label.style.removeProperty('top');
        entry.label.style.removeProperty('left');
        entry.label.style.removeProperty('right');
      }
    } else {
      this.positionLabels();
    }
  }

  positionLabels() {
    if (!this.layout || this.layout.rail) return;
    const { rows, lanes, width } = this.layout;

    for (const entry of this.entries.values()) {
      const planet = entry.planet;
      const rowY = rows[planet.navRow] ?? rows[1];
      const lane = lanes[planet.navSide];

      entry.label.style.top = `${rowY.toFixed(2)}px`;

      if (planet.navSide === 'left') {
        // The label's right edge sits just before the horizontal line end.
        entry.label.style.left = 'auto';
        entry.label.style.right = `${(width - lane.endX + 10).toFixed(2)}px`;
      } else {
        entry.label.style.left = `${(lane.endX + 10).toFixed(2)}px`;
        entry.label.style.right = 'auto';
      }
    }
  }

  /**
   * @param {Map<string, {x:number,y:number,r:number}>} positions
   * @param {ReturnType<import('./layout.js').getLayout>} layout
   */
  update(positions, layout) {
    if (layout.rail) return;

    for (const entry of this.entries.values()) {
      const pos = positions.get(entry.planet.id);
      if (!pos) continue;

      const rowY = layout.rows[entry.planet.navRow] ?? layout.rows[1];
      const lane = layout.lanes[entry.planet.navSide];
      const elbowX = lane.elbowX;

      const dx = elbowX - pos.x;
      const dy = rowY - pos.y;
      const length = Math.hypot(dx, dy) || 1;
      const edge = pos.r + 3.5;
      const startX = pos.x + (dx / length) * edge;
      const startY = pos.y + (dy / length) * edge;

      const d = `M ${startX.toFixed(2)} ${startY.toFixed(2)} L ${elbowX.toFixed(2)} ${rowY.toFixed(
        2,
      )} L ${lane.endX.toFixed(2)} ${rowY.toFixed(2)}`;

      entry.path.setAttribute('d', d);
      entry.pulse.setAttribute('d', d);
      entry.dot.setAttribute('cx', startX.toFixed(2));
      entry.dot.setAttribute('cy', startY.toFixed(2));
    }
  }

  setActive(planetId) {
    if (this.activeId === planetId) return;
    this.activeId = planetId;

    for (const [id, entry] of this.entries) {
      const active = id === planetId;
      entry.path.classList.toggle('is-active', active);
      entry.pulse.classList.toggle('is-active', active);
      entry.dot.classList.toggle('is-active', active);
      entry.label.classList.toggle('is-active', active);
    }
    this.navEl.classList.toggle('has-active', Boolean(planetId));
  }

  setCurrentRoute(path) {
    for (const entry of this.entries.values()) {
      const current = entry.route === path || (entry.route === '/' && path === '/');
      entry.label.classList.toggle('is-current', current);
      if (current) entry.label.setAttribute('aria-current', 'page');
      else entry.label.removeAttribute('aria-current');
    }
  }
}
