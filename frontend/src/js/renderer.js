/**
 * Canvas rendering utilities.
 *
 * The Sun follows the technique of the supplied frontend reference:
 * radial-gradient core, additive corona layers, a projected 3D point network,
 * rotating technical rings and drifting sparks. Planets are built with the
 * same Canvas 2D language at a smaller scale, keeping only directional rim
 * lighting and ring systems as body-specific details.
 *
 * No external textures, WebGL context or 3D asset is required.
 */

const TAU = Math.PI * 2;

const planetNetworks = new WeakMap();
const planetSparks = new WeakMap();
const planetSpins = new WeakMap();
let backgroundCache = { key: '', canvas: null };

/* ------------------------------------------------------------------ */
/* Small utilities                                                     */
/* ------------------------------------------------------------------ */

export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function mixAlpha(color, alpha) {
  if (!color) return `rgba(255,255,255,${alpha})`;
  if (color.startsWith('#')) {
    let hex = color.slice(1);
    if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
    const int = Number.parseInt(hex, 16);
    const r = (int >> 16) & 255;
    const g = (int >> 8) & 255;
    const b = int & 255;
    return `rgba(${r},${g},${b},${alpha})`;
  }
  if (color.startsWith('rgba(')) {
    return color.replace(/rgba\(([^)]+)\)/, (_, body) => {
      const parts = body.split(',').map((part) => part.trim());
      parts[3] = String(alpha);
      return `rgba(${parts.slice(0, 4).join(',')})`;
    });
  }
  if (color.startsWith('rgb(')) {
    return color.replace('rgb(', 'rgba(').replace(')', `,${alpha})`);
  }
  return color;
}

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function seedFromString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createCanvas(width, height) {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

/* ------------------------------------------------------------------ */
/* Starfield and background                                            */
/* ------------------------------------------------------------------ */

export function createStarfield(count, width, height) {
  const random = seededRandom(982451653);
  const stars = [];
  const palette = ['#ffffff', '#dbe9ff', '#bcd6ff', '#ffe8c8', '#eaf3ff'];

  for (let i = 0; i < count; i++) {
    const radius = random() * 1.35 + 0.2;
    stars.push({
      x: random() * width,
      y: random() * height,
      r: radius,
      a: random() * 0.68 + 0.18,
      tw: random() * TAU,
      sp: 0.35 + random() * 1.1,
      color: palette[Math.floor(random() * palette.length)],
      spike: radius > 1.08 && random() > 0.62,
    });
  }
  return stars;
}

export function resizeStarfield(stars, width, height) {
  for (const star of stars) {
    if (star.x > width) star.x = Math.random() * width;
    if (star.y > height) star.y = Math.random() * height;
  }
}

function getBackground(width, height, sunX, sunY) {
  const key = `${Math.round(width)}x${Math.round(height)}`;
  if (backgroundCache.key === key && backgroundCache.canvas) return backgroundCache.canvas;

  const canvas = createCanvas(Math.max(1, Math.ceil(width)), Math.max(1, Math.ceil(height)));
  const ctx = canvas.getContext('2d');
  const random = seededRandom(32452843);

  const base = ctx.createRadialGradient(sunX, sunY * 0.92, 0, sunX, sunY, Math.max(width, height) * 0.92);
  base.addColorStop(0, '#0b1430');
  base.addColorStop(0.4, '#050a18');
  base.addColorStop(0.72, '#02050d');
  base.addColorStop(1, '#010207');
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  // Rasputin-style ember atmosphere around the star. It fades into the cold
  // deep-space palette before it reaches the navigation lanes at the edges.
  const warm = ctx.createRadialGradient(
    sunX,
    sunY,
    0,
    sunX,
    sunY,
    Math.max(width, height) * 0.82,
  );
  warm.addColorStop(0, 'rgba(122, 45, 8, 0.72)');
  warm.addColorStop(0.38, 'rgba(74, 25, 12, 0.4)');
  warm.addColorStop(0.68, 'rgba(35, 12, 10, 0.17)');
  warm.addColorStop(1, 'rgba(18, 4, 2, 0)');
  ctx.fillStyle = warm;
  ctx.fillRect(0, 0, width, height);

  // Deep-space nebula fields: very low opacity so the interface stays legible.
  const nebula = [
    ['#2d5cff', 0.085],
    ['#7a43ff', 0.055],
    ['#1d9ca8', 0.05],
    ['#ff6a3d', 0.035],
  ];
  for (let i = 0; i < 13; i++) {
    const [color, alpha] = nebula[i % nebula.length];
    const x = random() * width;
    const y = random() * height;
    const radius = Math.max(width, height) * (0.12 + random() * 0.34);
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, mixAlpha(color, alpha));
    gradient.addColorStop(0.5, mixAlpha(color, alpha * 0.35));
    gradient.addColorStop(1, mixAlpha(color, 0));
    ctx.fillStyle = gradient;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }

  // A faint galactic band placed diagonally behind the system.
  ctx.save();
  ctx.translate(width * 0.5, height * 0.5);
  ctx.rotate(-0.42);
  const band = ctx.createLinearGradient(0, -height * 0.24, 0, height * 0.24);
  band.addColorStop(0, 'rgba(90,125,220,0)');
  band.addColorStop(0.35, 'rgba(110,145,235,0.045)');
  band.addColorStop(0.52, 'rgba(190,210,255,0.06)');
  band.addColorStop(0.7, 'rgba(110,145,235,0.035)');
  band.addColorStop(1, 'rgba(90,125,220,0)');
  ctx.fillStyle = band;
  ctx.fillRect(-width, -height * 0.24, width * 2, height * 0.48);

  for (let i = 0; i < 420; i++) {
    const x = (random() - 0.5) * width * 1.8;
    const y = (random() - 0.5) * height * 0.36;
    const a = random() * 0.07;
    ctx.fillStyle = `rgba(200,220,255,${a})`;
    ctx.beginPath();
    ctx.arc(x, y, random() * 1.2 + 0.2, 0, TAU);
    ctx.fill();
  }
  ctx.restore();

  // Vignette keeps labels readable at the edges of the composition.
  const vignette = ctx.createRadialGradient(
    width * 0.5,
    height * 0.47,
    Math.min(width, height) * 0.22,
    width * 0.5,
    height * 0.47,
    Math.max(width, height) * 0.78,
  );
  vignette.addColorStop(0, 'rgba(0,0,0,0)');
  vignette.addColorStop(0.62, 'rgba(0,2,8,0.18)');
  vignette.addColorStop(1, 'rgba(0,2,8,0.82)');
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, width, height);

  backgroundCache = { key, canvas };
  return canvas;
}

/**
 * The reference sun sits inside a tunnel of slowly rotating, nested squares.
 * It is reproduced verbatim (same sizes, alphas, colors and cadence) so the
 * star keeps the exact Rasputin atmosphere while the rest of the site keeps
 * its deep-space palette.
 */
function drawSolarTunnel(ctx, sunX, sunY, sunRadius, time, width, height, reduceMotion) {
  const t = reduceMotion ? 0 : time;
  const count = 10;
  const maxDimension = Math.max(width, height);

  ctx.save();
  for (let i = 0; i < count; i++) {
    const u = ((i + t * 0.12) % count) / count;
    const size =
      sunRadius * 0.95 + maxDimension * 1.15 * Math.pow(u, 1.7);
    const alpha = Math.min(1, u * 1.8) * (1 - u * 0.2) * 0.6;

    ctx.save();
    ctx.translate(sunX, sunY);
    ctx.rotate(Math.PI / 4 + Math.sin(t * 0.15 + u * 2) * 0.05);

    ctx.lineWidth = 1 + u * 8;
    ctx.strokeStyle = `rgba(255, ${140 + Math.floor(u * 60)}, 50, ${alpha})`;
    ctx.strokeRect(-size, -size, size * 2, size * 2);

    const inner = size * 0.9;
    ctx.lineWidth = 1 + u * 2;
    ctx.strokeStyle = `rgba(255, 205, 120, ${alpha * 0.55})`;
    ctx.strokeRect(-inner, -inner, inner * 2, inner * 2);

    ctx.restore();
  }
  ctx.restore();
}

export function drawBackground(
  ctx,
  width,
  height,
  sunX,
  sunY,
  sunRadius,
  stars,
  time,
  reduceMotion,
) {
  const background = getBackground(width, height, sunX, sunY);
  ctx.drawImage(background, 0, 0, width, height);

  drawSolarTunnel(ctx, sunX, sunY, sunRadius, time, width, height, reduceMotion);

  ctx.save();
  for (const star of stars) {
    const twinkle = reduceMotion ? 1 : 0.58 + 0.42 * Math.sin(time * star.sp + star.tw);
    ctx.globalAlpha = star.a * twinkle;
    ctx.fillStyle = star.color;
    ctx.beginPath();
    ctx.arc(star.x, star.y, star.r, 0, TAU);
    ctx.fill();

    if (star.spike) {
      const length = 2.4 + star.r * 2.4;
      ctx.strokeStyle = mixAlpha(star.color, 0.5);
      ctx.lineWidth = 0.55;
      ctx.beginPath();
      ctx.moveTo(star.x - length, star.y);
      ctx.lineTo(star.x + length, star.y);
      ctx.moveTo(star.x, star.y - length);
      ctx.lineTo(star.x, star.y + length);
      ctx.stroke();
    }
  }
  ctx.restore();
}

/* ------------------------------------------------------------------ */
/* Orbit paths                                                         */
/* ------------------------------------------------------------------ */

export function drawOrbit(ctx, cx, cy, rx, ry, time, active = false, reduceMotion = false) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.strokeStyle = active ? 'rgba(255, 214, 142, 0.55)' : 'rgba(255, 180, 96, 0.1)';
  ctx.lineWidth = active ? 1.2 : 0.8;
  ctx.setLineDash(active ? [2, 6] : [1, 9]);
  ctx.lineDashOffset = active && !reduceMotion ? -time * 22 : 0;
  if (active) {
    ctx.strokeStyle = 'rgba(255, 172, 80, 0.14)';
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.ellipse(0, 0, Math.max(rx, 1), Math.max(ry, 1), 0, 0, TAU);
    ctx.stroke();
    ctx.strokeStyle = active ? 'rgba(255, 214, 142, 0.55)' : 'rgba(255, 180, 96, 0.1)';
    ctx.lineWidth = 1.2;
  }
  ctx.beginPath();
  ctx.ellipse(0, 0, Math.max(rx, 1), Math.max(ry, 1), 0, 0, TAU);
  ctx.stroke();
  ctx.restore();
}

/* ------------------------------------------------------------------ */
/* Sun                                                                 */
/* ------------------------------------------------------------------ */

/**
 * The Sun is a faithful port of the reference implementation in
 * `assets/rasputin-asistente.zip`: the same haze, core gradient, four
 * rotating squares, elliptical arcs, Fibonacci point network, sparks and
 * floating embers. Only the centre and radius are parameterized so the
 * effect can live inside the Solar System composition.
 */
const SUN_NEIGHBOURS = 4;
const sunModel = {
  points: null,
  edges: null,
  sparks: [],
  embers: [],
  angle: 0,
  lastTime: null,
};

function ensureSunModel() {
  if (sunModel.points) return;

  const count = 64;
  const points = [];
  const edges = [];

  for (let i = 0; i < count; i++) {
    const y = 1 - (2 * (i + 0.5)) / count;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const angle = i * 2.399963;
    const jitter = 1 + (Math.random() - 0.5) * 0.2;
    points.push([
      Math.cos(angle) * radius * jitter,
      y * jitter,
      Math.sin(angle) * radius * jitter,
    ]);
  }

  for (let i = 0; i < count; i++) {
    const distances = points
      .map((point, j) => [
        j,
        (point[0] - points[i][0]) ** 2 +
          (point[1] - points[i][1]) ** 2 +
          (point[2] - points[i][2]) ** 2,
      ])
      .sort((a, b) => a[1] - b[1]);

    for (let n = 1; n <= SUN_NEIGHBOURS; n++) {
      const j = distances[n][0];
      if (
        !edges.some(
          (edge) =>
            (edge[0] === i && edge[1] === j) ||
            (edge[0] === j && edge[1] === i),
        )
      ) {
        edges.push([i, j]);
      }
    }
  }

  sunModel.points = points;
  sunModel.edges = edges;
  sunModel.sparks = Array.from({ length: 110 }, () => {
    let x;
    let y;
    let z;
    do {
      x = Math.random() * 2 - 1;
      y = Math.random() * 2 - 1;
      z = Math.random() * 2 - 1;
    } while (x * x + y * y + z * z > 1);

    return {
      x,
      y,
      z,
      vx: (Math.random() - 0.5) * 0.08,
      vy: (Math.random() - 0.5) * 0.08,
      vz: (Math.random() - 0.5) * 0.08,
      a: Math.random() * TAU,
      l: 3 + Math.random() * 10,
      ph: Math.random() * TAU,
    };
  });
  sunModel.embers = Array.from({ length: 50 }, () => ({
    x: Math.random(),
    y: Math.random(),
    v: 0.01 + Math.random() * 0.04,
    s: 0.6 + Math.random() * 1.8,
    ph: Math.random() * TAU,
  }));
}

export function drawSun(ctx, x, y, radius, time, reduceMotion, width, height) {
  ensureSunModel();

  const t = reduceMotion ? 0 : time;
  let dt = 0;

  if (!reduceMotion && sunModel.lastTime !== null && t >= sunModel.lastTime) {
    dt = Math.min(t - sunModel.lastTime, 0.05);
  }
  if (sunModel.lastTime === null || t < sunModel.lastTime) {
    sunModel.angle = 0;
  }
  sunModel.lastTime = t;

  if (dt > 0) {
    sunModel.angle += dt * 0.25;

    for (const spark of sunModel.sparks) {
      spark.x += spark.vx * dt * 3;
      spark.y += spark.vy * dt * 3;
      spark.z += spark.vz * dt * 3;
      if (spark.x * spark.x + spark.y * spark.y + spark.z * spark.z > 1) {
        spark.x *= -0.9;
        spark.y *= -0.9;
        spark.z *= -0.9;
      }
    }

    for (const ember of sunModel.embers) {
      ember.y -= ember.v * dt;
      if (ember.y < -0.02) ember.y = 1.02;
    }
  }

  // The reference gently floats its orb. Keep the same amplitude without
  // accumulating drift, so the Solar System centre stays predictable.
  const cx = x + (reduceMotion ? 0 : Math.sin(t * 0.2) * 6);
  const cy = y + (reduceMotion ? 0 : Math.cos(t * 0.17) * 4);
  const R = radius * (1 + (reduceMotion ? 0 : 0.03 * Math.sin(t * 1.5)));

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  // 1. Broad amber haze.
  let gradient = ctx.createRadialGradient(cx, cy, R * 0.3, cx, cy, R * 2.8);
  gradient.addColorStop(0, 'rgba(255, 120, 40, 0.5)');
  gradient.addColorStop(0.5, 'rgba(200, 40, 10, 0.22)');
  gradient.addColorStop(1, 'rgba(120, 10, 0, 0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(cx - R * 3, cy - R * 3, R * 6, R * 6);

  // 2. Luminous core with the exact reference stops.
  gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.25, 'rgba(255, 236, 170, 0.9)');
  gradient.addColorStop(0.7, 'rgba(255, 170, 60, 0.5)');
  gradient.addColorStop(0.93, 'rgba(255, 150, 40, 0.3)');
  gradient.addColorStop(1, 'rgba(255, 210, 100, 0.6)');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, TAU);
  ctx.fill();

  // 3. Four nested technical frames.
  for (let i = 0; i < 4; i++) {
    const size = R * (1.45 + i * 0.5) * (1 + 0.03 * Math.sin(t * 1.7 + i));
    const alpha = (0.55 - 0.11 * i) * (0.7 + 0.3 * Math.sin(t * 2.3 + i * 1.4));

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(Math.PI / 4);
    ctx.strokeStyle = `rgba(255, 215, 100, ${alpha})`;
    ctx.lineWidth = 3 - i * 0.5;
    ctx.strokeRect(-size, -size, size * 2, size * 2);

    const inner = size * 0.92;
    ctx.strokeStyle = `rgba(255, 240, 170, ${alpha * 0.4})`;
    ctx.lineWidth = 1;
    ctx.strokeRect(-inner, -inner, inner * 2, inner * 2);
    ctx.restore();
  }

  // 4. Two sweeping orbital arcs.
  ctx.strokeStyle = 'rgba(255, 190, 80, 0.35)';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.ellipse(cx, cy, R * 2.6, R * 1.1, t * 0.05, Math.PI * 1.1, Math.PI * 1.9);
  ctx.stroke();
  ctx.beginPath();
  ctx.ellipse(cx, cy, R * 3.2, R * 1.5, -t * 0.04, Math.PI * 1.05, Math.PI * 1.95);
  ctx.stroke();

  // 5. Projected Fibonacci sphere and its nearest-neighbour web.
  const ay = sunModel.angle;
  const ax = 0.5 + Math.sin(t * 0.13) * 0.3;
  const sinAy = Math.sin(ay);
  const cosAy = Math.cos(ay);
  const sinAx = Math.sin(ax);
  const cosAx = Math.cos(ax);

  const project = (point) => {
    const px = point[0] * cosAy + point[2] * sinAy;
    let pz = -point[0] * sinAy + point[2] * cosAy;
    const py = point[1] * cosAx - pz * sinAx;
    pz = point[1] * sinAx + pz * cosAx;
    const factor = 1 + pz * 0.08;
    return [cx + px * R * 1.3 * factor, cy + py * R * 1.3 * factor, pz];
  };

  const projected = sunModel.points.map((point, i) =>
    project([
      point[0] + Math.sin(t * 1.7 + i) * 0.035,
      point[1] + Math.cos(t * 1.3 + i * 1.7) * 0.035,
      point[2] + Math.sin(t * 2.1 + i * 0.7) * 0.035,
    ]),
  );

  ctx.lineWidth = 1;
  for (const edge of sunModel.edges) {
    const a = projected[edge[0]];
    const b = projected[edge[1]];
    const depth = (a[2] + b[2]) / 2;
    const flicker =
      0.45 +
      0.55 *
        Math.abs(
          Math.sin(t * 9 + edge[0] * 3.1 + Math.sin(t * 3 + edge[1]) * 2),
        );
    ctx.strokeStyle = `rgba(255, ${90 + Math.floor(depth * 30)}, 35, ${
      (0.3 + 0.4 * ((depth + 1) / 2)) * flicker
    })`;
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
  }

  ctx.fillStyle = 'rgba(255, 220, 140, 0.9)';
  for (const point of projected) {
    ctx.beginPath();
    ctx.arc(point[0], point[1], 1.2 + (point[2] + 1) * 0.5, 0, TAU);
    ctx.fill();
  }

  // 6. Sparks orbiting inside the sphere.
  for (const spark of sunModel.sparks) {
    const q = project([spark.x * 0.95, spark.y * 0.95, spark.z * 0.95]);
    const twinkle = Math.max(0, Math.sin(t * 5 + spark.ph));
    const length = spark.l * (R / 120);
    ctx.strokeStyle = `rgba(255, ${200 + Math.floor(twinkle * 55)}, 120, ${
      0.25 + 0.75 * twinkle
    })`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(q[0], q[1]);
    ctx.lineTo(q[0] + Math.cos(spark.a) * length, q[1] + Math.sin(spark.a) * length);
    ctx.stroke();
  }

  // 7. Screen-wide embers from the reference.
  for (const ember of sunModel.embers) {
    const alpha = 0.3 + 0.7 * Math.abs(Math.sin(t * 1.3 + ember.ph));
    ctx.fillStyle = `rgba(255, 190, 90, ${alpha})`;
    ctx.beginPath();
    ctx.arc(
      ember.x * width + Math.sin(t * 0.6 + ember.ph) * 8,
      ember.y * height,
      ember.s,
      0,
      TAU,
    );
    ctx.fill();
  }

  ctx.restore();
}

/* ------------------------------------------------------------------ */
/* Planets                                                             */
/* ------------------------------------------------------------------ */

function drawRingPass(ctx, x, y, radius, body, pass, sun) {
  const rings = body.rings;
  if (!rings) return;
  const colors = body.colors;
  const inner = radius * rings.inner;
  const outer = radius * rings.outer;
  const bandWidth = outer - inner;
  const squash = 0.32;
  const backPass = pass === 'back';

  const bands = [
    [inner + bandWidth * 0.18, bandWidth * 0.28, colors.ringInner],
    [inner + bandWidth * 0.52, bandWidth * 0.4, colors.ringMid],
    [inner + bandWidth * 0.84, bandWidth * 0.2, colors.ringOuter],
  ];

  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rings.tilt);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = (rings.opacity ?? 0.85) * (backPass ? 0.5 : 1);

  for (const [bandRadius, width, color] of bands) {
    if (!color) continue;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(0.7, width);
    ctx.beginPath();
    ctx.ellipse(
      0,
      0,
      bandRadius,
      bandRadius * squash,
      0,
      backPass ? Math.PI : 0,
      backPass ? TAU : Math.PI,
    );
    ctx.stroke();
  }

  // Crisp outer edge.
  ctx.globalAlpha *= 0.55;
  ctx.strokeStyle = colors.ringOuter || 'rgba(230, 220, 190, 0.3)';
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.ellipse(
    0,
    0,
    outer,
    outer * squash,
    0,
    backPass ? Math.PI : 0,
    backPass ? TAU : Math.PI,
  );
  ctx.stroke();
  ctx.restore();
}

/**
 * Planets are miniature versions of the reference Sun: a seeded Fibonacci
 * sphere, a nearest-neighbour network, additive gradients, technical frames,
 * sweeping arcs and drifting sparks. Surface textures are intentionally gone;
 * colour, scale, bands and rings carry each body's identity inside one shared
 * visual language.
 */
function getPlanetNetwork(body, count) {
  let cache = planetNetworks.get(body);
  if (!cache) {
    cache = new Map();
    planetNetworks.set(body, cache);
  }

  const cached = cache.get(count);
  if (cached) return cached;

  const random = seededRandom(seedFromString(`${body.id}-network-${count}`));
  const points = [];

  for (let i = 0; i < count; i += 1) {
    const y = 1 - (2 * (i + 0.5)) / count;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const angle = i * 2.399963;
    const jitter = 1 + (random() - 0.5) * 0.18;
    points.push([
      Math.cos(angle) * radius * jitter,
      y * jitter,
      Math.sin(angle) * radius * jitter,
    ]);
  }

  const neighbourCount = Math.min(3, count - 1);
  const edges = [];

  for (let i = 0; i < count; i += 1) {
    const distances = points
      .map((point, j) => [
        j,
        (point[0] - points[i][0]) ** 2 +
          (point[1] - points[i][1]) ** 2 +
          (point[2] - points[i][2]) ** 2,
      ])
      .sort((a, b) => a[1] - b[1]);

    for (let n = 1; n <= neighbourCount; n += 1) {
      const j = distances[n][0];
      if (
        !edges.some(
          (edge) =>
            (edge[0] === i && edge[1] === j) ||
            (edge[0] === j && edge[1] === i),
        )
      ) {
        edges.push([i, j]);
      }
    }
  }

  const network = { points, edges };
  cache.set(count, network);
  return network;
}

function getPlanetSparks(body) {
  let sparks = planetSparks.get(body);
  if (sparks) return sparks;

  const random = seededRandom(seedFromString(`${body.id}-sparks`));
  sparks = Array.from({ length: 8 }, () => ({
    angle: random() * TAU,
    radius: 1.16 + random() * 0.78,
    speed: (random() - 0.5) * 0.26,
    length: 0.12 + random() * 0.18,
    phase: random() * TAU,
    size: 0.6 + random() * 0.7,
  }));
  planetSparks.set(body, sparks);
  return sparks;
}

function getPlanetSpin(body) {
  let spin = planetSpins.get(body);
  if (!spin) {
    const random = seededRandom(seedFromString(`${body.id}-spin`));
    spin = { angle: random() * TAU, lastTime: null };
    planetSpins.set(body, spin);
  }
  return spin;
}

/**
 * Amber atmosphere and sweeping arcs behind the disc, mirroring the Sun's
 * outer haze so every body belongs to the same ember-lit system.
 */
function drawPlanetHalo(ctx, x, y, R, body, time, highlight) {
  const colors = body.colors;
  const light = colors.light || colors.base;
  const boost = highlight ? 1.5 : 1;

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  const haze = ctx.createRadialGradient(x, y, R * 0.45, x, y, R * 2.9);
  haze.addColorStop(0, mixAlpha(light, 0.15 * boost));
  haze.addColorStop(0.45, mixAlpha(colors.base, 0.09 * boost));
  haze.addColorStop(0.8, 'rgba(255, 132, 48, 0.035)');
  haze.addColorStop(1, 'rgba(255, 116, 32, 0)');
  ctx.fillStyle = haze;
  ctx.beginPath();
  ctx.arc(x, y, R * 2.9, 0, TAU);
  ctx.fill();

  ctx.strokeStyle = mixAlpha(light, highlight ? 0.36 : 0.2);
  ctx.lineWidth = Math.max(0.6, R * 0.022);
  ctx.beginPath();
  ctx.ellipse(
    x,
    y,
    R * 2.35,
    R * 1.0,
    time * 0.05 + body.phase,
    Math.PI * 1.12,
    Math.PI * 1.88,
  );
  ctx.stroke();

  ctx.strokeStyle = 'rgba(255, 198, 116, 0.18)';
  ctx.lineWidth = Math.max(0.5, R * 0.018);
  ctx.beginPath();
  ctx.ellipse(
    x,
    y,
    R * 2.95,
    R * 1.32,
    -time * 0.035 + body.phase,
    Math.PI * 1.08,
    Math.PI * 1.92,
  );
  ctx.stroke();

  ctx.restore();
}

/**
 * Additive core with a Sun-like white-hot centre, coloured mid-tones and a
 * luminous limb. The gradient is offset toward the star to keep the existing
 * directional lighting read.
 */
function drawPlanetCore(ctx, x, y, R, body, lx, ly) {
  const colors = body.colors;
  const light = colors.light || colors.base;

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  const core = ctx.createRadialGradient(
    x + lx * R * 0.3,
    y + ly * R * 0.3,
    R * 0.05,
    x,
    y,
    R,
  );
  core.addColorStop(0, mixAlpha(light, 0.58));
  core.addColorStop(0.26, mixAlpha(colors.base, 0.94));
  core.addColorStop(0.7, mixAlpha(colors.base, 0.46));
  core.addColorStop(0.92, mixAlpha(colors.dark, 0.54));
  core.addColorStop(1, mixAlpha(light, 0.26));
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(x, y, R, 0, TAU);
  ctx.fill();

  ctx.restore();
}

/**
 * Faint latitude bands keep gas and ice giants readable without returning to
 * the flat procedural textures the shared language replaces.
 */
function drawPlanetBands(ctx, x, y, R, body, time) {
  const bandCount = body.surface?.bands || 0;
  if (bandCount < 3) return;

  const colors = body.colors;
  const light = colors.light || colors.base;
  const lines = Math.min(4, bandCount - 1);

  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, R, 0, TAU);
  ctx.clip();
  ctx.globalCompositeOperation = 'lighter';

  for (let i = 1; i <= lines; i += 1) {
    const yy =
      y -
      R * 0.62 +
      (i / (lines + 1)) * R * 1.24 +
      Math.sin(time * 0.24 + body.phase + i) * R * 0.03;
    ctx.strokeStyle = mixAlpha(light, 0.07);
    ctx.lineWidth = Math.max(0.7, R * 0.045);
    ctx.beginPath();
    ctx.ellipse(x, yy, R * 0.96, R * 0.13, 0, 0, TAU);
    ctx.stroke();
  }

  ctx.restore();
}

/**
 * Projected Fibonacci sphere and nearest-neighbour web. Point count follows
 * the rendered radius so Mercury does not turn into noise while Jupiter keeps
 * a legible mesh.
 */
function drawPlanetNetwork(ctx, x, y, R, body, time, spin, highlight) {
  const colors = body.colors;
  const light = colors.light || colors.base;
  const count = clamp(Math.round(R * 1.15), 8, 30);
  const { points, edges } = getPlanetNetwork(body, count);

  const ax = 0.45 + Math.sin(time * 0.09 + body.phase) * 0.2;
  const ay = spin.angle;
  const sinAy = Math.sin(ay);
  const cosAy = Math.cos(ay);
  const sinAx = Math.sin(ax);
  const cosAx = Math.cos(ax);
  const scale = R * (1.04 + (highlight ? 0.03 : 0));

  const projected = points.map((point, i) => {
    const wobble = [
      point[0] + Math.sin(time * 1.4 + i) * 0.03,
      point[1] + Math.cos(time * 1.1 + i * 1.3) * 0.03,
      point[2] + Math.sin(time * 1.7 + i * 0.9) * 0.03,
    ];
    const px = wobble[0] * cosAy + wobble[2] * sinAy;
    let pz = -wobble[0] * sinAy + wobble[2] * cosAy;
    const py = wobble[1] * cosAx - pz * sinAx;
    pz = wobble[1] * sinAx + pz * cosAx;
    const factor = 1 + pz * 0.06;
    return [x + px * scale * factor, y + py * scale * factor, pz];
  });

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.lineWidth = Math.max(0.5, R * 0.014);

  for (const edge of edges) {
    const a = projected[edge[0]];
    const b = projected[edge[1]];
    const depth = (a[2] + b[2]) / 2;
    const alpha = (0.14 + 0.44 * ((depth + 1) / 2)) * (highlight ? 1.35 : 1);
    ctx.strokeStyle = mixAlpha(depth > 0 ? light : colors.base, Math.min(0.9, alpha));
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
  }

  ctx.fillStyle = mixAlpha(light, highlight ? 0.88 : 0.68);
  for (const point of projected) {
    ctx.beginPath();
    ctx.arc(
      point[0],
      point[1],
      Math.max(0.45, R * 0.026 * (1 + (point[2] + 1) * 0.35)),
      0,
      TAU,
    );
    ctx.fill();
  }

  ctx.restore();
}

/** Two 45-degree frames, the same gesture used around the reference Sun. */
function drawPlanetFrames(ctx, x, y, R, body, time, highlight) {
  const boost = highlight ? 1.6 : 1;

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  for (let i = 0; i < 2; i += 1) {
    const size =
      R * (1.5 + i * 0.55) * (1 + 0.025 * Math.sin(time * 1.7 + i + body.phase));
    const alpha = (0.26 - i * 0.07) * boost;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(Math.PI / 4);
    ctx.strokeStyle = `rgba(255, 213, 122, ${alpha})`;
    ctx.lineWidth = Math.max(0.6, R * 0.028);
    ctx.strokeRect(-size, -size, size * 2, size * 2);

    const inner = size * 0.92;
    ctx.strokeStyle = `rgba(255, 240, 176, ${alpha * 0.42})`;
    ctx.lineWidth = 0.8;
    ctx.strokeRect(-inner, -inner, inner * 2, inner * 2);
    ctx.restore();
  }

  ctx.restore();
}

/** Gold sparks shared by every body, echoing the Sun's ember debris. */
function drawPlanetSparks(ctx, x, y, R, body, time, highlight) {
  const boost = highlight ? 1.5 : 1;

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  for (const spark of getPlanetSparks(body)) {
    const angle = spark.angle + time * spark.speed;
    const distance = R * (spark.radius + 0.05 * Math.sin(time * 0.9 + spark.phase));
    const px = x + Math.cos(angle) * distance;
    const py = y + Math.sin(angle) * distance * 0.9;
    const twinkle = Math.max(0, Math.sin(time * 3.4 + spark.phase));

    ctx.strokeStyle = `rgba(255, ${196 + Math.floor(twinkle * 55)}, ${
      118 + Math.floor(twinkle * 60)
    }, ${(0.16 + 0.58 * twinkle) * boost})`;
    ctx.lineWidth = Math.max(0.55, R * 0.026);
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(
      px + Math.cos(angle) * R * spark.length,
      py + Math.sin(angle) * R * spark.length,
    );
    ctx.stroke();

    ctx.fillStyle = `rgba(255, 226, 164, ${(0.18 + 0.5 * twinkle) * boost})`;
    ctx.beginPath();
    ctx.arc(px, py, Math.max(0.5, R * 0.034 * spark.size), 0, TAU);
    ctx.fill();
  }

  ctx.restore();
}

/** Coloured atmospheric rim plus the shared gold limb facing the Sun. */
function drawPlanetRim(ctx, x, y, R, body, sun, highlight) {
  const colors = body.colors;
  const light = colors.light || colors.base;
  const toSun = Math.atan2(sun.y - y, sun.x - x);

  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  ctx.strokeStyle = mixAlpha(colors.atmosphere || light, highlight ? 0.36 : 0.2);
  ctx.lineWidth = Math.max(1.1, R * 0.08);
  ctx.beginPath();
  ctx.arc(x, y, Math.max(R - 0.4, 0), toSun - 0.95, toSun + 0.95);
  ctx.stroke();

  ctx.strokeStyle = `rgba(255, 204, 126, ${highlight ? 0.2 : 0.11})`;
  ctx.lineWidth = Math.max(1.4, R * 0.1);
  ctx.beginPath();
  ctx.arc(x, y, Math.max(R - 0.2, 0), toSun - 1.02, toSun + 1.02);
  ctx.stroke();

  ctx.strokeStyle = `rgba(255, 228, 170, ${highlight ? 0.82 : 0.52})`;
  ctx.lineWidth = Math.max(0.7, R * 0.032);
  ctx.beginPath();
  ctx.arc(x, y, Math.max(R - 0.4, 0), toSun - 1.02, toSun + 1.02);
  ctx.stroke();

  ctx.restore();
}

function drawFocusRing(ctx, x, y, radius, time) {
  const pulse = 0.5 + 0.5 * Math.sin(time * 2.6);
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';

  const halo = ctx.createRadialGradient(x, y, radius + 1, x, y, radius + 18);
  halo.addColorStop(0, `rgba(255, 190, 96, ${0.22 + pulse * 0.14})`);
  halo.addColorStop(1, 'rgba(255, 150, 60, 0)');
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(x, y, radius + 18, 0, TAU);
  ctx.fill();

  ctx.strokeStyle = `rgba(255, 224, 160, ${0.56 + pulse * 0.26})`;
  ctx.lineWidth = 1;
  ctx.setLineDash([2.5, 5.5]);
  ctx.lineDashOffset = -time * 16;
  ctx.beginPath();
  ctx.arc(x, y, radius + 7.5, 0, TAU);
  ctx.stroke();

  ctx.setLineDash([]);
  for (let i = 0; i < 4; i++) {
    const angle = (i / 4) * TAU + time * 0.3;
    const inner = radius + 5;
    const outer = radius + 10.5;
    ctx.strokeStyle = 'rgba(255, 236, 190, 0.86)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(angle) * inner, y + Math.sin(angle) * inner);
    ctx.lineTo(x + Math.cos(angle) * outer, y + Math.sin(angle) * outer);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Draw one planet with a cached procedural surface, dynamic light direction
 * from the Sun, atmospheric rim, optional clouds and optional ring system.
 */
export function drawPlanet(ctx, x, y, radius, body, time, reduceMotion, highlight = false, sun = { x: 0, y: 0 }) {
  const R = Math.max(radius, 1) * (highlight ? 1.045 : 1);
  const colors = body.colors;
  const t = reduceMotion ? 0 : time;

  const lightLength = Math.hypot(sun.x - x, sun.y - y) || 1;
  const lx = (sun.x - x) / lightLength;
  const ly = (sun.y - y) / lightLength;

  const spin = getPlanetSpin(body);
  if (!reduceMotion) {
    if (spin.lastTime !== null && time >= spin.lastTime) {
      const dt = Math.min(time - spin.lastTime, 0.05);
      const direction = body.rotationSpeed < 0 ? -1 : 1;
      spin.angle += dt * (0.1 + Math.abs(body.rotationSpeed) * 0.22) * direction;
    }
    spin.lastTime = time;
  } else {
    spin.lastTime = null;
  }

  drawPlanetHalo(ctx, x, y, R, body, t, highlight);

  if (body.rings) drawRingPass(ctx, x, y, R, body, 'back', sun);

  drawPlanetCore(ctx, x, y, R, body, lx, ly);
  drawPlanetBands(ctx, x, y, R, body, t);
  drawPlanetNetwork(ctx, x, y, R, body, t, spin, highlight);
  drawPlanetFrames(ctx, x, y, R, body, t, highlight);
  drawPlanetSparks(ctx, x, y, R, body, t, highlight);
  drawPlanetRim(ctx, x, y, R, body, sun, highlight);

  if (body.rings) drawRingPass(ctx, x, y, R, body, 'front', sun);

  if (highlight) drawFocusRing(ctx, x, y, R, t);
}
