// Click transition for the Home sun (anime.js): an orange disc grows from the sun until it covers the
// whole screen, Results opens underneath, then the disc fades out to reveal it.
import { animate } from "animejs";

const GROW_MS = 800;
const FADE_MS = 600;

/** Plays the transition from the sun's on-screen box. Resolves when the layer is removed. */
export function playSunTransition(sun: DOMRect, onCovered: () => void): Promise<void> {
  const cx = sun.left + sun.width / 2;
  const cy = sun.top + sun.height / 2;
  const d = sun.width;
  // Scale needed for the disc to reach the farthest screen corner.
  const w = window.innerWidth;
  const h = window.innerHeight;
  const reach = Math.max(Math.hypot(cx, cy), Math.hypot(w - cx, cy), Math.hypot(cx, h - cy), Math.hypot(w - cx, h - cy));
  const scale = (reach / (d / 2)) * 1.05;

  const layer = document.createElement("div");
  layer.className = "sun-transition";
  layer.setAttribute("aria-hidden", "true");
  Object.assign(layer.style, { position: "fixed", inset: "0", zIndex: "1000", pointerEvents: "auto" });

  const disc = document.createElement("div");
  Object.assign(disc.style, {
    position: "absolute",
    left: `${cx - d / 2}px`,
    top: `${cy - d / 2}px`,
    width: `${d}px`,
    height: `${d}px`,
    borderRadius: "var(--radius-round)",
    background: "var(--signal)",
  });
  layer.append(disc);
  document.body.append(layer);

  return new Promise((resolve) => {
    animate(disc, {
      scale: [1, scale],
      duration: GROW_MS,
      ease: "inQuad",
      onComplete: () => {
        onCovered();
        animate(layer, {
          opacity: [1, 0],
          duration: FADE_MS,
          delay: 120,
          ease: "outQuad",
          onComplete: () => {
            layer.remove();
            resolve();
          },
        });
      },
    });
  });
}
