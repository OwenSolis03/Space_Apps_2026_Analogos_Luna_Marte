# Plan T18: sitio web del proyecto en Vue (para ejecutar con Haiku 5.5)

## Context

El equipo Endurance CXXV necesita una página web que presente el proyecto **Planetary Analog Finder** (NASA Space Apps 2026, challenge "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars"). Hoy `./app` contiene un explorador React + Tailwind funcional. Se reemplaza por un sitio **Vue 3 + TypeScript + Sass + anime.js** con siete vistas, donde el Home es un sistema solar navegable (sol = Results, cinco planetas = secciones), y el explorador React se **porta a Vue** como corazón de Results. Todo sigue las líneas de diseño **RETÍCULA** (https://claude.ai/artifact/KKCjB4XjYzGiXQKt78yi74).

Decisiones ya tomadas por el usuario:

| Tema | Decisión |
| --- | --- |
| Explorador React | Portarlo a Vue dentro de `./app`; eliminar React y Tailwind |
| Idioma | Todo el sitio en **inglés** |
| Tema | Solo **Hangar** (claro). No hay modo oscuro ni toggle |
| Nombre de "Demo" | **How It Works** |
| Integrantes | El texto dice **eight students**; hay 6 con datos y 2 tarjetas pendientes |
| Apellido | **Elías Peregrina Cázares** |

Opinión sobre fusionar secciones (pedida por el usuario): **no fusionar**. Las seis secciones tienen público distinto. Dos ajustes: Home no ocupa planeta (es el sistema solar mismo, quedan 5 planetas + sol), y la antigua sección "Methodology" del explorador React desaparece y su contenido se reparte entre Algorithm y Data.

---

## 0. Reglas globales para Haiku (leer antes de cada fase)

1. **Trabaja fase por fase, en orden.** Al terminar cada fase corre `npm --prefix app run build`. Si falla, arréglalo antes de seguir. No dejes fases a medias.
2. **No inventes datos.** Todo número, nombre de dataset, fórmula o afirmación sale de este plan, de `docs/`, de `pipeline/` o de `app/public/data/analogs_universe.json`. Si falta un dato, usa el componente `RFrame` o un `RTag` con `[PENDING]`; nunca rellenes con texto inventado.
3. **Todo el copy visible va en inglés.** Comentarios de código en inglés.
4. **Solo tokens.** Ningún color, tamaño de fuente, espaciado o grosor escrito a mano en componentes: usa las variables CSS de `_tokens.scss`. Sin `border-radius` (salvo `50%` en `RIconButton` y círculos del sistema solar), sin `box-shadow`, sin `filter: blur`, sin degradados visuales (los `repeating-linear-gradient` de `RHazard` son el único permitido).
5. **Sin emoji, sin fuentes de iconos, sin iconos rellenos.** Solo `RGlyph`.
6. **El naranja `--signal` nunca es color de texto ni de borde informativo** sobre fondos claros. Texto naranja = `--signal-ink`. Texto sobre relleno naranja = `--on-signal`.
7. **Un estado nunca se comunica solo con color**: siempre palabra, marca o cambio de forma.
8. **anime.js es obligatorio** en el sistema solar y en How It Works. Si una llamada de este plan no compila, consulta los tipos en `app/node_modules/animejs/` y https://animejs.com/documentation antes de cambiarla. No la sustituyas por animaciones CSS.
9. **Respeta `prefers-reduced-motion`**: sin bucles ni líneas de tiempo; se pinta el estado final.
10. **GitNexus (obligatorio por `CLAUDE.md`)**: antes de editar o borrar un símbolo existente corre `node .gitnexus/run.cjs impact "<símbolo>" --direction upstream --repo .` y reporta el resultado; antes de cada commit corre `node .gitnexus/run.cjs detect-changes --scope all --repo .`.
11. **No toques** `pipeline/`, `tests/`, `jobs/`, `tools/`, `frontend/`, `output/`, `logs/`, `guion.txt` ni `app/public/data/`.
12. **Git**: rama nueva `feat/website-vue`, un commit local por fase. **No hagas push ni abras PR.**

---

## 1. Stack y dependencias

Dentro de `app/`:

```bash
npm uninstall react react-dom @vitejs/plugin-react @types/react @types/react-dom tailwindcss @tailwindcss/vite
npm install vue vue-router animejs leaflet katex highlight.js
npm install -D @vitejs/plugin-vue vue-tsc sass-embedded
```

- Obligatorias por el usuario: **Vue, TypeScript, Sass, anime.js** (v4, API modular: `import { animate, createTimeline, createScope, stagger, svg, utils } from 'animejs'`).
- Auxiliares necesarias (avisar al usuario en el resumen final): `vue-router` (rutas), `leaflet` (mapas del explorador, ya se usaba), `katex` (fórmulas LaTeX), `highlight.js` (resaltado de código).
- Si `@vitejs/plugin-vue` pide un Vite más nuevo, actualiza `vite` a la última versión.
- `package.json` scripts: `"dev": "vite"`, `"build": "vue-tsc --noEmit && vite build"`, `"preview": "vite preview"`.
- `.claude/launch.json` ya tiene la configuración `app` (puerto 5173): **no la cambies**.

`app/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  base: "./", // relative base: deployable under any sub-path
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { fs: { allow: [".."] } }, // lets the Algorithm page import ../pipeline/*.py?raw
});
```

`app/tsconfig.json`: quitar `"jsx"`, añadir `"paths": {"@/*": ["./src/*"]}`, `"baseUrl": "."`, e `"include": ["src/**/*.ts", "src/**/*.vue", "env.d.ts", "vite.config.ts"]`. Crear `app/env.d.ts` con `/// <reference types="vite/client" />`.

`app/index.html`: `<html lang="en">`, `<div id="app">`, `<script type="module" src="/src/main.ts">`, título `Planetary Analog Finder`, y las fuentes del sistema de diseño:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Martian+Mono:wght@300;400;500;700&family=Roboto:wght@300;400;500&family=Roboto+Condensed:wght@400&display=swap" rel="stylesheet" />
```

---

## 2. Sistema de diseño RETÍCULA (resumen operativo)

**Fase 0 guarda la referencia completa en el repo.** Lee con la herramienta Artifact (`action: "read"`, `url` del artifact, `paths`) estos archivos y cópialos tal cual a `docs/design-system/reticula/`: `project/README.md`, `project/tokens.json`, `project/components/bundle.css`, `project/components/bundle.js`, `project/components/index.d.ts` y los `README.md` de cada componente (`Panel`, `Tag`, `Button`, `IconButton`, `Progress`, `Readout`, `Headline`, `Frame`, `Hazard`, `DotGrid`, `Barcode`, `Glyph`). Son la fuente de verdad; este apartado es solo el resumen.

### 2.1 Tokens (tema Hangar) → `app/src/styles/_tokens.scss` en `:root`

| Variable | Valor | Uso |
| --- | --- | --- |
| `--surface` | `#dfdfdf` | Fondo de página |
| `--surface-raised` | `#ffffff` | Paneles y tarjetas |
| `--surface-sunken` | `#bfbfbf` | Inactivo, vacío, deshabilitado |
| `--surface-ghost` | `#d1d1d1` | Letras gigantes decorativas de fondo |
| `--ink` | `#121212` | Texto principal, hover |
| `--ink-muted` | `#4a4849` | Texto secundario y cuerpo |
| `--graphite` | `#716f70` | Estructura; texto solo si ≥ 24 px |
| `--on-graphite` | `#ffffff` | Texto sobre grafito |
| `--signal` | `#ff8500` | Único acento. Solo rellenos y marcas |
| `--signal-tint` | `#f0b26c` | Módulos secundarios; texto `--ink` |
| `--signal-ink` | `#9e4200` | Texto naranja legible |
| `--on-signal` | `#121212` | Texto sobre naranja |
| `--line` | `#716f70` | Contornos con significado |
| `--line-faint` | `#bfbfbf` | Guías decorativas |
| `--focus` | `#121212` | Anillo de foco 2 px, offset 2 px |

Espacio: `--space-1..9` = 4, 8, 12, 16, 24, 32, 48, 64, 96 px. `--dot-size: 4px`, `--dot-pitch: 16px`. Chaflán: `--chamfer-sm/md/lg` = 8, 16, 24 px. Trazos: `--stroke-hairline/line/bar/heavy` = 1, 2, 4, 8 px. `--radius-0: 0`, `--radius-round: 50%`.

Fuentes: `--font-display: "Martian Mono", "Share Tech Mono", ui-monospace, monospace`; `--font-text: "Roboto", system-ui, sans-serif`; `--font-condensed: "Roboto Condensed", "Roboto", system-ui, sans-serif`.

### 2.2 Tipografía → `_type.scss` (clases utilitarias)

| Clase | Familia | Tamaño / interlínea | Peso | Tracking | Mayúsculas |
| --- | --- | --- | --- | --- | --- |
| `.display-a` | display | `clamp(40px, 8vw, 96px)` / 1 | 300 | 0.12em | sí |
| `.display-c` | display | `clamp(28px, 4.5vw, 48px)` / 0.96 | 300 | 0.02em | sí |
| `.code` | display | `clamp(40px, 6vw, 72px)` / 1 | 300 | 0.04em | sí |
| `.headline` | display | `clamp(18px, 2.4vw, 28px)` / 1.1 | 500 | 0.12em | sí |
| `.byline` | display | 13px / 20px | 400 | 0.1em | sí |
| `.label` | display | 11px / 16px | 500 | 0.1em | sí |
| `.lead` | text | `clamp(18px, 2vw, 24px)` / 1.5 | 300 | 0 | no |
| `.body` | text | 14px / 20px | 400 | 0 | no |
| `.footnote` | text | 12px / 16px | 300 | 0 | no |
| `.quote` | condensed | 14px / 20px | 400 | 0.08em | sí |
| `.tm-outline` | — | `color: transparent; -webkit-text-stroke: 1px var(--ink)` | | | |

Reglas: **un solo `.display-a` por vista**; nunca menos de 11 px; todo texto de interfaz (etiquetas, botones, titulares, estados) en mayúsculas; solo el texto corrido usa minúsculas.

### 2.3 Voz

Escribe como un sistema que informa: frases nominales, sin "you/we" en etiquetas, sin exclamaciones. Identificadores como códigos con ceros: `SEC.04`, `STEP.07`, `FIG.003`, `RUN.2242506`. Estados como anotación entre corchetes: `[NEW CANDIDATE]`, `[KNOWN ANALOG]`, `[PENDING]`. (El texto corrido explicativo sí puede usar "we".)

### 2.4 Excepciones intencionales al sistema (ya aprobadas, documentarlas en un comentario al inicio de `_tokens.scss`)

1. **Movimiento.** RETÍCULA dice "cambios instantáneos, 120 ms lineales como máximo". Excepción: bucles ambientales del sistema solar y animaciones de How It Works, con anime.js y apagados con `prefers-reduced-motion`. Los cambios de estado de interfaz (hover, selección, abrir/cerrar) siguen siendo instantáneos.
2. **Fotografía.** RETÍCULA no admite fotos. Excepción: retratos del equipo en About, siempre con `filter: grayscale(1) contrast(1.05)`, recorte cuadrado, marco de 1 px `--line` y chaflán. Las teselas de Leaflet también en escala de grises.
3. **Texto largo.** Clase adicional `.prose` para Algorithm, Data y Challenge: Roboto 16 px / 26 px, color `--ink`, `max-width: 64ch`.
4. **Idioma.** El sistema tiene ejemplos en español; el sitio va en inglés con la misma voz.

### 2.5 Kit de componentes Vue → `app/src/components/reticula/`

Porta **uno a uno** los componentes de `bundle.js` a SFC de Vue con `<script setup lang="ts">`, las mismas props que `index.d.ts` y las mismas clases `tm-*`. Copia `bundle.css` casi literal a `app/src/styles/_reticula.scss`.

| Componente | Props | Notas |
| --- | --- | --- |
| `RGlyph.vue` | `name`, `size=24`, `tone='ink'`, `label?` | Copia el diccionario `GLYPHS` exacto de `bundle.js`. Sin `label` → `aria-hidden="true"` |
| `RPanel.vue` | `tone='raised'`, `chamfer=true`, `label?`, `note?`, `code?`, `marks?` + slot | Máximo un panel `signal` por zona |
| `RTag.vue` | `tone='graphite'`, `bracket?` + slot | 1 a 3 palabras |
| `RButton.vue` | `variant='primary'`, `arrow?`, `disabled?`, `type='button'`, **`to?`**, **`href?`** + slot | Añadido: con `to` renderiza `<RouterLink>`, con `href` renderiza `<a target="_blank" rel="noreferrer">`, mismas clases |
| `RIconButton.vue` | `label` (obligatorio), `glyph='plus'`, `pressed?`, `disabled?` | `aria-label`, `aria-pressed` |
| `RProgress.vue` | `label`, `value` (0 a 1), `hazard=true` | `role="progressbar"` |
| `RReadout.vue` | `title?`, `items: {label, value, status?, tone?}[]` | `<dl>` |
| `RHeadline.vue` | `title`, `kicker?`, `subtitle?`, `by?`, `size='md'`, `rule='signal'`, `as='h2'` | `lg`=display-a, `md`=display-c, `sm`=headline |
| `RFrame.vue` | `ratio='16 / 9'`, `caption?`, `label?` | Marcador de imagen pendiente |
| `RHazard.vue` | `tone`, `height?`, `width?` | Uno por composición |
| `RDotGrid.vue` | `cols=12`, `rows=3`, `tone`, `lead?` | |
| `RBarcode.vue` | `segments?`, `tone` | Uno por composición |

Añade a `_reticula.scss` dos piezas que el explorador necesita y el kit no trae, con la misma gramática: `.tm-chip` (botón rectangular de selección: borde 1 px `--line`, fondo `--surface-raised`, `.label`; hover → borde `--ink`; `[aria-pressed="true"]` → fondo `--ink`, texto `--surface`) y `.tm-range` (`input[type=range]`: pista de 2 px `--line`, pulgar cuadrado 16 px `--ink`, `accent-color: var(--signal)` como respaldo).

### 2.6 Base y layout → `_base.scss`, `_layout.scss`

- `body { background: var(--surface); color: var(--ink); font-family: var(--font-text); }`, `box-sizing: border-box` global, `:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }`.
- `.page` = contenedor `max-width: 1280px`, padding lateral `--space-4` (móvil) / `--space-8` (≥ 1024 px).
- Dos columnas asimétricas con hueco `--space-7`; bloques alineados al borde izquierdo de su columna; deja **40 a 60 % de vacío**.
- Regla de reduced motion global: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition: none !important; animation: none !important; } }`.
- `src/styles/main.scss` importa con `@use` en este orden: tokens, type, base, layout, reticula, prose, leaflet, code.

---

## 3. Arquitectura de archivos (`app/src/`)

```text
main.ts                     createApp(App).use(router).mount('#app'); imports styles/main.scss
App.vue                     <AppHeader v-if="route.name !== 'home'"/> <RouterView/> <AppFooter/>
router.ts                   createRouter({ history: createWebHashHistory(), routes, scrollBehavior })
styles/                     main.scss, _tokens, _type, _base, _layout, _reticula, _prose, _leaflet, _code
lib/                        types.ts, msi.ts, content.ts, explanations.ts  (EXISTENTES, se conservan sin cambios)
                            extract.ts (nuevo, §7.2), stats.ts (nuevo, §6.2)
composables/                useUniverse.ts, useExplorer.ts, useReducedMotion.ts, useInView.ts
content/                    sections.ts, facts.ts, about.ts, challenge.ts, datasets.ts, eda.ts, algorithm.ts, howItWorks.ts
components/reticula/        R*.vue (§2.5)
components/layout/          AppHeader.vue, AppFooter.vue, PageHero.vue, SectionBlock.vue, DataTable.vue, FigureSlot.vue
components/home/            SolarSystem.vue, SectionRail.vue
components/explorer/        ScenarioPanel.vue, InfoButton.vue, InfoPanel.vue, SiteMap.vue, RankList.vue, SiteDossier.vue, RadarChart.vue
components/charts/          BarChart.vue, StripPlot.vue, FunnelChart.vue, SimilarityMatrix.vue
components/algorithm/       MathTex.vue, CodeBlock.vue, StepCard.vue, PipelineDiagram.vue
components/how/             StageInput.vue, StagePatch.vue, StageMeasure.vue, StageFilter.vue, StageCompare.vue, StageOutput.vue
views/                      HomeView, ResultsView, ChallengeView, HowItWorksView, AlgorithmView, DataView, AboutView, NotFoundView
assets/                     Imagotipo.svg, Isotipo.svg, fotos originales, team/*.webp (generadas en fase 8)
```

Archivos React a **borrar** (después del análisis de impacto de GitNexus): `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/vite-env.d.ts`, `src/components/*.tsx`.

### 3.1 Secciones → `content/sections.ts`

| Código | `name` de ruta | Ruta | Etiqueta | Cuerpo en Home |
| --- | --- | --- | --- | --- |
| `SEC.00` | `home` | `/` | HOME | (el sistema completo) |
| `SEC.01` | `results` | `/results` | RESULTS | **Sol** |
| `SEC.02` | `challenge` | `/challenge` | CHALLENGE | Planeta 1 |
| `SEC.03` | `how-it-works` | `/how-it-works` | HOW IT WORKS | Planeta 2 |
| `SEC.04` | `algorithm` | `/algorithm` | ALGORITHM | Planeta 3 |
| `SEC.05` | `data` | `/data` | DATA | Planeta 4 |
| `SEC.06` | `about` | `/about` | ABOUT US | Planeta 5 |

Todas las vistas salvo Home se cargan con `() => import('./views/X.vue')`. `scrollBehavior`: a `savedPosition` si existe, a `{ el: to.hash }` si hay ancla, si no `{ top: 0 }`. Ruta comodín → `NotFoundView` con un `RButton` a Home.

### 3.2 Shell

- **`AppHeader.vue`** (pegajoso, fondo `--surface`, borde inferior 1 px `--line`): a la izquierda un enlace a Home con el **placeholder del logo del proyecto** (un cuadro de 32 px con `RGlyph name="bracket"` y al lado `PLANETARY ANALOG FINDER` en `.label`; deja un comentario `<!-- TODO: replace with project logo when available -->`). En el centro la navegación: las seis secciones en `.label`; la actual lleva `aria-current="page"`, color `--ink` y un `RGlyph name="tick-left" tone="signal"` delante (marca + palabra, no solo color). A la derecha `Isotipo.svg` a 32 px. En < 900 px la navegación se pliega tras un `RIconButton glyph="dots" label="Open navigation"` que despliega la lista debajo.
- **`AppFooter.vue`**: `ENDURANCE CXXV`, `FROM DATA TO ACTION`, enlace al repositorio, `NASA SPACE APPS CHALLENGE 2026 · SONORA`, línea `COMPUTED ON YUCA · ACARUS · UNIVERSIDAD DE SONORA` y un `RBarcode` como ornamento.
- **`PageHero.vue`** (props `code`, `title`, `subtitle`, slot `aside`): `RHeadline size="lg" as="h1"` con `kicker=code`, y a la derecha el slot para un `RReadout`. Es el único `display-a` de cada vista.
- **`SectionBlock.vue`** (props `id`, `code`, `title`, `subtitle?`): `<section :id>` con `RHeadline size="md" as="h2"` y slot. Separación vertical `--space-9`.

---

## 4. Fase 3 — Home: sistema solar (`views/HomeView.vue`, `components/home/SolarSystem.vue`)

### 4.1 Qué pidió el usuario (requisitos duros)

- Una estrella al centro y planetas en órbitas alrededor; **cada cuerpo es una sección** y lleva a ella con un clic.
- **El sol es RESULTS** y es el protagonista.
- Los planetas **no se trasladan** alrededor de la estrella (posición fija, fáciles de pulsar) pero **giran sobre su propio eje**.
- Sobre cada planeta, **una línea recta que lleva el nombre de la sección**.
- **Todos los planetas del mismo tamaño**; nada de Saturno, Júpiter, anillos ni tamaños distintos.
- Estética RETÍCULA: dibujo de líneas planas, sin brillos, sin degradados, sin fondo oscuro. `frontend/` es solo referencia de la idea (composición, líderes, accesibilidad, raíl móvil); **no copies su render Canvas ni sus colores**.

### 4.2 Construcción: un único SVG en línea

`<svg viewBox="-640 -360 1280 720" preserveAspectRatio="xMidYMid meet">` con ancho 100 % y alto `calc(100dvh - var(--space-9))`, mínimo 480 px. Unidades de diseño:

| Cuerpo | Sección | Órbita `rx` / `ry` | Ángulo θ | Posición (x, y) | Inclinación del eje | Paralelos |
| --- | --- | --- | --- | --- | --- | --- |
| Sol | RESULTS | — | — | (0, 0), radio **76** | — | — |
| Planeta 1 | CHALLENGE | 190 / 95 | 215° | (−156, −54) | −18° | 1 |
| Planeta 2 | HOW IT WORKS | 270 / 135 | 325° | (221, −77) | 12° | 2 |
| Planeta 3 | ALGORITHM | 350 / 175 | 150° | (−303, 88) | 24° | 3 |
| Planeta 4 | DATA | 430 / 215 | 22° | (399, 81) | −8° | 2 |
| Planeta 5 | ABOUT US | 510 / 255 | 197° | (−488, −75) | 30° | 1 |

`x = rx·cos θ`, `y = ry·sin θ` (y hacia abajo). **Radio de todos los planetas: 26.** Guarda esta tabla como arreglo tipado en `content/sections.ts` (campo `orbit`).

Capas, de atrás hacia delante:

1. **Órbitas**: cinco `<ellipse>` sin relleno, trazo 1 px `--line-faint`, `stroke-dasharray="2 6"`.
2. **Sol** (enlace `<a href="#/results">`):
   - tres marcos cuadrados girados 45° (`<rect>` centrados de lado 190, 230 y 270, sin relleno, trazo 1 px `--line`), clase `.sun__frame`;
   - un anillo de tics: `<circle r="92">` sin relleno, trazo 6 px `--graphite`, `stroke-dasharray="1 11"`, clase `.sun__ticks`;
   - un anillo de pulso: `<circle r="76">` sin relleno, trazo 2 px `--signal`, clase `.sun__pulse`;
   - el disco: `<circle r="76" fill="var(--signal)">`;
   - dentro, texto centrado en dos líneas: `SEC.01` (`.label`) y `RESULTS` (`.headline`), ambos con `fill: var(--on-signal)`.
3. **Planetas** (cada uno un `<a href="#/ruta">`), dentro de `<g transform="translate(x y)">`:
   - disco `<circle r="26">` relleno `--surface-raised`, trazo 2 px `--line`;
   - un grupo `<g transform="rotate(tilt)">` recortado al disco con `clipPath`, que contiene: los **paralelos** (1 a 3 líneas horizontales repartidas, trazo 1 px `--graphite`) y cuatro **meridianos** `<ellipse cx="0" cy="0" ry="26">` (trazo 1 px `--graphite`, sin relleno, clase `.planet__meridian`) cuyo `rx` se anima;
   - **líder**: `<line>` vertical de `(0, −32)` a `(0, −80)`, trazo 1 px `--line`, con un cuadrado de 4 px en el extremo superior;
   - **etiqueta** centrada en `(0, −94)`: `<rect>` de fondo `--surface` + texto `SEC.0N / NOMBRE` en `.label`, `fill: var(--ink)`.
4. El sol lleva además el mismo líder hacia arriba (de `(0, −100)` a `(0, −148)`) con la etiqueta `SEC.01 / RESULTS`, en un `RTag` naranja dibujado en SVG (rect `--signal` + texto `--on-signal`).

**Identidad sin tamaño ni color**: los planetas solo se distinguen por la inclinación del eje y el número de paralelos (tabla).

Estados (instantáneos, por CSS): en `:hover` y `:focus-visible` del enlace el disco pasa a trazo `--ink`, el líder a `--ink`, el rect de la etiqueta a `--ink` con texto `--surface`, y la órbita de ese planeta a trazo `--line`. El foco muestra además el anillo `--focus`. Cada `<a>` lleva `aria-label="Go to <section>"`.

Alrededor del SVG, como HTML normal y con mucho vacío: arriba a la izquierda un `RHeadline size="sm" as="h1"` (`kicker`: `NASA SPACE APPS CHALLENGE 2026 · ENDURANCE CXXV`, `title`: `PLANETARY ANALOG FINDER`, `subtitle`: `EARTH SITES THAT STAND IN FOR THE MOON AND MARS`); abajo a la izquierda un `RReadout` con las cifras de `content/facts.ts` (§6.3); abajo a la derecha un `RDotGrid` y la línea `.label` `SELECT A BODY TO NAVIGATE`. Añade un `<p class="sr-only">` que describa la navegación y un enlace "Skip to section list".

### 4.3 Animación con anime.js

```ts
import { animate, createScope, createTimeline, stagger, svg } from "animejs";

let scope: ReturnType<typeof createScope> | undefined;
onMounted(() => {
  scope = createScope({ root: root.value! }).add(() => {
    if (reducedMotion.value) return;            // final state is already in the markup

    // Sun: frames counter-rotate, tick ring turns, pulse ring breathes.
    animate(".sun__frame", { rotate: (_el, i) => (i % 2 ? -360 : 360), duration: (_el, i) => 70000 + i * 25000, ease: "linear", loop: true });
    animate(".sun__ticks", { rotate: 360, duration: 90000, ease: "linear", loop: true });
    animate(".sun__pulse", { scale: [1, 1.22], opacity: [0.7, 0], duration: 2600, ease: "outQuad", loop: true });

    // Orbits: the dash pattern drifts, the planets stay put.
    animate(".orbit", { strokeDashoffset: [0, -64], duration: 9000, ease: "linear", loop: true });

    // Planets spin on their own axis: each meridian's rx follows |sin|.
    root.value!.querySelectorAll<SVGGElement>(".planet").forEach((planet, i) => {
      const meridians = [...planet.querySelectorAll<SVGEllipseElement>(".planet__meridian")];
      const spin = { t: 0 };
      animate(spin, {
        t: Math.PI, duration: 12000 + i * 2500, ease: "linear", loop: true,
        onUpdate: () => meridians.forEach((m, k) =>
          m.setAttribute("rx", String(26 * Math.abs(Math.sin(spin.t + (k * Math.PI) / meridians.length))))),
      });
    });

    // One-off intro: orbits draw, sun grows, planets and labels arrive.
    createTimeline({ defaults: { ease: "outQuad" } })
      .add(svg.createDrawable(".orbit"), { draw: ["0 0", "0 1"], duration: 900, delay: stagger(80) })
      .add(".sun", { scale: [0.6, 1], opacity: [0, 1], duration: 500 }, 200)
      .add(".planet", { opacity: [0, 1], scale: [0.5, 1], duration: 400, delay: stagger(90) }, 500)
      .add(".leader, .planet__label", { opacity: [0, 1], duration: 300, delay: stagger(60) }, 900);
  });
});
onBeforeUnmount(() => scope?.revert());
```

Para que `rotate` y `scale` giren sobre el centro de cada elemento SVG añade en el SCSS: `.sun__frame, .sun__ticks, .sun__pulse, .sun, .planet { transform-box: fill-box; transform-origin: center; }`. El estado inicial del marcado debe ser el estado **final** (todo visible), para que sin JS o con reduced motion la escena esté completa.

`composables/useReducedMotion.ts`: `ref` ligado a `matchMedia('(prefers-reduced-motion: reduce)')` con listener de cambio.

### 4.4 Móvil (< 768 px de ancho)

El SVG usa `viewBox="-330 -200 660 400"`, solo órbitas 1 a 3 visibles a escala y **sin líderes ni etiquetas**; los cuerpos siguen siendo enlaces. Debajo, `SectionRail.vue`: lista de seis filas (RESULTS primero, en un `RPanel tone="signal"` sin altura mínima; el resto `tone="raised"`), cada fila con `SEC.0N`, nombre y `RGlyph name="chevron-right"`. Objetivo táctil ≥ 44 px. Es también el destino del enlace "Skip to section list".

---

## 5. Fase 4 — Results (`views/ResultsView.vue`): explorador portado

Es la sección más importante. Estructura de la vista:

1. **`PageHero`** `code="SEC.01"`, `title="RESULTS"`, `subtitle="WHAT THE GLOBAL SEARCH FOUND"`. En el aside, `RReadout` con cifras **calculadas del JSON** (§6.2): Earth patches evaluated, targets (mission sites), target–analog pairs, unique Earth sites, new candidates, known-analog sites, run id.
2. **`#headline` — "BEST ANALOG PER MISSION SITE"**: tabla (`DataTable`) con los 16 blancos `type === "CURATED"`: cuerpo, nombre, categoría, mejor análogo (país o `known_region`, coordenadas con `fmtLat`/`fmtLon`), MSI del preset seleccionado y un `RTag` `[NEW CANDIDATE]` (tone `signal`) o `[KNOWN ANALOG]` (tone `outline`). Un grupo de `tm-chip` cambia el preset. Clic en una fila → selecciona ese blanco en el explorador y hace scroll a `#explorer`.
3. **`#explorer` — "EXPLORER"**: rejilla de tres columnas en ≥ 1280 px (`ScenarioPanel` | dos `SiteMap` | `RankList`), dos en ≥ 768 px, una en móvil. Selector de cuerpo `MARS` / `MOON` con dos `tm-chip` (`aria-pressed`).
4. **`#site` — "SITE SHEET"**: `SiteDossier`.
5. **`#overview` — "THE BIG PICTURE"**: tres gráficas SVG propias (§6.4) con los datos del JSON.
6. **`#limits` — "WHAT THIS DOES NOT CLAIM"**: lista con `metadata.not_modelled` más los cinco puntos de `docs/value_proposition.md` §7 ("What we must not claim"), copiados literalmente.

### 5.1 Lógica que se reutiliza sin cambios

`lib/types.ts`, `lib/msi.ts` (`msi`, `msiLog`, `rankTargets`, `availableDimensions`, `fmtLat`, `fmtLon`, `fmtNum`, `pct`, `DIMENSION_BODIES`), `lib/content.ts` (`BODY_LABEL`, `DIM_LABEL`, `FEATURE_LABEL`, `GEO_CLASS_LABEL`, `fmtValue`, `limitLabel`, `TILES`, `suggestedUses`) y `lib/explanations.ts`. **No los reescribas.** Corre el análisis de impacto de GitNexus sobre `rankTargets`, `msi`, `msiLog`, `availableDimensions`, `fullWeights` y `suggestedUses` antes de borrar los `.tsx` y reporta el resultado.

### 5.2 Mapa de portado React → Vue

| React (borrar al final) | Vue | Qué conservar exactamente |
| --- | --- | --- |
| `fetch` en `App.tsx` | `composables/useUniverse.ts` | Singleton a nivel de módulo: `state = shallowRef<Load>({state:'loading'})`, una sola petición a `` `${import.meta.env.BASE_URL}data/analogs_universe.json` ``, compartida por Results, How It Works y Data. Estados `loading` / `error` / `ready` con los mismos textos |
| Estado de `App.tsx` | `composables/useExplorer.ts` | `body`, `presetId`, `weights`, `minScore`, `lambda`, `newOnly`, `targetId`, `analogIndex` como `ref`; `bodyTargets`, `available`, `dimInfo`, `ranked`/`unranked`, `selected`, `safeAnalog`, `targetPoints`, `earthPoints` como `computed`; acciones `selectTarget`, `changeBody` (con el cambio automático de preset si no aplica al cuerpo), `changeWeight` (pone `presetId = null`), `choosePreset`. Al cargar: primer preset de `mission_presets` |
| `ScenarioPanel.tsx` | `explorer/ScenarioPanel.vue` | Interruptor "Show explanations" (`role="switch"`, `localStorage` clave `paf.explanations` dentro de `try/catch`), 10 controles con su `InfoButton` + `InfoPanel`, porcentajes normalizados, dimensiones no disponibles deshabilitadas con la nota `not modelled for <body>`, `λ = 0.00 (0 = off)` |
| `InfoToggle.tsx` | `explorer/InfoButton.vue`, `explorer/InfoPanel.vue` | `aria-expanded`, `aria-controls`, `aria-label="What does X mean?"`, panel `role="region"` con las cuatro partes de `EXPLANATION_HEADINGS` |
| `SiteMap.tsx` | `explorer/SiteMap.vue` | Leaflet en `onMounted`; **guarda el mapa y la capa en variables normales, no en `ref`** (Vue no debe volver reactivos los objetos de Leaflet); `watch` de `points` para redibujar; `ResizeObserver` → `invalidateSize()`; `flyTo` al seleccionado en el mapa de la Tierra; `EPSG4326` para Marte y Luna (`geographic`), `EPSG3857` para la Tierra; `map.remove()` en `onBeforeUnmount` |
| `RankList.tsx` | `explorer/RankList.vue` | Lista ordenada, `aria-current`, contador `n / total`, pie con blancos no clasificados y sus dimensiones faltantes |
| `Dossier.tsx` | `explorer/SiteDossier.vue` | Tarjeta blanco vs. análogo, tira horizontal de análogos (chips `#n · MSI`), tabla de rasgos con `match` / `mismatch (z ±x)` / `differs` / `no data`, filas de `earth_missing_dims`, fila de elevación "not comparable (datum)", "Suggested field use", "Where the analogy breaks" con `limits[body]` |
| `Radar.tsx` | `explorer/RadarChart.vue` | Mismo cálculo; ejes no aplicables punteados; marcador hueco cuando falta el dato terrestre; `aria-label` con el resumen |

### 5.3 Reestilo RETÍCULA del explorador

- Paneles → `RPanel tone="raised"` (o `<section class="tm-panel tm-panel--raised">` sin altura mínima). Chips → `.tm-chip`. Títulos → `.headline` / `.label`. Números → `--font-display`.
- `match` = `RGlyph name="tick-right"` + palabra en `--ink`; `mismatch` = `RGlyph name="close"` + palabra en `--signal-ink`. Nunca solo color.
- El objeto seleccionado (fila del ranking, chip de análogo) = fondo `--ink`, texto `--surface`, y `RGlyph name="tick-left" tone="signal"` al lado.
- Mapa (`_leaflet.scss`, importa `leaflet/dist/leaflet.css`): `.leaflet-tile-pane { filter: grayscale(1) contrast(1.05); }`. Marcadores: blancos (`.mk-target`) relleno `--signal`, trazo `--ink`; análogos (`.mk-earth`) relleno `--surface-raised`, trazo `--ink`; seleccionado (`.is-on`) relleno `--ink` y radio 9 (cambio de tamaño además de color).
- Radar: polígono con relleno `--signal-tint` y trazo `--ink` de 2 px; retícula `--line-faint`.

---

## 6. Datos derivados y gráficas

### 6.1 Regla

Las gráficas son SVG propios en `components/charts/` (sin librerías). Una sola tinta: barras `--graphite`, la barra o punto destacado en `--signal`, texto `--ink` / `--ink-muted`, ejes 1 px `--line`. Cada gráfica lleva `role="img"`, un `aria-label` que resume el dato y los valores escritos junto a las marcas.

### 6.2 `lib/stats.ts` (funciones puras sobre `Universe`)

- `summary(u)` → `{ earthPatches, targets, curated, pairs, uniqueSites, newSites, knownSites, runId, generatedAt }`. Valores esperados con el JSON actual, para comprobar: 40,244 · 76 · 16 · 4,944 · 3,651 · 3,522 · 129 · `2242506`.
- `bestPerTarget(u, presetKey)` → mejor análogo con `msi_by_preset[presetKey] != null` por blanco curado.
- `sitesByCountry(u, n)` → conteo de sitios únicos (por `analog.id`) por país, top `n`. Esperado: Antarctica 571, China 414, Saudi Arabia 183, Algeria 164, Canada 147.
- `bestMsiByBody(u, presetKey)` → lista de mejores MSI por blanco, separada en Moon / Mars.
- `geoClassCounts(u)` → conteo de `target.geology.geo_class` por cuerpo.

### 6.3 `content/facts.ts` (constantes para Home y How It Works, con su fuente en un comentario)

`EARTH_PATCHES = 40244`, `MARS_PATCHES = 140916`, `MOON_PATCHES = 36741`, `TARGETS = 76`, `CURATED_TARGETS = 16`, `PAIRS = 4944`, `RUN_ID = "2242506"`, `PATCH_KM = 32`, `PATCH_RES_M = 500`, `PATCH_PX = 64`, `COPERNICUS_TILES = 26475`, y el embudo de la Tierra: `GRID = 497818`, `WITH_TILE = 179663`, `VEGETATED = 113935`, `NO_LAND_DATA = 21353`, `KEPT = 44375`, `VALID = 40244`. Fuentes: `docs/handoff.md` §1 y §3, `docs/logbook.md` (tabla `prefilter_stats.json`).

### 6.4 Gráficas de Results `#overview`

1. `BarChart` horizontal: 15 países con más sitios candidatos (`sitesByCountry`).
2. `StripPlot`: mejor MSI por blanco, una fila para Moon y otra para Mars, con la mediana marcada. Texto al lado (de `docs/value_proposition.md` §7): "Lunar scores are lower because Earth has very little arid terrain as rugged as the lunar south pole at this scale. That is a finding, not a bug."
3. Barra partida única: sitios `NEW_CANDIDATE` frente a `KNOWN_ANALOG` con ambas cifras escritas.

---

## 7. Fase 5 — Algorithm (`views/AlgorithmView.vue`)

### 7.1 Estructura

1. `PageHero` `code="SEC.04"`, `title="ALGORITHM"`, `subtitle="FROM RAW ELEVATION TO A RANKED, EXPLAINABLE ANALOG"`.
2. **Bloque del repositorio, lo primero de la página**: `RPanel tone="raised"` con `label="SOURCE CODE"`, un `RButton variant="primary" arrow` con `href="https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte"` y texto `OPEN REPOSITORY`, y un `CodeBlock lang="bash"` con `git clone https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte.git`.
3. `PipelineDiagram.vue`: SVG estático de las etapas `T3 → T4`, `T6 → T5`, `T12 / T13 / T14`, `T7 → T8 → APP` (cajas con chaflán y líneas rectas, cada caja enlaza al paso correspondiente). Fuente: bloque "How it works" del `README.md`.
4. Dos columnas: a la izquierda un índice pegajoso de pasos (`STEP.01` … `STEP.11`, con el actual marcado por `tick-left`); a la derecha un `StepCard` por paso.
5. Al final, "PARAMETERS AT A GLANCE": `RReadout` con todas las constantes del §7.4.

`StepCard.vue` muestra en este orden: código y título, párrafos `.prose`, fórmulas (`MathTex`), tabla de parámetros (`RReadout`), y los bloques de código (`CodeBlock`) con la ruta del archivo y un enlace `VIEW ON GITHUB` a `https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte/blob/main/<ruta>`.

### 7.2 Código real del repositorio, no copiado a mano

`CodeBlock` recibe el archivo completo importado con `?raw` y extrae el símbolo, para que el sitio nunca se desfase del pipeline:

```ts
// content/algorithm.ts
import featuresPy from "../../../pipeline/features.py?raw";
import matchPy from "../../../pipeline/match.py?raw";
// ... geo.py, planet_features.py, targets.py, earth_features.py, dust.py, ice.py, geology_rules.py
import msiTs from "@/lib/msi.ts?raw";
```

```ts
// lib/extract.ts
/** Returns the source of a top-level or nested Python `def`/`class` (with its decorators),
 *  or of a TS `export function`, by header text. Throws if the header is not found. */
export function extractBlock(source: string, header: string): string {
  const lines = source.split("\n");
  const start = lines.findIndex((l) => l.trimStart().startsWith(header));
  if (start < 0) throw new Error(`extractBlock: "${header}" not found`);
  const indent = lines[start].length - lines[start].trimStart().length;
  let first = start;
  while (first > 0 && lines[first - 1].trim().startsWith("@")) first--;   // decorators
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    const l = lines[i];
    if (l.trim() === "") continue;
    const ind = l.length - l.trimStart().length;
    const t = l.trimStart();
    // a multi-line signature closes with ")" or "}" at the header's indent: still the same block
    if (ind <= indent && !t.startsWith(")") && !t.startsWith("}")) { end = i; break; }
  }
  while (end > start && lines[end - 1].trim() === "") end--;
  return lines.slice(first, end).map((l) => l.slice(indent)).join("\n");
}
```

Para funciones TS que terminan en `}` a nivel 0, usa en su lugar `extractBetween(source, startHeader, endHeaderExclusive)` (corta desde la línea que empieza con `startHeader` hasta la anterior a la que empieza con `endHeaderExclusive`). Comprueba en el navegador que **cada** bloque muestra la función completa y nada más.

`CodeBlock.vue`: props `code`, `lang` (`python` | `typescript` | `bash`), `file?`, `collapsedLines = 36`. Resalta con `highlight.js/lib/core` registrando solo `python`, `typescript` y `bash`. Si el código supera `collapsedLines`, muestra las primeras y un `RButton variant="secondary"` `SHOW FULL FUNCTION (N LINES)` / `COLLAPSE`. Fondo `--surface-raised`, borde 1 px `--line`, chaflán, fuente `--font-display` 12 px / 18 px, scroll horizontal. Tema en `_code.scss` solo con tokens: palabras clave `--ink` peso 700, cadenas y números `--signal-ink`, comentarios y docstrings `--ink-muted`, resto `--ink`. Botón `COPY` (`navigator.clipboard`), que cambia su texto a `COPIED` durante 1.5 s.

`MathTex.vue`: props `tex`, `block = true`. `katex.renderToString(tex, { displayMode: block, throwOnError: false })` en `v-html`; importa `katex/dist/katex.min.css`. Escribe las fórmulas en `content/algorithm.ts` con `String.raw` para no escapar las barras. Fórmulas de bloque dentro de un contenedor con scroll horizontal en móvil.

### 7.3 Los pasos (contenido exacto)

Cada paso: `code`, `title`, `summary` (redáctalo en 2 a 4 frases en inglés a partir de "Idea"), `formulas`, `params`, `snippets`.

**STEP.01 — ONE GRID FOR EVERY BODY.** Idea: se barren los tres cuerpos con una malla casi equiareal de centros de parche entre −88° y 88°; el paso en longitud se ensancha con la latitud para que todos los parches cubran la misma superficie.
```latex
\Delta\varphi=\frac{180}{\pi}\cdot\frac{L}{R},\qquad \Delta\lambda(\varphi)=\frac{\Delta\varphi}{\cos\varphi},\qquad L=32\ \text{km}
```
Params: R Earth 6,371,000 m · R Moon 1,737,400 m · R Mars 3,396,190 m (`pipeline/config.py`). Snippet: `planet_features.py` → `def generate_grid`.

**STEP.02 — THE SAME 32 KM PATCH EVERYWHERE.** Idea: cada parche se reproyecta a una proyección azimutal equidistante local centrada en sí mismo y se remuestrea a 500 m/px (64 × 64). Antes se limpian los datos: se enmascara `nodata`, luego se aplica escala y offset. Se descartan parches con menos del 90 % de píxeles válidos y los que cruzan ±180°. Así pendiente y rugosidad son comparables entre cuerpos y latitudes.
```latex
N=\frac{L}{r}=\frac{32\,000\ \text{m}}{500\ \text{m}}=64,\qquad z=\text{raw}\cdot s+o,\qquad \frac{\#\{\text{valid pixels}\}}{N^{2}}\ \ge\ 0.90
```
```latex
x=R\,c\,\sin\alpha,\quad y=R\,c\,\cos\alpha,\qquad \cos c=\sin\varphi_0\sin\varphi+\cos\varphi_0\cos\varphi\cos(\lambda-\lambda_0)
```
(c = distancia angular al centro, α = acimut). Snippets: `geo.py` → `def extract_patch` (colapsado) y `def _clean_nodata`.

**STEP.03 — SIX TERRAIN FEATURES.** Idea: una única función calcula los mismos rasgos para Tierra, Luna y Marte. La elevación media se guarda pero **no se compara**, porque los datums difieren.
```latex
s_{ij}=\arctan\sqrt{\left(\frac{\partial z}{\partial x}\right)^{2}+\left(\frac{\partial z}{\partial y}\right)^{2}},\qquad \bar{s}=\operatorname{mean}(s),\qquad s_{90}=P_{90}(s)
```
```latex
\text{relief}=P_{95}(z)-P_{5}(z),\qquad HI=\frac{\bar{z}-z_{\min}}{z_{\max}-z_{\min}}
```
```latex
\hat{z}=ax+by+c\ \ (\text{least squares}),\qquad \sigma_d=\operatorname{std}\!\left(z-\hat{z}\right)
```
```latex
TRI=\operatorname*{mean}_{(i,j)}\sqrt{\sum_{k\in N_8(i,j)}\left(z_k-z_{ij}\right)^{2}}
```
Snippet: `features.py` → `def compute_features` (completa, es la pieza central).

**STEP.04 — TARGETS ON THE MOON AND MARS.** Idea: 16 blancos curados (8 lunares: regiones candidatas de Artemis III ancladas en el rasgo IAU del mismo nombre, más el borde de Shackleton; 8 marcianos: sitios de aterrizaje y la región de hielo somero de Arcadia) y 30 arquetipos de terreno por cuerpo. Un ancla `point` promedia 5 parches (centro + 4 vecinos, mínimo 3 válidos); un ancla `rim` promedia 8 parches sobre el borde cada 45° (mínimo 5 válidos). Los arquetipos salen de k-means sobre rasgos estandarizados (con `log1p` en relieve, σ_d y TRI); el representante es el parche real más cercano al centroide.
```latex
\mathbf{f}_T=\frac{1}{n}\sum_{p=1}^{n}\mathbf{f}_p,\qquad \min_{\mu,\,c}\ \sum_i\left\lVert \mathbf{x}_i-\mu_{c(i)}\right\rVert^{2},\quad k=30
```
Snippets: `targets.py` → `def anchor_points`, `def build_clusters`. Lee en `targets.py` los valores de `NEIGHBOR_OFFSET_KM`, `N_CLUSTERS`, `KMEANS_SEED` y `CLUSTER_FEATURES` y ponlos en la tabla de parámetros.

**STEP.05 — EARTH: ONLY BARE GROUND.** Idea: de 497,818 puntos de malla, 179,663 tienen tesela de tierra; se descartan los vegetados (NDVI máximo anual > 0.25); los que no tienen NDVI (hielo y nieve permanentes) pasan solo si tienen temperatura de superficie. Quedan 44,375 candidatos y 40,244 parches válidos (90.69 %). Cada sitio recibe además distancia a carretera y aeropuerto, país, y la etiqueta `KNOWN_ANALOG` si cae en una de las 12 regiones análogas ya estudiadas, o `NEW_CANDIDATE`.
```latex
\text{keep}\iff \mathrm{NDVI}_{\max}\le 0.25\ \ \lor\ \ \left(\mathrm{NDVI}_{\max}=\varnothing\ \land\ \mathrm{LST}_{\text{day}}\neq\varnothing\right)
```
Snippet: `earth_features.py` → `def _compute_prefilter_masks`. Incluye aquí el `FunnelChart` (§8.3).

**STEP.06 — ROBUST NORMALISATION IN EARTH UNITS.** Idea: los rasgos se expresan en "desviaciones típicas terrestres" con mediana y MAD ajustadas **solo con la Tierra**, tras `log1p` en los rasgos de cola larga. Así un z = 2 significa "dos desviaciones terrestres más abrupto que el suelo desnudo típico de la Tierra".
```latex
x'=\ln(1+x)\ \ \text{for relief},\ \sigma_d,\ TRI;\qquad z_k=\frac{x'_k-\operatorname{med}_E(x'_k)}{1.4826\cdot\operatorname{MAD}_E(x'_k)},\qquad \operatorname{MAD}=\operatorname{med}\left|x'-\operatorname{med}(x')\right|
```
Snippet: `match.py` → `class Normalizer`. Tabla con `metadata.normalization` (mediana y escala por rasgo) leída del JSON.

**STEP.07 — SEVEN SIMILARITY DIMENSIONS.** Idea: cada dimensión da una similitud entre 0 y 1 con un núcleo gaussiano (RBF). Las que no son comparables en unidades absolutas (térmica, polvo, frío) comparan **rangos percentiles dentro de cada planeta**: qué tan extremo es el sitio "en casa". Presenta cada dimensión como sub-bloque con su fórmula:
```latex
d_{\text{topo}}=\sqrt{\tfrac{1}{4}\sum_{k\in\mathcal{T}}\left(z^{E}_k-z^{T}_k\right)^{2}},\qquad S_{\text{topo}}=\exp\!\left(-\frac{d_{\text{topo}}^{2}}{2\sigma^{2}}\right),\quad \sigma=1
```
```latex
d_{\text{rough}}=\sqrt{\tfrac{1}{2}\sum_{k\in\mathcal{R}}\left(z^{E}_k-z^{T}_k\right)^{2}},\qquad S_{\text{rough}}=\exp\!\left(-\frac{d_{\text{rough}}^{2}}{2\sigma^{2}}\right)
```
```latex
S_{\text{env}}=\exp\!\left(-\frac{\max\!\left(0,\ \mathrm{NDVI}_{\max}-0.10\right)^{2}}{2\,(0.10)^{2}}\right)
```
```latex
r=\frac{\operatorname{rank}(x)}{n}\ \ (\text{within its own planet}),\qquad S_{\text{thermal}}=\exp\!\left(-\frac{1}{2}\left(\frac{r_E-r_T}{0.15}\right)^{2}\right)
```
```latex
S_{\text{geo}}=M\!\left[c_T,\ c_E\right]\quad(\text{8-class similarity matrix})
```
```latex
S_{\text{dust}}=\exp\!\left(-\frac{d_L^{2}+d_S^{2}+d_\phi^{2}}{6}\right),\quad d_L=\frac{\left|r^{L}_E-r^{L}_T\right|}{0.15},\quad d_S=\frac{\left|r^{S}_E-r^{S}_T\right|}{0.15},\quad d_\phi=\frac{\Delta_\circ(\phi_E,\phi_T)}{60^\circ}
```
```latex
\text{seasonality}=\frac{\max_b\tau_b-\min_b\tau_b}{\bar{\tau}+\varepsilon},\qquad L_s^{E}=\left(\frac{\text{doy}-79.5}{365.2422}\cdot 360^\circ\right)\bmod 360^\circ
```
```latex
S_{\text{ice}}^{\text{Moon}}=\exp\!\left(-\frac{d^{2}}{2}\right),\quad d=\sqrt{\frac{d_c^{2}+d_i^{2}}{2}},\quad d_c=\frac{r^{c}_E-r^{c}_T}{0.15},\quad d_i=\frac{I_E-I_T}{0.5};\qquad S_{\text{ice}}^{\text{Mars}}=\exp\!\left(-\frac{d_i^{2}}{2}\right)\ \ (I_T>0)
```
Notas a incluir: 𝒯 = {mean slope, p90 slope, relief, hypsometric integral}; ℛ = {σ_d, TRI}; NDVI ausente (hielo) cuenta como suelo desnudo, S_env = 1; térmica y polvo solo para Marte; cerca del ecuador (|lat| < 15° en el parche terrestre o en el blanco) se elimina el término de fase y el divisor pasa de 6 a 4; la fase del polvo se desplaza 180° en el hemisferio sur para alinear estaciones; I_E = 1 (capa de hielo), 0.5 (suelo helado, LST diurna < 0 °C), 0 (resto). Dibuja la matriz geológica con `SimilarityMatrix.vue` leyendo `metadata.geology_similarity` (tabla 8 × 8, celdas con el valor escrito y relleno `--surface-raised` / `--signal-tint` / `--signal` según 0 / intermedio / 1). Snippets: `match.py` → `def dimension_scores`, `def geology_scores`; `dust.py` → `def S_dust`; `ice.py` → `def S_ice`; `geology_rules.py` → `_OFF_DIAGONAL_SIMILARITIES` (con `extractBetween`).

**STEP.08 — MISSION SIMILARITY INDEX AND MISSING DATA.** Idea: el MSI es la media ponderada de las dimensiones. Cinco presets de misión fijan los pesos y el usuario puede cambiarlos. La política de datos faltantes distingue tres casos: (A) la dimensión no aplica al cuerpo → se ignora; (B) falta en el blanco → se ignora, pero si la cobertura de pesos cae por debajo de 0.6 el blanco no se clasifica en ese preset; (C) el blanco la tiene y el parche terrestre no → cuenta 0 ("no evidence, no credit"). Cuenta el porqué, de `docs/plan_t16_missing_data.md` §0: antes de esta regla el preset de polvo mandaba los blancos de Marte a la Antártida, porque allí no hay dato de polvo y ese 40 % del peso desaparecía.
```latex
\mathrm{MSI}=\frac{\sum_{d\in\mathcal{D}_T}w_d\,\tilde{S}_d}{\sum_{d\in\mathcal{D}_T}w_d},\qquad \tilde{S}_d=\begin{cases}S_d&\text{if measured on Earth}\\[2pt]0&\text{otherwise}\end{cases}
```
```latex
\text{coverage}=\frac{\sum_{d\in\mathcal{D}_T}w_d}{\sum_{d\in\mathcal{A}_b}w_d}\ \ge\ 0.6
```
Tabla de presets × dimensiones leída de `mission_presets` del JSON. Lista `metadata.scoring_policy.rules` tal cual. Snippets: `match.py` → `def msi`, `def preset_status`, `def available_dims`.

**STEP.09 — DIVERSE TOP 30.** Idea: se puntúan los 40,244 parches terrestres contra cada blanco y se recorre la lista de mayor a menor MSI aceptando un sitio solo si está a ≥ 150 km de todos los aceptados, hasta 30 por preset; como máximo 3 sitios sobre hielo por lista (salvo en el preset de hielo).
```latex
d=2R\arcsin\sqrt{\sin^{2}\frac{\Delta\varphi}{2}+\cos\varphi_1\cos\varphi_2\,\sin^{2}\frac{\Delta\lambda}{2}},\qquad \min_j d(i,j)\ \ge\ 150\ \text{km}
```
Snippets: `match.py` → `def select_diverse`, `def haversine_km`, `def select_by_preset`.

**STEP.10 — WHERE THE ANALOGY BREAKS.** Idea: cada pareja lista los rasgos que no coinciden, en unidades físicas, más los límites físicos fijos de cada cuerpo (gravedad, atmósfera, radiación…), que ningún sitio terrestre reproduce.
```latex
\left|z^{E}_k-z^{T}_k\right|>1.5,\qquad \left|r_E-r_T\right|>0.30,\qquad \Delta_\circ(\phi_E,\phi_T)>90^\circ,\qquad c_E\neq c_T
```
Snippets: `match.py` → `def mismatches`, `def layer_mismatches`. Muestra `limits.Moon` y `limits.Mars` del JSON en dos tablas.

**STEP.11 — RE-WEIGHTING IN THE BROWSER.** Idea: el JSON exportado guarda las sub-puntuaciones, así que la app recalcula el MSI al mover un deslizador, con un factor opcional de cercanía a carretera.
```latex
\mathrm{MSI}_{\lambda}=\mathrm{MSI}\cdot\left(1-\lambda+\lambda\,e^{-d_{\text{road}}/100\ \text{km}}\right),\qquad \lambda\in[0,\ 0.3]
```
Snippets: `lib/msi.ts` → `msi`, `msiLog` (con `extractBetween`). Termina con un `RButton arrow to="/results"` `TRY IT IN RESULTS`.

### 7.4 Constantes para "PARAMETERS AT A GLANCE" (de `pipeline/match.py`, `dust.py`, `ice.py`, `config.py`)

Patch 32 km · 500 m/px · 64 × 64 · valid ≥ 0.90 · σ = 1 · NDVI free 0.10 · NDVI scale 0.10 · NDVI prefilter 0.25 · thermal unit 0.15 · dust rank σ 0.15 · dust phase σ 60° · tropical band 15° · cold rank σ 0.15 · ice level σ 0.50 · Earth-missing score 0.0 · min preset coverage 0.6 · top N 30 · min separation 150 km · max ice-surface sites 3 · mismatch z 1.5 · mismatch rank 0.30 · mismatch phase 90° · MAD→σ 1.4826.

---

## 8. Fase 6 — Data (`views/DataView.vue`)

`PageHero` `code="SEC.05"`, `title="DATA"`, `subtitle="OPEN DATASETS AND WHAT THEY TAUGHT US"`. Aside: `RReadout` con `RAW VOLUME ≈ 80 GB`, `DATASETS 15`, `COPERNICUS TILES 26,475`, `BODIES 3`.

### 8.1 `#datasets` — "DATASETS"

`content/datasets.ts`: transcribe la tabla "Data" del `README.md` (cuerpo, dataset, uso, fuente con su enlace) y complétala con las filas de geología, polvo y nomenclatura de `docs/pipeline.md` §Data (GLiM, USGS SIM 3292, Unified Geologic Map of the Moon, Montabone CDOD, MOD08_M3, Gazetteer). Muéstrala agrupada por cuerpo (MARS / MOON / EARTH) con `DataTable` y un `RTag` por dimensión que alimenta. Debajo:

- **"OFFICIAL CHALLENGE RESOURCES"**: la tabla de `docs/implementation_plan.md` §2 (recurso oficial, ¿usado?, producto), literal.
- **"REFERENCES"**: `metadata.citations` del JSON, como lista `.footnote`, más los enlaces de `metadata.datasets`.

### 8.2 `#eda` — "EXPLORATORY DATA ANALYSIS"

Fuentes: `docs/pipeline.md` (§"Type, scale and nodata of every file", §"Recorded runs", §"Exploring the data"), `docs/HISTORY.md` §2 y §6, `docs/logbook.md` (entrada de T5) y `docs/plan_t16_missing_data.md` §0 y §1. Contenido en `content/eda.ts`:

1. **"WHAT IS INSIDE EVERY FILE"**: la tabla completa de tipo, escala, offset, nodata y nota de `docs/pipeline.md`, con la regla destacada en un `RPanel tone="tint"`: `ALWAYS APPLY value = raw · scale + offset`.
2. **"FINDINGS"**: una tarjeta `RPanel` por hallazgo, con código `EDA.01`…, título, dos o tres frases y la consecuencia para el diseño:
   - `EDA.01` LOLA stores half-metres (`scale = 0.5`): every lunar vertical metric was doubled; after the fix the median lunar slope went from 13.24° to 6.93°.
   - `EDA.02` MODIS uses opposite conventions: NDVI is `raw ÷ 10000`, LST is `raw × 0.02 − 273.15`.
   - `EDA.03` Copernicus GLO-90 has no nodata value and the sea is exactly 0.0; the mosaic treats 0 as nodata.
   - `EDA.04` The file named lunar "albedo" was a colour-shaded relief; it was discarded and replaced by LROC WAC.
   - `EDA.05` THEMIS mosaics are grey levels, not kelvin, and LROC WAC is relative brightness → compared as percentile ranks within each planet.
   - `EDA.06` MODIS NDVI has no data south of 59.45°S and Deep Blue AOD has no retrievals over snow and ice → the missing-data policy (STEP.08).
   - `EDA.07` v1 compared windows of different size per body (~118 km on Mars, ~30 km on the Moon, ~46 km on Earth) → one 32 km patch at 500 m/px for all three.
   - `EDA.08` Earth is flat at this scale: the median mean slope of bare-ground patches is 0.46° (from `metadata.normalization.median.mean_slope_deg`), against a 6.93° median on the Moon.
3. **"COVERAGE"**: `DataTable` con Mars 140,916 parches (99.61 %), Moon 36,741 (99.26 %), Earth 40,244 válidos de 44,375 candidatos (90.69 %); y el desglose del prefiltro terrestre (`grid`, `no_tile`, `vegetated`, `no_land_data`, `ndvi_missing`, `kept`) de `docs/logbook.md`.
4. **Gráficas en vivo** (del JSON, §6): `StripPlot` de `mean_slope_deg` de los blancos por cuerpo; `BarChart` de clases geológicas de los blancos (`geoClassCounts`); tabla de `metadata.normalization`.
5. **"FIGURES"**: los mapas de control viven en Yuca, no en el repositorio. Usa `FigureSlot.vue` (props `src?`, `caption`, `alt`): si `src` existe muestra la imagen en escala de grises; si no, un `RFrame` con el pie. Declara en `content/eda.ts` estas ranuras sin `src`: `FIG.001 map_earth_mean_slope_deg.png (run 2242438)`, `FIG.002 map_earth_classification.png (run 2242438)`, `FIG.003 map_targets_mars.png (run 2242423)`, `FIG.004 map_targets_moon.png (run 2242423)`, `FIG.005 map_dust_level_*.png (run 2242484)`. Crea `app/public/figures/README.md` explicando que basta con copiar ahí el PNG y poner su ruta en `content/eda.ts`.

### 8.3 `FunnelChart.vue`

Barras horizontales decrecientes con las cifras del embudo de `content/facts.ts`: 497,818 → 179,663 → 44,375 → 40,244, cada una con su etiqueta (`GRID POINTS`, `ON LAND TILES`, `BARE GROUND`, `VALID PATCHES`) y el porcentaje respecto a la anterior. La última barra en `--signal`. Se reutiliza en Algorithm STEP.05 y en How It Works.

---

## 9. Fase 7 — How It Works (`views/HowItWorksView.vue`)

Público: un estudiante con nociones, no un experto. **Sin fórmulas ni código.** Lenguaje llano, con el tono de `lib/explanations.ts`. Es la parte más visual: qué entra, qué pasa, qué sale.

`PageHero` `code="SEC.03"`, `title="HOW IT WORKS"`, `subtitle="WHAT GOES IN, WHAT COMES OUT"`. Debajo, una tira fija de progreso con los seis pasos (`01 INPUT` … `06 OUTPUT`) que marca el actual.

Seis etapas a pantalla casi completa (`min-height: 80dvh`), cada una con texto a la izquierda (columna estrecha: `RHeadline size="md"`, un párrafo `.lead` corto y dos o tres líneas `.body`) y una figura SVG animada a la derecha. Cada figura es un componente en `components/how/` que crea su `createTimeline({ autoplay: false })` dentro de un `createScope` y lo reproduce al entrar en pantalla con `composables/useInView.ts` (un `IntersectionObserver` con `threshold: 0.4`, que llama `timeline.play()` una vez). Con reduced motion, `timeline.seek(timeline.duration)` para mostrar el estado final.

| # | Etapa | Texto (idea) | Figura y animación |
| --- | --- | --- | --- |
| 01 | INPUT | Three worlds, one question. In: elevation maps of the Moon (LOLA), Mars (MOLA) and Earth (Copernicus), plus vegetation, temperature, rock type, dust and ice layers | Tres discos de línea con su código (`MOON`, `MARS`, `EARTH`) y debajo las capas como `RTag`; los discos se dibujan (`svg.createDrawable`) y las etiquetas entran con `stagger` |
| 02 | SAME SQUARE | Every place is cut into the same 32 by 32 km square with one height value every 500 m | Una rejilla 16 × 16 de puntos (representa la de 64 × 64) que aparece desde el centro con `stagger(…, { grid: [16,16], from: 'center' })`, repetida en los tres cuerpos, con la cota `32 KM` |
| 03 | MEASURE | From each square we take six numbers that describe the terrain: how steep, how much relief, how bumpy | Un perfil de terreno que se dibuja y seis barras ("huella") que crecen desde 0, rotuladas con `FEATURE_LABEL` |
| 04 | FILTER | The Moon and Mars have no plants, so Earth squares with vegetation are removed | El `FunnelChart` con contadores que suben (`animate(obj, { value, onUpdate })`) de 497,818 a 40,244 |
| 05 | COMPARE | Each Earth square gets a similarity from 0 to 100 on seven aspects; you choose which ones matter for your mission | Dos huellas lado a lado (blanco y Tierra) que se funden en un `RadarChart` cuyo polígono crece, y un contador de MSI. **Ejemplo real**: blanco `mars-jezero-perseverance` y su mejor análogo del preset `mobility_and_traction`, leídos con `useUniverse()`; mientras carga, la figura queda en esqueleto |
| 06 | OUTPUT | Out: a ranked list of Earth places, each with what matches, where the analogy breaks, and how far it is from a road | Tres tarjetas que entran escalonadas (ranking, "where it breaks" con dos mismatches reales del ejemplo, logística) y un `RButton variant="primary" arrow to="/results"` `OPEN RESULTS` |

Cierre: un `RPanel tone="graphite"` con la idea "What Earth cannot reproduce: gravity, vacuum, radiation" y un enlace a Results `#limits`.

---

## 10. Fase 8 — Challenge y About

### 10.1 `views/ChallengeView.vue`

`PageHero` `code="SEC.02"`, `title="CHALLENGE"`, `subtitle="NASA SPACE APPS CHALLENGE 2026"`.

La página oficial del challenge se renderiza en cliente y no se pudo leer automáticamente. Intenta abrir https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/ con el navegador integrado; **si no obtienes el texto, usa solo el contenido de abajo** (ya verificado contra esa página en `docs/value_proposition.md` y el `README.md`). No añadas cifras de participación ni historia que no puedas leer en una fuente.

1. **`#hackathon` — "THE HACKATHON"**. Copy: "NASA Space Apps Challenge is an annual global hackathon led by NASA. Over one weekend, teams around the world use open data from NASA and its space agency partners to build solutions to challenges about Earth and space. It runs through local events hosted in cities worldwide." Enlace `RButton variant="secondary"` a https://www.spaceappschallenge.org. Después "OUR LOCAL EVENT": NASA Space Apps Sonora 2026, Tec de Monterrey, Campus Sonora Norte, Hermosillo, 13–15 November 2026, enlace a https://spaceappssonora.org/, y el calendario del `README.md` (Friday 13 bootcamp and opening; Saturday 14, 9:00–21:00 hackathon; Sunday 15, 9:00–14:00 pitches) en un `RReadout`.
2. **`#challenge` — "OUR CHALLENGE"**. Título literal: "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars", con botón al enlace oficial. Resumen (del `README.md`): encontrar lugares, entornos o procesos de la Tierra que sirvan de sustitutos de futuras bases lunares o sitios de exploración marciana, caracterizarlos con datos abiertos y explicar tres cosas, en tres `RPanel` numerados `01`–`03`: what makes the analogy strong / where it breaks / how the analog would help prepare Moon or Mars exploration.
3. **"WHAT THE CHALLENGE WARNS ABOUT"**: cuatro puntos (del `README.md`): visual resemblance is not enough; scale matters; well-known analogs (Atacama, Antarctica, Iceland, Hawaii) are already studied; Earth cannot reproduce reduced gravity, vacuum, the thin Martian atmosphere or space radiation.
4. **"WHAT NASA ASKS · WHAT WE DO"**: la tabla de `docs/value_proposition.md` §4 (tres columnas), literal, y la frase diferenciadora del §5 en `.quote`.
5. CTA: `RButton arrow to="/how-it-works"` `SEE HOW IT WORKS`.

### 10.2 `views/AboutView.vue`

`PageHero` `code="SEC.06"`, `title="ENDURANCE CXXV"`, `subtitle="FROM DATA TO ACTION"`. Aside: `Imagotipo.svg` sobre un bloque `--surface-raised`.

Aviso sobre los logos: `Imagotipo.svg` e `Isotipo.svg` contienen un `<text>` "CXXV" con la fuente `Slicker`, que no está en el sistema. Úsalos con `<img>` **sin modificarlos**, revisa en una captura cómo se ven y repórtalo al usuario en el resumen final (necesitan una exportación con el texto convertido a trazados).

1. **`#story` — "THE TEAM"**, copy en `.prose` (traducción aprobada del texto del usuario; cópiala literal a `content/about.ts`):
   - "Endurance CXXV is a team of Computer Science students brought together by an interest in technology, innovation and building solutions to real-world problems."
   - "Our story began in 2024. Since then we have taken part in competitions, innovation events and research experiences."
   - "Each experience has helped us grow as a team, explore new technologies, face different challenges and find out how far we can go working together."
   - "We are eight students: a team that started as a group of friends and keeps looking for new challenges and opportunities to take our ideas further."
   - Cierre en `.quote`: "ENDURANCE CXXV — FROM DATA TO ACTION."
2. **`#track-record` — "TRACK RECORD"**: lista vertical tipo bitácora, cada fila con año en `.label`, evento y, si hay premio, un `RTag tone="signal" bracket`:
   - 2024 · NASA Space Apps Challenge 2024
   - 2025 · Summer of Research 2025 — Universidad de Guadalajara
   - 2025 · NASA Space Apps Challenge 2025
   - 2026 · TE AI Cup 2026 · `[1ST PLACE · INTERNATIONAL]`
   - 2026 · SmartCity Hackathon 2026 · `[PEOPLE'S CHOICE]`
   - 2026 · Health Systems Innovation Lab Hackathon 2026 · `[3RD PLACE]`
   - 2026 · NASA Space Apps Challenge 2026 · `[IN PROGRESS]` (tone `outline`)
3. **`#members` — "CREW"**: rejilla de 4 columnas (2 en tablet, 1 en móvil) con **8 ranuras** desde `content/about.ts`:

   | Nombre | Foto (`src/assets/`) | LinkedIn |
   | --- | --- | --- |
   | Ángel Fernando Bórquez Guerrero | `fernando_borquez.png` | https://www.linkedin.com/in/fernandoborquez/ |
   | Elías Peregrina Cázares | `elias_peregrina.jpeg` | https://www.linkedin.com/in/el%C3%ADas-peregrina-c%C3%A1zares-4886503a7/ |
   | Emily Margarita Beltrán Zazueta | `emily_beltran.jpeg` | https://www.linkedin.com/in/emily-beltran-b712a2421/ |
   | Flor María Machado Félix | `flor_machado.jpeg` | https://www.linkedin.com/in/flor-maria-machado-felix-a318633a8/ |
   | Javier Leonardo Miranda Sánchez | `javier_miranda.jpeg` | https://www.linkedin.com/in/javier-miranda-sanchez-201aa1383/ |
   | Owen Adiel Solis Zatarain | `owen_solis.png` | https://www.linkedin.com/in/owen-solis/ |
   | (pendiente) | — | — |
   | (pendiente) | — | — |

   Tarjeta: foto cuadrada en gris con marco y chaflán, código `CREW.01`…, nombre en `.headline` pequeño y un enlace `LINKEDIN` con `RGlyph name="chevron-right"` (`target="_blank" rel="noreferrer"`, `aria-label="LinkedIn profile of <name>"`). Las dos pendientes usan `RFrame ratio="1 / 1" caption="CREW.07 · [PENDING]"`. Añadir un integrante debe ser solo añadir un objeto al arreglo.

   Las fotos originales pesan hasta 2 MB. Genera copias optimizadas (ImageMagick está instalado) y usa esas, sin tocar las originales:
   ```bash
   mkdir -p app/src/assets/team && for f in app/src/assets/*.{png,jpeg}; do magick "$f" -resize 640x640^ -gravity north -extent 640x640 -quality 82 "app/src/assets/team/$(basename "${f%.*}").webp"; done
   ```
   Revisa cada recorte en una captura; si corta una cara, cambia `-gravity north` por `center` en esa foto.
4. **`#acknowledgements` — "ACKNOWLEDGEMENTS"**, la última sección de la página, en un `RPanel tone="graphite"` ancho con `label="ACARUS · UNIVERSIDAD DE SONORA"`: "This project was developed in collaboration with ACARUS (Área de Cómputo de Alto Rendimiento de la Universidad de Sonora), using Yuca, the University of Sonora's high-performance computing cluster. It would not have been possible without their support." y un `RButton variant="secondary" href="https://acarus.unison.mx/"` `VISIT ACARUS`.

---

## 11. Orden de ejecución y criterios de aceptación

| Fase | Trabajo | Hecho cuando |
| --- | --- | --- |
| **0** Preparación | `git checkout -b feat/website-vue`. Copiar este plan a `docs/plan_t18_website.md`. Guardar la referencia RETÍCULA en `docs/design-system/reticula/` (§2). Impacto GitNexus de los símbolos de §5.1 y de `App` | Los archivos existen; el reporte de impacto está escrito en la respuesta |
| **1** Andamiaje | §1; borrar los archivos React; `main.ts`, `App.vue`, `router.ts`, estilos base (§2.1–2.4, 2.6), `AppHeader`, `AppFooter`, `PageHero`, `SectionBlock`, siete vistas con solo su `PageHero` | `npm --prefix app run build` pasa; las siete rutas abren sin errores de consola |
| **2** Kit RETÍCULA | §2.5 y una ruta temporal `/kit` que muestra todos los componentes en todas sus variantes | Cada componente coincide con su `preview.html` de referencia; quitar `/kit` en la fase 9 |
| **3** Home | §4 | Sol y 5 planetas del mismo tamaño enlazan a su sección; los planetas giran sin trasladarse; etiquetas sin solaparse a 1366 × 768 y 1920 × 1080; raíl en 375 px; con reduced motion la escena está completa y quieta |
| **4** Results | §5 y §6 | El explorador se comporta como el de React (lista de §5.2); `summary()` da las cifras esperadas de §6.2; el MSI en pantalla de 4 parejas coincide con `msi_by_preset` del JSON |
| **5** Algorithm | §7 | 11 pasos; todas las fórmulas renderizan sin texto rojo de error de KaTeX; cada bloque de código muestra la función correcta y completa |
| **6** Data | §8 | Tablas completas; 8 hallazgos; gráficas con valores; ranuras de figura con `RFrame` |
| **7** How It Works | §9 | 6 etapas se animan al entrar en pantalla; el ejemplo de Jezero usa datos reales; sin fórmulas ni código |
| **8** Challenge y About | §10 | Copy literal; 6 fotos optimizadas + 2 pendientes; agradecimiento a ACARUS al final de About |
| **9** Cierre | Quitar `/kit`. Revisión responsive, accesibilidad y consola (§12). Actualizar `README.md` (stack de `app/`: Vue, Vite, TypeScript, Sass, anime.js, Leaflet; tabla "Repository layout"), fila T10 de `docs/handoff.md`, y una entrada nueva al inicio de `docs/logbook.md` (qué se hizo, qué se verificó, qué queda pendiente). `detect-changes` y commit final | Todo §12 en verde |

---

## 12. Verificación de extremo a extremo

1. **Build**: `npm --prefix app run build` sin errores de `vue-tsc` ni de Vite.
2. **Servidor**: `preview_start` con `name: "app"` (ya está en `.claude/launch.json`). No uses Bash para levantar el servidor.
3. **Por cada ruta** (`#/`, `#/results`, `#/challenge`, `#/how-it-works`, `#/algorithm`, `#/data`, `#/about`): `read_console_messages` con `onlyErrors` (debe venir vacío), `read_page` para estructura y nombres accesibles, y captura a **1366 × 768** y a **375 × 812** (`resize_window`). Sin scroll horizontal en móvil.
4. **Home**: clic en el sol y en cada planeta navega a la ruta correcta; foco con Tab recorre los seis cuerpos y Enter navega; con `javascript_tool` comprueba que el `rx` de un `.planet__meridian` cambia entre dos lecturas separadas 500 ms y que el `transform` del `<g>` del planeta **no** cambia de posición.
5. **Results**: mover un deslizador reordena el ranking; cambiar MARS / MOON deshabilita Thermal y Dust en la Luna; el interruptor de explicaciones abre los 10 paneles y recuerda el estado al recargar; clic en un marcador del mapa cambia la ficha; comprobación numérica en consola de que `msi(analog, fullWeights(preset.weights), target.available_dims)` iguala a `analog.msi_by_preset[preset]` (error < 0.001) en 4 parejas.
6. **Algorithm**: `document.querySelectorAll('.katex-error').length === 0`; cada `CodeBlock` empieza por `def`, `class`, `@` o `export`.
7. **Reglas de diseño**, con búsquedas en `app/src`: ningún `border-radius` fuera de `_reticula.scss` y el sistema solar; ningún `box-shadow`, `blur(`, `linear-gradient` (salvo `RHazard`); ningún color hexadecimal fuera de `_tokens.scss`; ningún emoji; ningún `color: var(--signal)` aplicado a texto.
8. **Movimiento reducido**: con `resize_window`/emulación o forzando `matchMedia`, Home y How It Works quedan estáticos y completos.
9. **GitNexus**: `node .gitnexus/run.cjs detect-changes --scope all --repo .` antes de cada commit (repetir si devuelve `partial` o `truncated`); al final, `node .gitnexus/run.cjs analyze --index-only`.
10. **Pipeline intacto**: `git status` no muestra cambios en `pipeline/`, `tests/`, `jobs/`, `tools/` ni `app/public/data/`.

---

## 13. Pendientes que Haiku debe reportar al usuario al terminar

- Nombre, foto y LinkedIn de los **dos integrantes** que faltan (el texto ya dice "eight students").
- **Logo del proyecto**: hay un placeholder en `AppHeader`.
- Los SVG del equipo usan la fuente `Slicker` en el texto "CXXV": hace falta exportarlos con el texto en trazados.
- Las **figuras del EDA** (mapas PNG) viven en Yuca: copiarlas a `app/public/figures/`.
- El texto oficial del challenge no se pudo leer automáticamente; la página Challenge usa el contenido del README y de `value_proposition.md`.
- Librerías añadidas además de las cuatro pedidas: `vue-router`, `leaflet`, `katex`, `highlight.js`.
- No se hizo push ni PR; el despliegue (GitHub Pages u otro) queda fuera de este plan, pero `base: "./"` y el enrutado por hash lo dejan listo.
