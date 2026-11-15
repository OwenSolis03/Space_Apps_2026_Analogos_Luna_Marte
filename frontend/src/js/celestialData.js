/**
 * Celestial body and navigation configuration.
 *
 * The Solar System is a navigation interface, not a decorative background.
 * Six planets are assigned to sections; Uranus and Neptune are ambient bodies
 * whose `nav` value is null so a section can be attached later without
 * changing the composition or the renderer.
 *
 * Coordinates are expressed in design units. `layout.js` scales them to the
 * current viewport, which keeps the composition coherent across screen sizes.
 */

export const NAV_SECTIONS = {
  Home: '/',
  'About Us': '/about-us',
  Algorithm: '/algorithm',
  EDA: '/eda',
  Demonstrations: '/demonstrations',
  Challenge: '/challenge',
};

/**
 * Orbital composition.
 *
 * `baseAngle` is measured in degrees on the canvas (0 = right, 90 = down).
 * Navigation planets have a deliberately constrained angular sway: the
 * movement is visible, but it never pushes a planet through a label lane or
 * across another connector. Uranus and Neptune use a wider, slower drift
 * because they have no label to protect.
 *
 * `navSide` and `navRow` define the fixed label lane. The connector geometry
 * is calculated from the live planet position to that lane.
 *
 * Orbit radii are evenly spaced to keep the system legible. Labeled planets
 * read top-to-bottom on each side; Uranus and Neptune close the lower-left and
 * upper-right diagonals so the two ambient bodies complete the composition.
 */
export const BODIES = [
  {
    id: 'sun',
    name: 'Sun',
    type: 'star',
    radius: 62,
    colors: {
      core: '#fffef2',
      inner: '#ffe9a8',
      mid: '#ffb347',
      outer: '#ff6a1f',
      deep: '#c23b08',
      corona: 'rgba(255, 140, 40, 0.45)',
      glow: 'rgba(255, 120, 30, 0.35)',
    },
  },
  {
    id: 'mercury',
    name: 'Mercury',
    nav: 'Home',
    navSide: 'left',
    navRow: 0,
    radius: 6.4,
    orbitRadius: 150,
    baseAngle: 208,
    sway: 4.2,
    swaySpeed: 0.028,
    phase: 0.3,
    rotationSpeed: 0.32,
    colors: {
      base: '#8f8a84',
      light: '#d4cec6',
      dark: '#403c39',
      atmosphere: 'rgba(205, 208, 215, 0.10)',
      bandA: '#7d7771',
      bandB: '#a39d95',
    },
    surface: { kind: 'rocky', craters: true },
  },
  {
    id: 'venus',
    name: 'Venus',
    nav: 'About Us',
    navSide: 'left',
    navRow: 1,
    radius: 10.2,
    orbitRadius: 205,
    baseAngle: 162,
    sway: 3.4,
    swaySpeed: 0.023,
    phase: 1.1,
    rotationSpeed: -0.18,
    colors: {
      base: '#d8a262',
      light: '#ffe0b0',
      dark: '#7d4e22',
      atmosphere: 'rgba(255, 206, 140, 0.22)',
      bandA: '#c78a49',
      bandB: '#edc489',
    },
    surface: { kind: 'clouded', bands: 5 },
  },
  {
    id: 'earth',
    name: 'Earth',
    nav: 'Algorithm',
    navSide: 'right',
    navRow: 0,
    radius: 10.8,
    orbitRadius: 260,
    baseAngle: 338,
    sway: 3.1,
    swaySpeed: 0.02,
    phase: 2.4,
    rotationSpeed: 0.55,
    colors: {
      base: '#1d63c9',
      light: '#8fd3ff',
      dark: '#071c3c',
      atmosphere: 'rgba(110, 185, 255, 0.35)',
      bandA: '#1b57b4',
      bandB: '#2c79dc',
      land: '#3f9f62',
      landAlt: '#9b8b54',
      cloud: 'rgba(244, 250, 255, 0.9)',
      ice: 'rgba(238, 249, 255, 0.92)',
    },
    surface: { kind: 'terrestrial', continents: true, clouds: true, ice: true },
  },
  {
    id: 'mars',
    name: 'Mars',
    nav: 'EDA',
    navSide: 'left',
    navRow: 2,
    radius: 7.8,
    orbitRadius: 315,
    baseAngle: 128,
    sway: 3.5,
    swaySpeed: 0.018,
    phase: 3.3,
    rotationSpeed: 0.5,
    colors: {
      base: '#bf5427',
      light: '#f3a173',
      dark: '#4f1a0b',
      atmosphere: 'rgba(255, 140, 105, 0.16)',
      bandA: '#a8441f',
      bandB: '#d46b3c',
      ice: 'rgba(255, 243, 228, 0.72)',
    },
    surface: { kind: 'rocky', craters: true, darkRegions: true, ice: true },
  },
  {
    id: 'jupiter',
    name: 'Jupiter',
    nav: 'Demonstrations',
    navSide: 'right',
    navRow: 1,
    radius: 23,
    orbitRadius: 372,
    baseAngle: 18,
    sway: 2.5,
    swaySpeed: 0.014,
    phase: 4.1,
    rotationSpeed: 0.7,
    colors: {
      base: '#cfa971',
      light: '#ffe5bb',
      dark: '#674025',
      atmosphere: 'rgba(244, 219, 184, 0.18)',
      bandA: '#a97b4a',
      bandB: '#e4c798',
      storm: 'rgba(176, 91, 53, 0.9)',
    },
    surface: { kind: 'gas', bands: 10, storm: true },
  },
  {
    id: 'saturn',
    name: 'Saturn',
    nav: 'Challenge',
    navSide: 'right',
    navRow: 2,
    radius: 19.5,
    orbitRadius: 430,
    baseAngle: 52,
    sway: 2.4,
    swaySpeed: 0.012,
    phase: 5,
    rotationSpeed: 0.6,
    colors: {
      base: '#d7c184',
      light: '#fff0c7',
      dark: '#69572d',
      atmosphere: 'rgba(248, 232, 180, 0.16)',
      bandA: '#bda15f',
      bandB: '#e8d6a2',
      ringInner: 'rgba(210, 195, 150, 0.16)',
      ringMid: 'rgba(242, 227, 184, 0.68)',
      ringOuter: 'rgba(188, 168, 116, 0.28)',
    },
    surface: { kind: 'gas', bands: 8 },
    rings: { inner: 1.42, outer: 2.35, tilt: 0.38, opacity: 0.9 },
  },
  {
    id: 'uranus',
    name: 'Uranus',
    nav: null,
    radius: 13.4,
    orbitRadius: 486,
    baseAngle: 130,
    sway: 8,
    swaySpeed: 0.009,
    phase: 5.9,
    rotationSpeed: -0.4,
    colors: {
      base: '#6ad3d9',
      light: '#d0fbfd',
      dark: '#1f5c66',
      atmosphere: 'rgba(150, 245, 250, 0.3)',
      bandA: '#55bfc7',
      bandB: '#8de5ea',
      ringMid: 'rgba(170, 245, 250, 0.22)',
      ringOuter: 'rgba(120, 210, 220, 0.1)',
    },
    surface: { kind: 'ice', bands: 4 },
    rings: { inner: 1.55, outer: 1.82, tilt: 1.32, opacity: 0.4 },
  },
  {
    id: 'neptune',
    name: 'Neptune',
    nav: null,
    radius: 13,
    orbitRadius: 542,
    baseAngle: 305,
    sway: 7,
    swaySpeed: 0.008,
    phase: 0.9,
    rotationSpeed: 0.45,
    colors: {
      base: '#2454c6',
      light: '#86b1ff',
      dark: '#081b4d',
      atmosphere: 'rgba(90, 145, 255, 0.32)',
      bandA: '#1c46b3',
      bandB: '#3769dc',
      storm: 'rgba(8, 24, 74, 0.9)',
    },
    surface: { kind: 'ice', bands: 5, storm: true },
  },
];

export const BODY_BY_ID = new Map(BODIES.map((body) => [body.id, body]));
export const PLANETS = BODIES.filter((body) => body.type !== 'star');
export const NAV_PLANETS = PLANETS.filter((planet) => Boolean(planet.nav));

/**
 * Navigation order. Keeping this derived list in one place means the router,
 * the navigation manager and the route overlay always agree on labels.
 */
export const SECTIONS = NAV_PLANETS.map((planet, index) => ({
  index: index + 1,
  label: planet.nav,
  path: NAV_SECTIONS[planet.nav],
  planetId: planet.id,
  planetName: planet.name,
}));

export const SECTION_BY_PATH = new Map(SECTIONS.map((section) => [section.path, section]));

/**
 * Route copy deliberately stays generic: only the Home experience is built.
 * Future sections should replace these strings with real project content.
 */
export const ROUTE_COPY = {
  '/about-us': {
    eyebrow: 'Section 02',
    summary: 'This section is being prepared. Its content will be connected to the planet navigation once it is ready.',
  },
  '/algorithm': {
    eyebrow: 'Section 03',
    summary: 'This section is being prepared. Its content will be connected to the planet navigation once it is ready.',
  },
  '/eda': {
    eyebrow: 'Section 04',
    summary: 'This section is being prepared. Its content will be connected to the planet navigation once it is ready.',
  },
  '/demonstrations': {
    eyebrow: 'Section 05',
    summary: 'This section is being prepared. Its content will be connected to the planet navigation once it is ready.',
  },
  '/challenge': {
    eyebrow: 'Section 06',
    summary: 'This section is being prepared. Its content will be connected to the planet navigation once it is ready.',
  },
};
