/**
 * Responsive orbital composition.
 *
 * The layout is intentionally computed in JavaScript rather than baked into
 * CSS. Planet coordinates, label lanes and SVG connector geometry must agree
 * on every frame; a single source of truth prevents drift between the canvas
 * and the DOM overlay.
 */

const DESIGN_MAX_ORBIT = 562;
export const ORBIT_SQUASH = 0.52;
const DEG = Math.PI / 180;

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

/**
 * @param {number} width  viewport width in CSS pixels
 * @param {number} height viewport height in CSS pixels
 */
export function getLayout(width, height) {
  const compactPortrait = width < 700 && height >= 620;

  if (compactPortrait) {
    const orbitScale = clamp((width * 0.94) / (2 * DESIGN_MAX_ORBIT), 0.2, 0.52);
    return {
      mode: 'mobile',
      rail: true,
      width,
      height,
      orbitScale,
      orbitSquash: 0.66,
      planetScale: 0.9,
      sun: { x: width * 0.5, y: height * 0.44, r: 62 * 0.44 },
      rows: [height * 0.24, height * 0.5, height * 0.76],
      lanes: {
        left: { endX: 0, elbowX: 0 },
        right: { endX: 0, elbowX: 0 },
      },
      margin: 16,
    };
  }

  const orbitScale = clamp(
    Math.min(
      (width * 0.72) / (2 * DESIGN_MAX_ORBIT),
      (height * 0.64) / (2 * DESIGN_MAX_ORBIT * ORBIT_SQUASH),
    ),
    0.3,
    1.05,
  );

  const margin = width < 900 ? 18 : 28;
  const leftColumn = clamp(width * 0.12, 96, 160);
  const rightColumn = clamp(width * 0.145, 132, 172);
  const leftEnd = margin + leftColumn + 10;
  const rightEnd = width - margin - rightColumn - 10;
  const leftElbow = width * 0.265;
  const rightElbow = width * 0.735;

  const mode = width < 1000 ? 'tablet' : width < 1320 ? 'laptop' : 'desktop';

  return {
    mode,
    rail: false,
    width,
    height,
    orbitScale,
    orbitSquash: ORBIT_SQUASH,
    planetScale: clamp(orbitScale * 1.18, 0.74, 1.06),
    sun: { x: width * 0.5, y: height * 0.5, r: 62 * clamp(orbitScale * 1.05, 0.55, 1) },
    rows: [height * 0.235, height * 0.5, height * 0.765],
    lanes: {
      left: { endX: leftEnd, elbowX: leftElbow },
      right: { endX: rightEnd, elbowX: rightElbow },
    },
    margin,
  };
}

export function getOrbitGeometry(body, layout) {
  const rx = body.orbitRadius * layout.orbitScale;
  return { rx, ry: rx * (layout.orbitSquash ?? ORBIT_SQUASH) };
}

export function getAngle(body, time) {
  const base = body.baseAngle * DEG;
  const sway = body.sway * DEG;
  const primary = Math.sin(time * body.swaySpeed + body.phase) * sway;
  const secondary =
    Math.sin(time * body.swaySpeed * 1.73 + body.phase * 2.1) * sway * 0.28;
  return base + primary + secondary;
}

/**
 * Screen-space position for one body at a given time.
 */
export function getBodyPosition(body, time, layout) {
  if (body.type === 'star') {
    return {
      x: layout.sun.x,
      y: layout.sun.y,
      r: layout.sun.r,
      depth: layout.sun.y,
      angle: 0,
    };
  }

  const { rx, ry } = getOrbitGeometry(body, layout);
  const angle = getAngle(body, time);
  return {
    x: layout.sun.x + Math.cos(angle) * rx,
    y: layout.sun.y + Math.sin(angle) * ry,
    r: body.radius * layout.planetScale,
    depth: layout.sun.y + Math.sin(angle) * ry,
    angle,
  };
}

/**
 * All bodies with their current geometry. The renderer sorts this list by
 * depth so foreground planets overlap background planets convincingly.
 */
export function getSceneBodies(bodies, time, layout) {
  return bodies.map((body) => ({
    body,
    ...getBodyPosition(body, time, layout),
  }));
}
