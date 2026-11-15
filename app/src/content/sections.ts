// Site sections. One entry per route. The Home solar system reads the `orbit` field of each planet.
// Source of the table and of the codes: docs/plan_t18_website.md §3.1 and §4.2.

export type SectionName =
  | "home"
  | "results"
  | "challenge"
  | "how-it-works"
  | "algorithm"
  | "data"
  | "about";

/** Position of a planet in the solar system drawing (design units, y points down). */
export interface OrbitSpec {
  /** Horizontal and vertical radius of the orbit ellipse. */
  rx: number;
  ry: number;
  /** Angle on the orbit in degrees: x = rx·cos θ, y = ry·sin θ. */
  theta: number;
  /** Planet centre, as listed in the plan's table. */
  x: number;
  y: number;
  /** Tilt of the planet's axis in degrees. Together with `parallels` it is the only planet identity. */
  tilt: number;
  /** Number of horizontal parallels drawn on the planet (1 to 3). Used by the flat fallback drawing. */
  parallels: number;
  /** Which body the planet is drawn as. Earth and Mars take the two inner orbits. */
  body: PlanetBody;
  /** Rotation speed on its own axis, in turns per minute. Each planet has its own. */
  spin: number;
}

export type PlanetBody = "earth" | "mars" | "moon" | "mercury" | "neptune";

export interface SiteSection {
  code: string;
  name: SectionName;
  path: string;
  label: string;
  orbit?: OrbitSpec;
}

export const PROJECT_NAME = "PROTOTERRA";
export const PROJECT_TAGLINE = "Grounded in Earth. Built for beyond.";
export const REPOSITORY_URL = "https://github.com/OwenSolis03/prototerra";

export const SECTIONS: SiteSection[] = [
  { code: "SEC.00", name: "home", path: "/", label: "HOME" },
  { code: "SEC.01", name: "results", path: "/results", label: "RESULTS" },
  {
    code: "SEC.02",
    name: "challenge",
    path: "/challenge",
    label: "CHALLENGE",
    orbit: { rx: 320, ry: 160, theta: 325, x: 262, y: -92, tilt: 25, parallels: 2, body: "mars", spin: 5.8 },
  },
  {
    code: "SEC.03",
    name: "how-it-works",
    path: "/how-it-works",
    label: "HOW IT WORKS",
    orbit: { rx: 240, ry: 120, theta: 215, x: -197, y: -69, tilt: -23, parallels: 1, body: "earth", spin: 6 },
  },
  {
    code: "SEC.04",
    name: "algorithm",
    path: "/algorithm",
    label: "ALGORITHM",
    orbit: { rx: 400, ry: 200, theta: 135, x: -283, y: 141, tilt: 7, parallels: 3, body: "moon", spin: 1.2 },
  },
  {
    code: "SEC.05",
    name: "data",
    path: "/data",
    label: "DATA",
    orbit: { rx: 470, ry: 235, theta: 22, x: 436, y: 88, tilt: -2, parallels: 2, body: "mercury", spin: 0.8 },
  },
  {
    code: "SEC.06",
    name: "about",
    path: "/about",
    label: "ABOUT US",
    orbit: { rx: 540, ry: 270, theta: 160, x: -507, y: 92, tilt: 28, parallels: 1, body: "neptune", spin: 9 },
  },
];

/** The six sections shown in the header and in the mobile section list. */
export const NAV_SECTIONS = SECTIONS.filter((s) => s.name !== "home");

export const sectionByName = (name: SectionName): SiteSection => {
  const found = SECTIONS.find((s) => s.name === name);
  if (!found) throw new Error(`Unknown section: ${name}`);
  return found;
};
