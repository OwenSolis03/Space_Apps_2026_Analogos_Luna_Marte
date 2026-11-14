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
  /** Number of horizontal parallels drawn on the planet (1 to 3). */
  parallels: number;
}

export interface SiteSection {
  code: string;
  name: SectionName;
  path: string;
  label: string;
  orbit?: OrbitSpec;
}

export const PROJECT_NAME = "PLANETARY ANALOG FINDER";
export const REPOSITORY_URL = "https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte";

export const SECTIONS: SiteSection[] = [
  { code: "SEC.00", name: "home", path: "/", label: "HOME" },
  { code: "SEC.01", name: "results", path: "/results", label: "RESULTS" },
  {
    code: "SEC.02",
    name: "challenge",
    path: "/challenge",
    label: "CHALLENGE",
    orbit: { rx: 190, ry: 95, theta: 215, x: -156, y: -54, tilt: -18, parallels: 1 },
  },
  {
    code: "SEC.03",
    name: "how-it-works",
    path: "/how-it-works",
    label: "HOW IT WORKS",
    orbit: { rx: 270, ry: 135, theta: 325, x: 221, y: -77, tilt: 12, parallels: 2 },
  },
  {
    code: "SEC.04",
    name: "algorithm",
    path: "/algorithm",
    label: "ALGORITHM",
    orbit: { rx: 350, ry: 175, theta: 150, x: -303, y: 88, tilt: 24, parallels: 3 },
  },
  {
    code: "SEC.05",
    name: "data",
    path: "/data",
    label: "DATA",
    orbit: { rx: 430, ry: 215, theta: 22, x: 399, y: 81, tilt: -8, parallels: 2 },
  },
  {
    code: "SEC.06",
    name: "about",
    path: "/about",
    label: "ABOUT US",
    orbit: { rx: 510, ry: 255, theta: 197, x: -488, y: -75, tilt: 30, parallels: 1 },
  },
];

/** The six sections shown in the header and in the mobile section list. */
export const NAV_SECTIONS = SECTIONS.filter((s) => s.name !== "home");

export const sectionByName = (name: SectionName): SiteSection => {
  const found = SECTIONS.find((s) => s.name === name);
  if (!found) throw new Error(`Unknown section: ${name}`);
  return found;
};
