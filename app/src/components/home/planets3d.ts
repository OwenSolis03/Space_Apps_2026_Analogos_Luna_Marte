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

type Palette = Record<"surface" | "raised" | "sunken" | "ink" | "muted" | "graphite" | "signal" | "tint" | "signalInk" | "line" | "faint" | "sea" | "land" | "soil" | "marsRed" | "marsDark" | "marsDust" | "moonGrey" | "moonDark" | "moonRim" | "mercuryBase" | "mercuryDark" | "mercuryLight" | "neptuneDeep" | "neptuneMid" | "neptuneLight", string>;

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
    sea: v("--earth-sea"),
    land: v("--earth-land"),
    soil: v("--earth-soil"),
    marsRed: v("--mars-red"),
    marsDark: v("--mars-dark"),
    marsDust: v("--mars-dust"),
    moonGrey: v("--moon-grey"),
    moonDark: v("--moon-dark"),
    moonRim: v("--moon-rim"),
    mercuryBase: v("--mercury-base"),
    mercuryDark: v("--mercury-dark"),
    mercuryLight: v("--mercury-light"),
    neptuneDeep: v("--neptune-deep"),
    neptuneMid: v("--neptune-mid"),
    neptuneLight: v("--neptune-light"),
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

/** Mars in the logo's reds: rust ground, darker regions, light dust craters and graticule. */
function drawMars(ctx: CanvasRenderingContext2D, p: Palette, rand: () => number) {
  ctx.fillStyle = p.marsRed;
  ctx.fillRect(0, 0, TEX_W, TEX_H);
  const rr = seeded(41);
  for (let i = 0; i < 7; i++) {
    ctx.fillStyle = p.marsDark;
    ctx.beginPath();
    ctx.ellipse(rr() * TEX_W, TEX_H * 0.35 + rr() * TEX_H * 0.35, 30 + rr() * 45, 10 + rr() * 16, rr() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  craters(ctx, rand, 26, 3, 10, p.marsDust);
  graticule(ctx, p.marsDust, 0.6);
}

/** Moon in warm greys: highlands, darker maria, crater rims. */
function drawMoon(ctx: CanvasRenderingContext2D, p: Palette, rand: () => number) {
  ctx.fillStyle = p.moonGrey;
  ctx.fillRect(0, 0, TEX_W, TEX_H);
  const rr = seeded(7);
  for (let i = 0; i < 6; i++) {
    ctx.fillStyle = p.moonDark;
    ctx.beginPath();
    ctx.ellipse(rr() * TEX_W, TEX_H * 0.3 + rr() * TEX_H * 0.4, 18 + rr() * 30, 12 + rr() * 18, rr() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  craters(ctx, rand, 40, 3, 14, p.moonRim);
}

function drawTexture(body: PlanetBody, p: Palette): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = TEX_W;
  canvas.height = TEX_H;
  const ctx = canvas.getContext("2d")!;
  const rand = seeded(body.length * 977 + body.charCodeAt(0));

  if (body === "earth") {
    drawEarth(ctx, p);
  } else if (body === "mars") {
    drawMars(ctx, p, rand);
    // White polar caps (Home only; the three-colour version leaves them out)
    ctx.fillStyle = p.raised;
    ctx.fillRect(0, 0, TEX_W, ly(78));
    ctx.fillRect(0, ly(-80), TEX_W, TEX_H - ly(-80));
  } else if (body === "moon") {
    drawMoon(ctx, p, rand);
  } else if (body === "mercury") {
    ctx.fillStyle = p.mercuryBase;
    ctx.fillRect(0, 0, TEX_W, TEX_H);
    craters(ctx, rand, 90, 2, 9, p.mercuryDark);
    craters(ctx, rand, 12, 10, 18, p.mercuryLight);
  } else {
    // Neptune: blue latitude bands and a dark spot
    const bands = [p.neptuneMid, p.neptuneLight, p.neptuneMid, p.neptuneDeep, p.neptuneMid, p.neptuneLight, p.neptuneMid, p.neptuneDeep, p.neptuneMid];
    const h = TEX_H / bands.length;
    bands.forEach((c, i) => {
      ctx.fillStyle = c;
      ctx.fillRect(0, i * h, TEX_W, h + 1);
    });
    ctx.fillStyle = p.neptuneDeep;
    ctx.beginPath();
    ctx.ellipse(TEX_W * 0.3, TEX_H * 0.6, 26, 12, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  return canvas;
}

/** Earth in three natural colours: blue sea, green land, brown soil (hatching, coastlines, graticule). */
function drawEarth(ctx: CanvasRenderingContext2D, p: Palette) {
  ctx.fillStyle = p.sea;
  ctx.fillRect(0, 0, TEX_W, TEX_H);
  for (const poly of CONTINENTS) {
    const path = new Path2D();
    poly.forEach(([lon, lat], i) => (i === 0 ? path.moveTo(lx(lon), ly(lat)) : path.lineTo(lx(lon), ly(lat))));
    path.closePath();
    ctx.fillStyle = p.land;
    ctx.fill(path);
    hatch(ctx, path, p.soil, 9);
    ctx.strokeStyle = p.soil;
    ctx.lineWidth = 2;
    ctx.stroke(path);
  }
  graticule(ctx, p.sea, 0.8);
}

/**
 * Three-colour versions of Earth, Mars and the Moon (How It Works). Each body uses at most three
 * token colours; the flat shading adds tone but no new hues.
 */
function drawTextureThree(body: PlanetBody, p: Palette): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = TEX_W;
  canvas.height = TEX_H;
  const ctx = canvas.getContext("2d")!;
  const rand = seeded(body.length * 977 + body.charCodeAt(0));

  if (body === "earth") {
    drawEarth(ctx, p);
  } else if (body === "mars") {
    // mars-red (ground), mars-dark (regions), mars-dust (craters, graticule)
    drawMars(ctx, p, rand);
  } else {
    // moon-grey (highlands), moon-dark (maria), moon-rim (crater rims)
    drawMoon(ctx, p, rand);
  }
  return canvas;
}

export interface SceneOptions {
  /** Sphere radius in viewBox units. Default 34 (the Home planets). */
  radius?: number;
  /** Draw the small moon around Earth. Default true. */
  satellite?: boolean;
  /** Light position in scene units (y up). Default: the Home sun, at the centre. */
  lightAt?: [number, number, number];
  /** Use the three-colour textures. Default false. */
  threeColour?: boolean;
  /** Ambient and point-light intensities. Defaults 1.1 and 3.2 (the Home scene). */
  ambient?: number;
  light?: number;
}

const RADIUS = 34;
// The small moon that circles Earth: its size, its distance from Earth's centre, and turns per minute.
const SATELLITE_RADIUS = 8;
const SATELLITE_DISTANCE = 56;
const SATELLITE_TURNS = 3;

/** Builds the scene. Throws if WebGL is unavailable, so the caller can fall back to the flat SVG planets. */
export function createPlanetScene(canvas: HTMLCanvasElement, planets: PlanetSpec[], options: SceneOptions = {}): PlanetScene {
  const radius = options.radius ?? RADIUS;
  const paint = options.threeColour ? drawTextureThree : drawTexture;
  const renderer = new WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearAlpha(0);

  const palette = readPalette();
  const scene = new Scene();
  const camera = new OrthographicCamera(-640, 640, 360, -360, 1, 2000);
  camera.position.set(0, 0, 800);
  camera.lookAt(0, 0, 0);

  // Light comes from the sun at the centre, a little in front of the planets, plus an even ambient.
  scene.add(new AmbientLight(new Color(palette.raised), options.ambient ?? 1.1));
  const sunLight = new PointLight(new Color(palette.raised), options.light ?? 3.2, 0, 0);
  sunLight.position.set(...(options.lightAt ?? [0, 0, 160]));
  scene.add(sunLight);

  const geometry = new SphereGeometry(radius, 20, 14);
  const items = planets.map((p) => {
    const texture = new CanvasTexture(paint(p.body, palette));
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
  const satTexture = new CanvasTexture(paint("moon", palette));
  satTexture.colorSpace = SRGBColorSpace;
  const satMaterial = new MeshLambertMaterial({ map: satTexture, flatShading: true });
  const satOrbit = new Group();
  if (earth && options.satellite !== false) {
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

/**
 * One planet mesh with the Home texture, radius 1 (scale it in the caller). Used by the click
 * transition so the planet that grows looks exactly like the one in the solar system.
 */
export function createPlanetMesh(body: PlanetBody): { mesh: Mesh; dispose: () => void } {
  const texture = new CanvasTexture(drawTexture(body, readPalette()));
  texture.colorSpace = SRGBColorSpace;
  const geometry = new SphereGeometry(1, 28, 20);
  const material = new MeshLambertMaterial({ map: texture, flatShading: true });
  const mesh = new Mesh(geometry, material);
  return {
    mesh,
    dispose() {
      texture.dispose();
      geometry.dispose();
      material.dispose();
    },
  };
}
