# Project Context: Interactive Solar System Homepage

## A. Project Overview

### Project Purpose
Build an immersive, interactive web experience where a procedurally rendered Solar System acts as the primary interface and navigation system for the website.

### General Concept
The homepage presents the Sun and all eight planets as animated celestial bodies on a deep-space Canvas 2D scene. Six planets are navigation points connected to labeled sections by SVG leaders made of a diagonal segment followed by a horizontal segment. Hovering a planet, its leader, or its label highlights all three; clicking routes to the matching section.

### Main Objectives
- Reuse and extend the Canvas 2D Sun technique from the provided reference (`assets/rasputin-asistente.zip`).
- Render the Sun plus Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune with distinct visual identities.
- Provide planet navigation for Home, About Us, Algorithm, EDA, Demonstrations and Challenge.
- Keep Uranus and Neptune visible and animated without labels so navigation can be assigned later.
- Deliver a responsive composition that reorganizes intentionally on phone portrait screens instead of scaling everything down.
- Document the real architecture, setup and next steps in this file.

### Development Stage
The Solar System homepage, navigation, hash routing, responsive layouts and reduced-motion handling are implemented. Only the Home experience is built; every other route intentionally shows a "module pending" panel rather than invented section content.

## B. Technology Stack

### Frontend Framework
None. The project is vanilla HTML, CSS and JavaScript (ES modules), preserving the starter architecture.

### Languages
- HTML5
- CSS3
- JavaScript (ES modules)

### Rendering Technologies
- HTML5 Canvas 2D for the starfield, nebula, orbit guides, Sun and planets.
- SVG for navigation leaders, endpoint nodes and animated pulses.
- DOM and CSS for labels, HUD chrome and the route panel.

### Animation
- No animation library. A single `requestAnimationFrame` loop advances time and redraws the canvas.
- Motion is time-based and frame-rate independent (delta capped at 50 ms).
- `prefers-reduced-motion` freezes orbital motion and renders a clean static frame.

### Styling
Plain CSS in `src/css/styles.css`, using custom properties, media queries, `:focus-visible`, and reduced-motion rules.

### Dependencies and Build Tools
- `vite` 8.3.8 is the only dependency (development).
- `vite.config.js` sets `base: './'`, so the built site can be served from a sub-directory without rewrite rules.
- npm scripts:
  - `npm run dev` starts Vite with `--host 0.0.0.0`.
  - `npm run build` writes a production bundle to `dist/`.
  - `npm run preview` serves the built bundle.
- No runtime dependencies. No WebGL, Three.js, 3D models or external image assets are used for the scene.
- No environment variables are required.

## C. Project Architecture

### Directory Structure
```text
.
├── assets/
│   └── rasputin-asistente.zip        # Provided reference for the original Sun canvas effect
├── src/
│   ├── css/
│   │   └── styles.css                # Tokens, stage, labels, HUD, route panel, responsive rules
│   └── js/
│       ├── celestialData.js          # Bodies, palettes, orbits, nav assignments, route copy
│       ├── layout.js                 # Responsive geometry: scale, lanes, rows, positions
│       ├── renderer.js               # Canvas 2D background, orbits, Sun, planets, rings
│       ├── navigation.js             # SVG leaders, labels, hover state, mobile rail
│       ├── router.js                 # Hash router for `#/...` paths
│       └── main.js                   # Bootstrap, loop, hit testing, routing UI
├── index.html                        # Entry document and overlay markup
├── package.json
├── start.sh                          # Convenience launcher for the Vite dev server
├── vite.config.js                    # Relative base for sub-path static hosting
├── context.md                        # This document
└── dist/                             # Generated build output (not source)
```

### Responsibilities
- `index.html`: canvas, SVG overlay, navigation container, HUD, route panel, module entry.
- `celestialData.js`: single source of truth for body properties, orbital parameters, navigation mapping, section order and generic route copy.
- `layout.js`: converts viewport size into orbit scale, orbit squash, Sun size, label rows/lanes and body coordinates. Canvas and DOM geometry share this module so they cannot drift apart.
- `renderer.js`: all drawing. Planet point networks and surface bands are generated deterministically per body; nothing is loaded from disk.
- `navigation.js`: creates the six labels and SVG paths, positions labels in fixed lanes, recomputes leader geometry every frame from live planet coordinates, and exposes hover/current-route state.
- `router.js`: normalizes `#/...` hashes, rejects unknown paths to `/`, and emits `{ path, section }`.
- `main.js`: sizes canvas with DPR clamping, owns the animation loop, performs hit testing, synchronizes hover state, renders the pending-route panel and handles lifecycle events.

### Rendering Order
Each animated frame:
1. Cached deep-space background: base gradient, warm ember wash around the Sun, nebula fields, galactic band and vignette.
2. The reference Sun tunnel: ten nested, rotating 45° square frames expanding from the star to the viewport edges.
3. Twinkling starfield above the tunnel.
4. Orbit guides, with the active section's orbit drawn last.
5. The Sun: amber haze, reference core gradient, four nested technical frames, two sweeping ellipses, projected 64-point sphere network, sparks and screen-wide embers.
6. Planets sorted by screen `y` so nearer bodies overlap farther ones; each body draws an additive orb, a projected point network, technical frames, sparks and a Sun-facing rim, and Saturn/Uranus rings split into back/front passes.
7. Navigation leaders and labels (DOM/SVG) are updated from the final planet positions.

### Architecture Notes
- The canvas is the visual layer; labels and leaders are accessible DOM/SVG elements, so navigation works with keyboard and assistive technology.
- Planet positions are the shared contract between renderer, navigation and hit testing.
- Navigation planets have constrained orbital sway so leaders and labels remain stable. Uranus and Neptune drift more widely because no label depends on them.

## D. Solar System Implementation

### Sun Rendering
`drawSun` is a faithful port of the Sun from `assets/rasputin-asistente.zip`. It keeps the reference's exact layer order, colors, counts and motion, and only parameterizes the centre, radius and viewport size:

1. Broad amber haze: radial gradient from `rgba(255,120,40,0.5)` to transparent, painted additively over a square around the star.
2. Luminous core: the reference's five gradient stops (white → warm cream → amber → orange → gold edge) drawn on the solar disc.
3. Four nested 45° technical frames, each with a thinner inner outline, pulsing alpha and slight scale breathing.
4. Two sweeping elliptical arcs rotating in opposite directions.
5. A 64-point Fibonacci sphere projected in 3D, with each point connected to its four nearest neighbours; the web flickers per edge and rotates over time.
6. 110 drifting sparks confined to the sphere volume, each drawn as a short radial streak.
7. 50 screen-wide embers that rise and twinkle across the whole canvas.

All motion is delta-time based and capped at 50 ms. The star floats gently around `layout.sun` without accumulating drift, so orbits, leaders and hit testing stay aligned. Under reduced motion time is pinned, sparks/embers freeze and the core remains fully drawn.

### Original Reference Adaptation
The reference was a self-contained canvas animation inside a single HTML file. Its Sun was ported rather than approximated:

- The same haze/core gradient stops, four 45° frames, two ellipses, 64 sphere points, nearest-4 edge generation, 110 sparks and 50 embers.
- Random geometry is generated once and reused, instead of being rebuilt every frame.
- The original orb centre and size are replaced by `layout.sun` and `layout.sun.r`; the floating offsets and pulse remain.
- The reference background tunnel is reproduced in `drawSolarTunnel` with the same nested-square cadence, sizes, line weights and amber colors, and integrated into `drawBackground` before the starfield and orbits.
- Nothing in the port uses images, WebGL or an external animation library.

### Planet Rendering
`drawPlanet` now reuses the Sun's technique instead of a flat textured disc:
- A seeded Fibonacci sphere is projected in 3D and rotated at a per-body speed. Each point is connected to its three nearest neighbours, producing the same technical network as the Sun.
- The point count adapts to the rendered radius (`clamp(round(R * 1.15), 8, 30)`) so Mercury stays legible and Jupiter keeps a visible mesh.
- The core is an additive radial gradient tinted by the body palette: light centre, saturated mid-tones, dark limb and a luminous edge.
- A warm amber haze and two sweeping elliptical arcs sit behind the disc.
- Two 45° technical frames, eight gold sparks and a two-pass gold rim face the Sun.
- Gas and ice giants get four faint latitude bands clipped to the disc for identity; terrestrial and rocky bodies rely on palette, network and rim.
- Directional lighting remains: the core gradient, coloured atmosphere and gold rim are all offset toward the Sun.
- Saturn and Uranus keep front/back ring passes with configurable radii, tilt and opacity.
- Hover/active state adds the focus ring, a stronger halo, brighter frames/sparks and a brighter rim.

### Visual Identity
Each planet keeps its distinct palette from `celestialData.js`: Mercury small and grey; Venus warm ochre; Earth blue with a cool atmospheric rim; Mars rust-red; Jupiter large and warm-banded; Saturn pale with prominent rings; Uranus cyan with tilted rings; Neptune deep blue with faint bands. No body uses procedural surface textures any more: colour, scale, latitude bands, rings and the shared network/frames carry its identity inside the Sun's visual language.


### Lighting
- Directional lighting is derived from the direction between each planet and the Sun.
- The additive core gradient is offset toward the Sun; the far limb uses the body's dark colour.
- The Sun-facing limb carries a coloured atmospheric rim plus the shared two-pass gold rim.
- The Sun and all planet glow layers use additive (`lighter`) compositing, so bodies overlap the star's glow naturally.
- No `shadowBlur` is used; it was removed because it dropped software-canvas rendering from ~55 FPS to ~9 FPS. Glow is faked with layered strokes and radial gradients instead.

### Orbital Motion
- Positions use `x = sun.x + cos(angle) * rx`, `y = sun.y + sin(angle) * ry`.
- `rx = orbitRadius * orbitScale`; `ry = rx * orbitSquash` (0.52 on desktop/tablet, 0.66 in the phone rail layout).
- Orbit radii are spaced evenly from 150 to 542 design units, so the system reads as concentric lanes rather than a cramped centre and a detached outer pair.
- Angle combines `baseAngle` with two low-frequency sine terms (`sway`, `swaySpeed`, `phase`), creating a gentle drift rather than a full orbit.
- Navigation planets use small sway values to protect label lanes; Uranus and Neptune use larger, slower drift.
- Labeled planets are distributed top-to-bottom on each side (Mercury/Venus/Mars left, Earth/Jupiter/Saturn right). Uranus closes the lower-left column and Neptune the upper-right column, giving the two unlabeled bodies a deliberate diagonal balance instead of leaving them isolated at the viewport extremes.
- The composition is designed for usability, not astronomical accuracy.

### Background
- Radial deep-space gradient anchored near the Sun, fading to near-black at the viewport edges.
- Warm ember wash centred on the Sun, layered over the deep-space base; it fades out before the navigation lanes so cool-toned UI labels stay legible.
- The reference tunnel of ten nested, rotating 45° squares expands from the star to the viewport edges, tying the composition to the Rasputin visual language.
- Soft nebula wisps, a faint diagonal galactic band and a procedural starfield with per-star phase and twinkle.
- Star count scales with viewport area and is capped for performance.
- The static background layers are cached by viewport size and Sun position; only the tunnel and starfield are redrawn each frame.
- Orbit guides and focus rings use warm gold tones to match the star; navigation labels keep cool light tones for contrast.

## E. Navigation System

### Planet-to-Section Assignments
| Planet | Label | Route |
|---|---|---|
| Mercury | Home | `#/` |
| Venus | About Us | `#/about-us` |
| Earth | Algorithm | `#/algorithm` |
| Mars | EDA | `#/eda` |
| Jupiter | Demonstrations | `#/demonstrations` |
| Saturn | Challenge | `#/challenge` |
| Uranus | none | not assigned |
| Neptune | none | not assigned |

### Leader Geometry
Generated in `navigation.js`:
- Start point: planet center plus the normalized direction toward the elbow, offset by `radius + 3.5`, so the line begins at the planet edge.
- Segment 1 (diagonal): start point to (`lane.elbowX`, `rowY`).
- Segment 2 (horizontal): elbow to (`lane.endX`, `rowY`).
- Labels sit at fixed left/right lanes and fixed rows; only the diagonal segment changes as the planet drifts.
- Each entry also has a pulse path and an endpoint node at the planet edge.

The geometry is recalculated every frame, so leaders stay attached during animation. Labels are positioned once per layout change, which avoids text jitter.

### Interaction States
- Hovering a planet (canvas hit test), a leader, or a label sets the same active planet id.
- Active state highlights the planet focus ring, brightens and animates the leader/pulse/node, emphasizes the label, and updates the HUD readout with the planet name and destination.
- Clicking a navigation planet or label routes to the section.
- Uranus and Neptune have no navigation target but still show "No section assigned" in the readout.
- Keyboard focus on a label produces the same active state; `:focus-visible` provides an outline.
- Home clicked while already on Home triggers a short confirmation pulse instead of a no-op.

### Routing
- Hash routing is used for static-host portability and sub-path deployment: `#/`, `#/about-us`, `#/algorithm`, `#/eda`, `#/demonstrations`, `#/challenge`.
- Unknown hashes are normalized to `#/` with `history.replaceState`, avoiding a broken state.
- Non-home routes open an accessible pending-module panel with a section index, title, honest placeholder summary, and a return-to-home action.
- Escape returns home from any section route.
- Home pauses the animation loop when the document is hidden or a route panel is open.

### Adding a Section
1. Add the label and path to `NAV_SECTIONS` in `celestialData.js`.
2. Assign `nav: '<Label>'` to a planet; set `navSide` (`left`/`right`) and `navRow` (`0`, `1`, `2`).
3. Add generic copy to `ROUTE_COPY` if the route is not ready.
4. Verify label width at the narrowest canvas-layout breakpoint and rerun the browser checks.
5. Update this document.

Uranus and Neptune are the intended extension points: assigning `nav`, `navSide` and `navRow` is enough for the existing navigation manager to generate their leader and label.

## F. Responsive Design

### Desktop and Laptop
- Primary target. Orbit scale is limited by both width and height, the Sun is centered, and labels use fixed left/right columns with three rows.
- Label columns have minimum widths so long labels such as "Demonstrations" do not clip; the right column minimum is 132 px.
- Larger viewports increase spacing and label size while preserving the diagonal-then-horizontal leader shape.

### Tablet
- Same canvas layout with a reduced orbit scale and smaller labels.
- At 768×1024 all six labels remain fully inside the viewport (Demonstrations ends at x≈753).
- Short landscape viewports scale the system by height so the Sun and label rows stay visible.

### Phone Portrait
- Below 700 px wide and at least 620 px tall, the SVG leaders are hidden and the six anchors reflow into a two-column, three-row navigation rail beneath the scene.
- The Sun moves to 44% of viewport height and the orbit squash increases to 0.66, giving the system a rounder, more legible shape above the rail.
- Labels keep their planet swatches, index numbers and accessible names; the rail preserves DOM order for screen readers.
- The canvas remains interactive above the rail; tapping a nav planet still routes.

### Reduced Motion
- The loop stops and time is pinned to 0.
- Twinkle, orbital sway, pulses and transitions are removed or shortened via CSS media query.
- The full scene and all navigation remain usable.

### Known Layout Limits
- Label lanes are intentionally fixed; adding a seventh label would require a fourth row or a different rail arrangement.
- At extremely short viewports (under 620 px tall in landscape), the composition prioritizes keeping the Sun and labels visible over showing every outer orbit.

## G. Development Setup

### Prerequisites
- Node.js 20.19+ or 22.12+ (required by Vite 8).
- npm.
- A modern browser with Canvas 2D, SVG and ES module support.

### Install
```bash
npm install
```

### Run the Development Server
Recommended:
```bash
./start.sh
```
`start.sh` installs dependencies on first run if `node_modules` is missing, starts Vite, and opens the browser when a graphical session is available.

Options:
```bash
PORT=8080 ./start.sh    # request a specific port (Vite moves up if busy)
OPEN=0 ./start.sh       # never open a browser
OPEN=1 ./start.sh       # always attempt to open one
```

Equivalent npm command:
```bash
npm run dev
```

Then open the printed URL (default `http://localhost:5173/`).

### Production Build
```bash
npm run build
npm run preview
```
The build is written to `dist/`. Because routing uses hashes and the Vite base is relative, no server rewrite rules are needed and the bundle can be hosted at any sub-path.

### Verification Performed
- Production build succeeds with Vite.
- The built bundle was also served from `/site/` on a plain static server; assets loaded and routing worked with no console errors.
- Playwright checks at 1440×900, 1920×1080, 1280×800, 1024×768, 768×1024, 390×844, 430×932 and 844×390.
- Verified: canvas renders, Sun is luminous, six labels and six leaders exist, each leader has a diagonal then horizontal segment, hover synchronizes planet/leader/label/readout, planet and label clicks route, Escape and back return home, mobile rail stays inside the viewport, reduced motion renders, and no console or page errors occur.
- Verified long labels are not clipped at 768 px.
- Headless Chromium software-canvas profiling after the Rasputin port: ~44–55 FPS at 1440×900, ~29–47 FPS at 1920×1080, ~59 FPS at 768×1024 and ~60 FPS at 390×844. The remaining cost is the unavoidable additive layer count; `shadowBlur` was the single largest regression and is gone.

## H. Current Development Status

### Implemented
- Full-screen interactive Solar System with the Sun and eight planets.
- Sun ported faithfully from the supplied Canvas 2D reference: amber haze, exact core stops, four 45° frames, two sweeping ellipses, 64-point nearest-4 sphere network, 110 sparks and 50 embers.
- Reference square tunnel and warm ember wash integrated into the background without hiding orbits or labels.
- Planets use the Sun's technique at their own scale: additive core, projected nearest-neighbour network, 45° frames, sweeping arcs, gold sparks and a Sun-facing rim.
- Distinct body identity through palette, size, latitude bands, Saturn/Uranus rings and dynamic lighting.
- Nebula background, starfield, warm orbit guides and active-orbit emphasis.
- Six navigation planets with diagonal + horizontal SVG leaders, endpoint nodes and pulses.
- Hover, focus, click and touch interactions synchronized across canvas, SVG and DOM.
- HUD readout with planet name and destination.
- Hash router with pending-module panels for non-home routes, route index and Escape handling.
- Desktop, laptop, tablet, short-landscape and phone-portrait layouts.
- Reduced-motion support and document-visibility pause.
- Vite setup, production build and `start.sh` launcher.
- This documentation.

### Pending
- Real content for About Us, Algorithm, EDA, Demonstrations and Challenge.
- Optional navigation assignments for Uranus and Neptune.
- Final content/branding review and cross-browser QA on physical devices.

### Known Limitations
- Rendering is a stylized procedural Canvas 2D approximation, not physically based or WebGL.
- The full additive layer stack is expensive on software rendering at very large viewports; a discrete GPU is recommended for 1920×1080 and above.
- Labels use fixed lanes; a new section needs an explicit row/side assignment and a layout check.
- The pending route panel is deliberately generic until section content exists.
- There is no automated test suite in the repository; verification was performed with Playwright scripts outside the project.

## I. Development Guidelines for Future AI Agents

- Read this file before changing architecture, rendering, navigation or responsive behavior.
- Preserve the Canvas 2D visual identity derived from the supplied Sun reference. Do not swap it for static images, generic planet illustrations, WebGL or a 3D model without an explicit requirement.
- Keep the Sun's reference layer set intact (haze, core stops, four frames, two ellipses, 64-point nearest-4 network, 110 sparks, 50 embers) and keep the tunnel in `drawBackground`.
- Keep the shared planet language: additive core, projected point network, warm haze, two 45° frames, elliptical arcs, gold sparks and the Sun-facing gold rim. New bodies should join that language rather than introducing a separate glow or texture style.
- Never reintroduce `shadowBlur`; use layered strokes and radial gradients for glow. It caused an order-of-magnitude software-rendering regression.
- Keep the vanilla ES-module structure and the existing separation: data, layout, rendering, navigation, routing, bootstrap.
- Keep `layout.js` as the single source of truth for shared scene geometry. Renderer, labels and hit testing must use the same coordinates.
- Maintain the leader contract: diagonal segment from the planet edge, then horizontal segment into a fixed label lane.
- Keep all UI copy, code identifiers, comments and documentation in English.
- Keep undeveloped sections honest. Do not invent project claims, metrics or dataset content for pending routes.
- Preserve accessibility: real anchors, keyboard focus, `aria-current`, inert navigation behind route panels, Escape to return, and reduced-motion behavior.
- Test at desktop, 768 px tablet, phone portrait and short landscape. Check label clipping, console errors, hover synchronization and routing before declaring work complete.
- Run `npm run build` after changes and update this document when behavior or architecture changes.
