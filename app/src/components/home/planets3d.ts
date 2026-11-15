// 3D planets for the Home solar system, drawn with three.js in the RETÍCULA style:
// low-poly spheres, flat shading, line and hatch patterns in the token palette, no glow.
// The canvas uses an orthographic camera mapped to the SVG viewBox, so each sphere sits exactly
// under its SVG link and label. Colours are read from the CSS variables at runtime.
import {
  AmbientLight,
  CanvasTexture,
  Color,
  Group,
  Mesh,
  MeshLambertMaterial,
  OrthographicCamera,
  PointLight,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
  WebGLRenderer,
} from "three";
import type { PlanetBody } from "@/content/sections";

export interface PlanetSpec {
  name: string;
  body: PlanetBody;
  x: number;
  y: number;
  tilt: number;
  /** Turns per minute around the planet's own axis. */
  spin: number;
}

export interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PlanetScene {
  /** Fits the camera to the canvas size and the current viewBox. */
  resize(width: number, height: number, view: ViewBox): void;
  setVisible(names: Set<string>): void;
  /** Starts the render loop; with `still` it draws a single frame. */
  start(still: boolean): void;
  dispose(): void;
  /** For checks: current rotation and position of each planet mesh. */
  probe(): { name: string; rotation: number; x: number; y: number }[];
}

const TEX_W = 512;
const TEX_H = 256;

type Palette = Record<"surface" | "raised" | "sunken" | "ink" | "muted" | "graphite" | "signal" | "tint" | "signalInk" | "line" | "faint", string>;

function readPalette(): Palette {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    surface: v("--surface"),
    raised: v("--surface-raised"),
    sunken: v("--surface-sunken"),
    ink: v("--ink"),
    muted: v("--ink-muted"),
    graphite: v("--graphite"),
    signal: v("--signal"),
    tint: v("--signal-tint"),
    signalInk: v("--signal-ink"),
    line: v("--line"),
    faint: v("--line-faint"),
  };
}

/** Deterministic pseudo-random numbers, so each planet always looks the same. */
function seeded(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// Equirectangular helpers: longitude -180..180 → x, latitude 90..-90 → y.
const lx = (lon: number) => ((lon + 180) / 360) * TEX_W;
const ly = (lat: number) => ((90 - lat) / 180) * TEX_H;

function graticule(ctx: CanvasRenderingContext2D, color: string, width: number) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  for (let lon = -180; lon <= 180; lon += 30) {
    ctx.beginPath();
    ctx.moveTo(lx(lon), 0);
    ctx.lineTo(lx(lon), TEX_H);
    ctx.stroke();
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    ctx.beginPath();
    ctx.moveTo(0, ly(lat));
    ctx.lineTo(TEX_W, ly(lat));
    ctx.stroke();
  }
}

function craters(ctx: CanvasRenderingContext2D, rand: () => number, n: number, rMin: number, rMax: number, color: string, fill?: string) {
  for (let i = 0; i < n; i++) {
    const x = rand() * TEX_W;
    const y = TEX_H * 0.12 + rand() * TEX_H * 0.76;
    const r = rMin + rand() * (rMax - rMin);
    ctx.beginPath();
    ctx.ellipse(x, y, r, r * 0.9, 0, 0, Math.PI * 2);
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

/** Fills a region with diagonal hatching, clipped to the given path. */
function hatch(ctx: CanvasRenderingContext2D, path: Path2D, color: string, pitch = 6) {
  ctx.save();
  ctx.clip(path);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  for (let x = -TEX_H; x < TEX_W; x += pitch) {
    ctx.beginPath();
    ctx.moveTo(x, TEX_H);
    ctx.lineTo(x + TEX_H, 0);
    ctx.stroke();
  }
  ctx.restore();
}

// Very coarse continent outlines (lon, lat), only to make Earth read as Earth at 50 px.
const CONTINENTS: [number, number][][] = [
  // North America
  [[-165, 65], [-140, 70], [-95, 72], [-75, 62], [-60, 50], [-80, 30], [-97, 18], [-105, 22], [-118, 33], [-125, 48], [-150, 58]],
  // South America
  [[-80, 10], [-62, 10], [-35, -6], [-40, -22], [-58, -38], [-70, -55], [-75, -40], [-81, -5]],
  // Africa
  [[-17, 20], [-5, 35], [12, 37], [33, 31], [43, 12], [51, 11], [40, -15], [20, -35], [12, -18], [8, 4], [-8, 4]],
  // Eurasia
  [[-10, 36], [-9, 44], [0, 50], [10, 58], [30, 70], [70, 73], [110, 75], [140, 70], [170, 66], [140, 50], [122, 30], [108, 20], [100, 8], [80, 8], [72, 20], [56, 25], [35, 36], [25, 40], [10, 44]],
  // Australia
  [[114, -22], [130, -12], [142, -11], [153, -27], [146, -39], [130, -32], [115, -34]],
];

function drawTexture(body: PlanetBody, p: Palette): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = TEX_W;
  canvas.height = TEX_H;
  const ctx = canvas.getContext("2d")!;
  const rand = seeded(body.length * 977 + body.charCodeAt(0));

  if (body === "earth") {
    ctx.fillStyle = p.raised;
    ctx.fillRect(0, 0, TEX_W, TEX_H);
    for (const poly of CONTINENTS) {
      const path = new Path2D();
      poly.forEach(([lon, lat], i) => (i === 0 ? path.moveTo(lx(lon), ly(lat)) : path.lineTo(lx(lon), ly(lat))));
      path.closePath();
      ctx.fillStyle = p.sunken;
      ctx.fill(path);
      hatch(ctx, path, p.graphite);
      ctx.strokeStyle = p.ink;
      ctx.lineWidth = 2;
      ctx.stroke(path);
    }
    // Polar ice as flat bands
    ctx.fillStyle = p.raised;
    ctx.fillRect(0, 0, TEX_W, ly(75));
    ctx.fillRect(0, ly(-68), TEX_W, TEX_H - ly(-68));
    ctx.strokeStyle = p.ink;
    ctx.lineWidth = 2;
    [75, -68].forEach((lat) => {
      ctx.beginPath();
      ctx.moveTo(0, ly(lat));
      ctx.lineTo(TEX_W, ly(lat));
      ctx.stroke();
    });
    graticule(ctx, p.line, 1);
  } else if (body === "mars") {
    ctx.fillStyle = p.tint;
    ctx.fillRect(0, 0, TEX_W, TEX_H);
    // Dark albedo regions as signal-coloured patches
    const rr = seeded(41);
    for (let i = 0; i < 7; i++) {
      ctx.fillStyle = p.signal;
      ctx.beginPath();
      ctx.ellipse(rr() * TEX_W, TEX_H * 0.35 + rr() * TEX_H * 0.35, 30 + rr() * 45, 10 + rr() * 16, rr() * Math.PI, 0, Math.PI * 2);
      ctx.fill();
    }
    craters(ctx, rand, 26, 3, 10, p.signalInk);
    ctx.fillStyle = p.raised;
    ctx.fillRect(0, 0, TEX_W, ly(78));
    ctx.fillRect(0, ly(-80), TEX_W, TEX_H - ly(-80));
    graticule(ctx, p.signalInk, 0.6);
  } else if (body === "moon") {
    ctx.fillStyle = p.sunken;
    ctx.fillRect(0, 0, TEX_W, TEX_H);
    const rr = seeded(7);
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = p.graphite;
      ctx.beginPath();
      ctx.ellipse(rr() * TEX_W, TEX_H * 0.3 + rr() * TEX_H * 0.4, 18 + rr() * 30, 12 + rr() * 18, rr() * Math.PI, 0, Math.PI * 2);
      ctx.fill();
    }
    craters(ctx, rand, 40, 3, 14, p.muted);
  } else if (body === "mercury") {
    ctx.fillStyle = p.graphite;
    ctx.fillRect(0, 0, TEX_W, TEX_H);
    craters(ctx, rand, 90, 2, 9, p.sunken);
    craters(ctx, rand, 12, 10, 18, p.faint);
  } else {
    // Neptune: flat latitude bands
    const bands = [p.raised, p.faint, p.raised, p.sunken, p.raised, p.faint, p.raised, p.line, p.raised];
    const h = TEX_H / bands.length;
    bands.forEach((c, i) => {
      ctx.fillStyle = c;
      ctx.fillRect(0, i * h, TEX_W, h + 1);
    });
    ctx.fillStyle = p.graphite;
    ctx.beginPath();
    ctx.ellipse(TEX_W * 0.3, TEX_H * 0.6, 26, 12, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  return canvas;
}

const RADIUS = 34;
// The small moon that circles Earth: its size, its distance from Earth's centre, and turns per minute.
const SATELLITE_RADIUS = 8;
const SATELLITE_DISTANCE = 56;
const SATELLITE_TURNS = 3;

/** Builds the scene. Throws if WebGL is unavailable, so the caller can fall back to the flat SVG planets. */
export function createPlanetScene(canvas: HTMLCanvasElement, planets: PlanetSpec[]): PlanetScene {
  const renderer = new WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearAlpha(0);

  const palette = readPalette();
  const scene = new Scene();
  const camera = new OrthographicCamera(-640, 640, 360, -360, 1, 2000);
  camera.position.set(0, 0, 800);
  camera.lookAt(0, 0, 0);

  // Light comes from the sun at the centre, a little in front of the planets, plus an even ambient.
  scene.add(new AmbientLight(new Color(palette.raised), 1.1));
  const sunLight = new PointLight(new Color(palette.raised), 3.2, 0, 0);
  sunLight.position.set(0, 0, 160);
  scene.add(sunLight);

  const geometry = new SphereGeometry(RADIUS, 20, 14);
  const items = planets.map((p) => {
    const texture = new CanvasTexture(drawTexture(p.body, palette));
    texture.colorSpace = SRGBColorSpace;
    const material = new MeshLambertMaterial({ map: texture, flatShading: true });
    const mesh = new Mesh(geometry, material);
    const pivot = new Group();
    // SVG y points down and three.js y points up; tilt is drawn the same way as in the SVG.
    pivot.position.set(p.x, -p.y, 0);
    pivot.rotation.z = (-p.tilt * Math.PI) / 180;
    pivot.rotation.x = 0.35;
    pivot.add(mesh);
    scene.add(pivot);
    mesh.rotation.y = (p.name.length * 0.7) % (Math.PI * 2);
    return { spec: p, mesh, pivot, texture, material };
  });

  // A small moon circles Earth. Its orbit is tilted towards the camera, so it passes in front of
  // Earth and behind it (hidden by the depth test).
  const earth = items.find((it) => it.spec.body === "earth");
  const satGeometry = new SphereGeometry(SATELLITE_RADIUS, 12, 8);
  const satTexture = new CanvasTexture(drawTexture("moon", palette));
  satTexture.colorSpace = SRGBColorSpace;
  const satMaterial = new MeshLambertMaterial({ map: satTexture, flatShading: true });
  const satOrbit = new Group();
  if (earth) {
    satOrbit.position.copy(earth.pivot.position);
    satOrbit.rotation.x = 0.45;
    satOrbit.rotation.z = -0.2;
    const satellite = new Mesh(satGeometry, satMaterial);
    satellite.position.set(SATELLITE_DISTANCE, 0, 0);
    satOrbit.add(satellite);
    satOrbit.rotation.y = 0.8;
    scene.add(satOrbit);
  }

  let frame = 0;
  let last = 0;

  const render = () => renderer.render(scene, camera);

  const loop = (t: number) => {
    const dt = last ? Math.min((t - last) / 1000, 0.1) : 0;
    last = t;
    for (const it of items) it.mesh.rotation.y += ((it.spec.spin * Math.PI * 2) / 60) * dt;
    satOrbit.rotation.y += ((SATELLITE_TURNS * Math.PI * 2) / 60) * dt;
    render();
    frame = requestAnimationFrame(loop);
  };

  return {
    resize(width, height, view) {
      if (width <= 0 || height <= 0) return;
      renderer.setSize(width, height, false);
      // Same fit as the SVG's preserveAspectRatio="xMidYMid meet".
      const scale = Math.min(width / view.w, height / view.h);
      const halfW = width / scale / 2;
      const halfH = height / scale / 2;
      const cx = view.x + view.w / 2;
      const cy = -(view.y + view.h / 2);
      camera.left = cx - halfW;
      camera.right = cx + halfW;
      camera.top = cy + halfH;
      camera.bottom = cy - halfH;
      camera.updateProjectionMatrix();
      render();
    },
    setVisible(names) {
      for (const it of items) it.pivot.visible = names.has(it.spec.name);
      satOrbit.visible = earth ? names.has(earth.spec.name) : false;
      render();
    },
    start(still) {
      cancelAnimationFrame(frame);
      if (still) {
        render();
        return;
      }
      last = 0;
      frame = requestAnimationFrame(loop);
    },
    dispose() {
      cancelAnimationFrame(frame);
      for (const it of items) {
        it.texture.dispose();
        it.material.dispose();
      }
      geometry.dispose();
      satGeometry.dispose();
      satTexture.dispose();
      satMaterial.dispose();
      renderer.dispose();
    },
    probe() {
      const planetsNow = items.map((it) => ({ name: it.spec.name, rotation: it.mesh.rotation.y, x: it.pivot.position.x, y: -it.pivot.position.y }));
      return [...planetsNow, { name: "earth-moon", rotation: satOrbit.rotation.y, x: satOrbit.position.x, y: -satOrbit.position.y }];
    },
  };
}
