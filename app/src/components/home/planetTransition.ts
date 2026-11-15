// Click transition for the Home planets (three.js + anime.js).
// The clicked planet is redrawn on a full-screen layer at the same place and size, starts spinning fast,
// grows until it fills the screen height while moving to the left edge, and then sweeps from left to
// right. A surface-coloured cover hides the Home while the planet grows; the section is opened under the
// cover, and the cover is cut away behind the planet as it sweeps, so the section is revealed left to right.
import { AmbientLight, Color, Group, OrthographicCamera, PointLight, Scene, WebGLRenderer } from "three";
import { createTimeline } from "animejs";
import type { PlanetBody } from "@/content/sections";
import { createPlanetMesh } from "./planets3d";

export interface TransitionOptions {
  body: PlanetBody;
  /** Planet centre and radius on screen, in CSS pixels. */
  start: { x: number; y: number; r: number };
  /** Axis tilt in degrees, as in the solar system. */
  tilt: number;
  /** Called when the planet fills the screen height: open the section here. */
  onCovered: () => void;
}

const GROW_MS = 750;
const SWEEP_MS = 950;

/** Plays the transition. Resolves when the layer is removed. Throws if WebGL is unavailable. */
export function playPlanetTransition(opts: TransitionOptions): Promise<void> {
  const w = window.innerWidth;
  const h = window.innerHeight;

  const layer = document.createElement("div");
  layer.className = "planet-transition";
  layer.setAttribute("aria-hidden", "true");
  Object.assign(layer.style, { position: "fixed", inset: "0", zIndex: "1000", pointerEvents: "auto" });

  const cover = document.createElement("div");
  Object.assign(cover.style, { position: "absolute", inset: "0", background: "var(--surface)", opacity: "0" });

  const canvas = document.createElement("canvas");
  Object.assign(canvas.style, { position: "absolute", inset: "0", width: "100%", height: "100%" });

  layer.append(cover, canvas);
  document.body.append(layer);

  let renderer: WebGLRenderer;
  try {
    renderer = new WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch (e) {
    layer.remove();
    throw e;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  renderer.setClearAlpha(0);

  // Camera in screen pixels; scene y points up, so screen y is negated.
  const camera = new OrthographicCamera(0, w, 0, -h, 1, 8000);
  camera.position.set(0, 0, 4000);

  const css = getComputedStyle(document.documentElement);
  const light = new Color(css.getPropertyValue("--surface-raised").trim());
  const scene = new Scene();
  scene.add(new AmbientLight(light, 1.1));
  const sun = new PointLight(light, 2.6, 0, 0);
  scene.add(sun);

  const { mesh, dispose } = createPlanetMesh(opts.body);
  const pivot = new Group();
  pivot.rotation.z = (-opts.tilt * Math.PI) / 180;
  pivot.rotation.x = 0.35;
  pivot.add(mesh);
  scene.add(pivot);

  // Tweened by anime.js; the render loop reads it every frame.
  const state = { x: opts.start.x, y: opts.start.y, r: opts.start.r, cover: 0, spin: 1.5 };
  let sweeping = false;

  let frame = 0;
  let last = 0;
  const loop = (t: number) => {
    const dt = last ? Math.min((t - last) / 1000, 0.1) : 0;
    last = t;
    mesh.rotation.y += state.spin * Math.PI * 2 * dt; // state.spin is turns per second
    pivot.position.set(state.x, -state.y, 0);
    pivot.scale.setScalar(state.r);
    // Light from the upper left, in front, scaled with the planet so the shading keeps its shape.
    sun.position.set(state.x - state.r * 1.2, -state.y + state.r * 1.2, state.r * 2.5);
    cover.style.opacity = String(state.cover);
    // Everything left of the planet's centre is uncovered while it sweeps.
    cover.style.clipPath = sweeping ? `inset(0 0 0 ${Math.max(0, state.x)}px)` : "none";
    renderer.render(scene, camera);
    frame = requestAnimationFrame(loop);
  };
  frame = requestAnimationFrame(loop);

  const fillR = h / 2;

  return new Promise((resolve) => {
    const finish = () => {
      cancelAnimationFrame(frame);
      dispose();
      renderer.dispose();
      layer.remove();
      resolve();
    };

    createTimeline({ onComplete: finish })
      // Grow to the full screen height while moving to the left edge, spinning faster.
      .add(state, {
        x: fillR,
        y: h / 2,
        r: fillR,
        spin: 3.5,
        duration: GROW_MS,
        ease: "inOutQuad",
        onComplete: () => {
          sweeping = true;
          opts.onCovered();
        },
      })
      .add(state, { cover: 1, duration: GROW_MS * 0.6, ease: "outQuad" }, 0)
      // Sweep left to right, uncovering the section behind the planet.
      .add(state, { x: w + fillR, spin: 2, duration: SWEEP_MS, ease: "inOutCubic" }, GROW_MS);
  });
}
