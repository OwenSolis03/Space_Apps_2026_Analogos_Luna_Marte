# T17: plain-language explanations in the Scenario panel

Specification written by Claude on 2026-11-14 for the coding agent. It only touches the app (`app/`). No pipeline change, no re-run.

**Goal.** Someone who does not code and is not a planetary scientist (a judge, a teammate, a visitor) must be able to open the Explorer and understand, for every control in the left panel: **what it is, what it measures, what moving it does, and why it matters for a mission.** Today the panel shows jargon (`elevation σ and TRI`, `NDVI`, `hypsometry`, `MSI`, `λ`) with no explanation.

**Scope.** The panel in `app/src/components/ScenarioPanel.tsx`: mission case buttons, the seven dimension sliders, "Minimum MSI", "Prefer sites near a road" and "Only new candidates". Nothing else changes in this task.

**Language.** The app is in English (the submission is in English), so all copy below is in English. Use it **as written**; if a sentence does not fit, shorten it, but do not add claims. Every number in the copy was checked against the code and the export of run 2242506.

---

## 1. What the user will see

1. A short **intro line** at the top of the panel explaining the score in one sentence.
2. A **"Show explanations"** switch next to the panel title that opens or closes all explanations at once (useful when presenting on a projector).
3. Next to each control, an **info button** (a small circled "i", drawn as an inline SVG, not an emoji or a font glyph) that opens a short explanation **inline, right below the control**. A second click closes it. Several can be open at the same time.
4. The grey hint next to each slider name is rewritten in plain words (§3.1). The technical terms move inside the explanation.
5. The percentage at the right of each slider gets a one-line explanation (§3.3).

**Why inline and not hover tooltips:** tooltips do not work on touch screens, disappear while you move the slider, and are hard to reach with the keyboard or a screen reader. A disclosure button that expands text below the control works everywhere.

---

## 2. Files

| File | Change |
| --- | --- |
| `app/src/lib/explanations.ts` | **New.** All the copy of §3 as typed constants. No JSX in this file |
| `app/src/components/InfoToggle.tsx` | **New.** The info button + the expandable explanation block (§4) |
| `app/src/components/ScenarioPanel.tsx` | Uses `InfoToggle` for every control; intro line; "Show explanations" switch; state of open explanations |
| `app/src/lib/content.ts` | Replace the `hint` strings of `DIM_LABEL` with the plain ones in §3.1 (the radar and other places keep using `label`) |
| `app/src/index.css` | Only if needed: one class for the explanation block, using the existing tokens (`--surface-2`, `--line`, `--muted`, `--fg`). No new colours |

Do not touch the pipeline, the data, `msi.ts`, `Dossier.tsx` or `Radar.tsx` in this task.

---

## 3. The copy

### 3.0 Intro line (top of the panel, under the legend "Mission case")

> Each Earth place gets a similarity score from 0 to 100 (the MSI) against the Moon or Mars site you pick. Choose a mission case, or move the sliders to decide which aspects count most.

"Show explanations" switch label: **Show explanations**. Its accessible name: "Show all explanations in this panel".

### 3.1 New short hints (visible next to each slider name)

| Dimension | Label (unchanged) | New hint |
| --- | --- | --- |
| `topography` | Topography | slope and shape of the land |
| `roughness` | Roughness | how bumpy the ground is |
| `environment` | Aridity | no plants |
| `thermal` | Thermal | day vs night temperature swing |
| `geology` | Geology | type of rock |
| `dust` | Dust | dust in the air and its seasons |
| `ice` | Ice | water ice and very cold spots |

### 3.2 Explanations, one per control

Each explanation has the same four short parts, always in this order and with these exact headings, so people learn where to look:

- **What it is**
- **How we measure it**
- **What the slider does**
- **Why it matters**

Store them in `explanations.ts` as:

```ts
export interface Explanation {
  what: string;
  measure: string;
  slider: string;
  why: string;
  note?: string; // optional extra line, shown in a muted style (limits, availability)
}
export const DIM_EXPLANATION: Record<Dimension, Explanation> = { ... };
export const CONTROL_EXPLANATION: Record<"minScore" | "road" | "newOnly" | "weightsShare", Explanation | string> = { ... };
export const PRESET_EXPLANATION: Record<string, string> = { ... };
export const INTRO = "...";
```

#### Topography

- **What it is:** The shape of the land: how steep it is and how much it rises and falls.
- **How we measure it:** We cut every place into a 32 by 32 km square with one height value every 500 m, the same on Earth, the Moon and Mars. From that we take the average slope, the steepest parts, the difference between the highest and lowest points, and whether the square is mostly high ground or mostly low ground. Heights come from laser altimeters (MOLA on Mars, LOLA on the Moon) and the Copernicus elevation model on Earth.
- **What the slider does:** The higher it is, the more the ranking prefers Earth places whose land has the same shape as the target.
- **Why it matters:** Landers need gentle slopes, rovers have a maximum slope they can climb, and the shape of the land decides where you can drive, land and build.

#### Roughness

- **What it is:** How bumpy the ground is once the general tilt is removed: hills, ridges and crater rims inside the square.
- **How we measure it:** From the same 32 km height grid: how much the ground goes up and down around a flat fit, and how different each point is from its neighbours.
- **What the slider does:** The higher it is, the more the ranking prefers places with the same amount of bumpiness.
- **Why it matters:** Bumpy ground is harder to drive and riskier to land on. Smooth ground is good for long drives and for testing how a rover keeps track of where it is.
- **Note:** With one value every 500 m this sees hills and ridges, not individual rocks.

#### Aridity

- **What it is:** Whether the Earth place is bare ground, like the Moon and Mars, or covered with plants.
- **How we measure it:** NASA's MODIS satellite measures how green the ground is every month. We take the greenest month of 2023: the greener the place, the lower this score. Ice sheets count as bare because nothing grows there.
- **What the slider does:** The higher it is, the more it pushes down places with vegetation.
- **Why it matters:** The Moon and Mars have no plants. A field test on bare rock and soil is much closer to the real thing than one in a forest or a field.

#### Thermal

- **What it is:** How much the ground temperature changes between day and night.
- **How we measure it:** Mars: the THEMIS camera on Mars Odyssey, which sees heat. Earth: NASA's MODIS satellite. The two planets have very different temperatures, so we do not compare degrees: we compare how extreme each place is within its own planet, from 0 (smallest swing) to 1 (largest swing).
- **What the slider does:** The higher it is, the more it prefers Earth places that are as extreme at home as the target is on Mars.
- **Why it matters:** On Mars a large swing usually means fine dust or sand, and a small swing means solid rock that keeps the heat. Equipment also has to survive being heated and cooled every day.
- **Note:** Only for Mars. There is no matching dataset for the Moon, so it is switched off there.

#### Geology

- **What it is:** The type of rock that covers the region: for example volcanic, sedimentary, crystalline or impact rock.
- **How we measure it:** Geologic maps of each body (GLiM for Earth, USGS maps for the Moon and Mars), translated into 8 rock families shared by the three bodies. Similar families score high, different ones score low.
- **What the slider does:** The higher it is, the more it prefers Earth places with the same kind of rock as the target.
- **Why it matters:** The rock decides the soil the wheels drive on, what the instruments will find, and what could be used as building material.
- **Note:** These are regional maps: they say what most of the region is made of, not what each outcrop is.

#### Dust

- **What it is:** How dusty the air is and how that changes through the year.
- **How we measure it:** Mars: a record of dust in the Martian atmosphere over several years. Earth: dust and haze measured by NASA's MODIS satellite. As with temperature, each place is compared within its own planet: how dusty it is, how much the dust changes between seasons, and when its dusty season comes.
- **What the slider does:** The higher it is, the more it prefers Earth places whose dust behaves like the target's.
- **Why it matters:** Dust covers solar panels, wears out moving parts and, in storms, blocks the light. Dusty places on Earth are where those problems can be tested.
- **Note:** Only for Mars. Places with no dust measurement on Earth (for example ice sheets, where the satellite cannot measure it) score 0 here instead of being skipped.

#### Ice

- **What it is:** Whether there is water ice, and very cold spots (cold traps) where ice can last.
- **How we measure it:** Moon: temperatures from the Diviner instrument on NASA's Lunar Reconnaissance Orbiter near the south pole. Mars: mapped shallow ice. Earth: temperatures from MODIS and mapped ice.
- **What the slider does:** The higher it is, the more it prefers cold, icy Earth places for targets that have ice.
- **Why it matters:** Water can be turned into drinking water, oxygen and rocket fuel. Finding and extracting it is key for a permanent base.
- **Note:** Only sites with ice data can be scored on this. In the "Water ice and cold traps" case, sites without ice data are not ranked, and a note under the ranking lists them.

#### Percentage at the right of each slider (`weightsShare`, one line, shown once under the "Weights by dimension" legend)

> The percentage is how much of the score each aspect counts right now. They always add up to 100%, so raising one lowers the share of the others.

#### Minimum MSI

- **What it is:** A filter on the score.
- **How we measure it:** The MSI goes from 0 to 100. 100 means the Earth place matches the target on everything the mission case looks at; it does not mean the place is "better" in general.
- **What the slider does:** Hides targets whose best Earth match scores below the number you choose.
- **Why it matters:** It lets you focus on the clearest matches. Scores are only comparable within the same mission case.

#### Prefer sites near a road

- **What it is:** A bonus for Earth places that are easy to reach.
- **How we measure it:** Distance from each place to the nearest road (Natural Earth map).
- **What the slider does:** At 0, distance is ignored. At the maximum, a place 50 km from a road keeps about 88% of its score, one 100 km away about 81%, and one 300 km away about 72%. Places next to a road keep their full score.
- **Why it matters:** Field campaigns near a road are cheaper, safer and can be repeated more often than expeditions to remote places.

(The "λ = 0.00" readout stays, but add the text "(0 = off)" next to it.)

#### Only new candidates

- **What it is:** A switch to hide places that are already famous as Moon or Mars analogs.
- **How we measure it:** We mark Earth places inside nine well-known analog regions: the Atacama Desert, Iceland, the McMurdo Dry Valleys, Devon Island, Svalbard, Utah (MDRS), the Mojave Desert, Meteor Crater and the Pilbara.
- **What the slider does:** When it is on, those places disappear from the results and only new candidates remain.
- **Why it matters:** The challenge asks to go beyond the sites everyone already uses. This shows what is left when the famous ones are taken out.

(For this control the third heading reads **What the switch does** instead of "What the slider does". For "Minimum MSI" keep "What the slider does".)

### 3.3 Mission cases (`PRESET_EXPLANATION`)

Show the explanation of the **selected** case in one line under the case buttons (not behind an info button), so it is always visible:

| Preset | Text |
| --- | --- |
| `mobility_and_traction` | Where to test how rovers drive: mostly the shape and bumpiness of the land, plus rock type. |
| `construction_and_base` | Where to rehearse landing and building a base: mostly gentle, stable land and the type of rock. |
| `geology_and_materials` | Where to train geologists and test instruments: mostly the type of rock. |
| `dust_and_seasons` | Where to test equipment against dust and seasonal storms: mostly dust and temperature swings. Mars only. |
| `isru_and_ice` | Where to practise finding and using water ice: mostly ice and very cold spots. Only sites with ice data are ranked. |

### 3.4 Disabled dimensions

When a dimension is off for the selected body, keep the existing "not modelled for the Moon" text and make the info button still work, so the explanation (with its **Note**) tells why it is off.

---

## 4. Component `InfoToggle`

```tsx
interface InfoToggleProps {
  id: string;                 // unique, e.g. "dim-topography"
  title: string;              // e.g. "Topography" (used in the accessible name)
  open: boolean;
  onToggle: () => void;
  explanation: Explanation;
  actionHeading?: string;     // default "What the slider does"
}
```

It renders two things that the panel places in its layout:

1. **The button** (`<InfoButton>`), placed on the same line as the control's label:
   - `<button type="button" aria-expanded={open} aria-controls={`exp-${id}`}>` with an inline SVG of a circled "i" (16 px icon) and `aria-label={`What does ${title} mean?`}`.
   - Hit area at least 24 by 24 px (use padding; on screens under 640 px wide, 32 by 32 px).
   - Visible focus ring using the existing `--ring` / accent outline style from `index.css`.
   - Must not be inside the `<label>` of the slider (a button inside a label breaks clicking and screen readers). Put label text and button side by side in a flex row.
2. **The panel** (`<InfoPanel>`), placed right below the slider:
   - `<div id={`exp-${id}`} role="region" aria-label={`${title}: explanation`} hidden={!open}>`.
   - Four short blocks: a small bold heading (`What it is`, `How we measure it`, the action heading, `Why it matters`) followed by its text; then `note` in muted text if present.
   - Style: `rounded-panel bg-surface-2 p-3 text-sm leading-relaxed`, max width of the panel, no animation that moves the sliders while dragging (a 150 ms fade is fine; respect `prefers-reduced-motion`).

State lives in `ScenarioPanel`: `const [open, setOpen] = useState<Set<string>>(new Set())`. The "Show explanations" switch sets all keys open or closes all. Keep the switch's checked state derived: on when every key is open.

Optional (do it only if everything else is done): remember the switch in `localStorage` under `paf.explanations`, wrapped in `try/catch` so the app works when storage is blocked.

---

## 5. Rules for the copy in code

- **No em dashes or en dashes** in strings or comments (`—`, `–`). The project's design hook rejects them on write. Use commas, colons, "to" or a plain hyphen.
- **No emoji.** The info icon is an inline SVG.
- Keep the technical names (`MSI`, `NDVI`, `TRI`, `σ`) out of the visible hints. They may appear inside explanations only where already written in §3.
- Do not invent numbers. The road percentages come from `MSI · (1 − λ + λ·exp(−km/100))` with λ = 0.3 and are already rounded in §3.2.
- If `metadata.dimensions` in the export changes a dimension's sources, update the "How we measure it" line in the same commit.

---

## 6. Acceptance

**Functional**

- Every control listed in "Scope" has an info button and an explanation with the four headings (Minimum MSI, road and new-candidates included).
- "Show explanations" opens and closes all of them; individual buttons still work afterwards.
- The selected mission case shows its one-line explanation, and it changes when the case changes.
- On the Moon, Thermal and Dust stay disabled but their info buttons work and show the "Only for Mars" note.
- Moving a slider does not open or close anything and does not move the slider under the pointer.

**Accessibility**

- Keyboard only: Tab reaches every info button after its slider label; Enter or Space toggles it; `aria-expanded` changes; focus stays on the button.
- Screen reader name of each button: "What does Topography mean?", and so on.
- Text contrast of the explanation passes WCAG AA (4.5:1) in both the light and the dark theme (the app follows the system setting; use `--fg` for body text, `--muted` only for the note).

**Layout**

- At 375 px wide (phone) and at 1366 by 768 (projector) the panel has no horizontal scroll and the text wraps cleanly.
- With all explanations open, the page scrolls normally and the maps and ranking are still usable.

**Build**

- `npx tsc -b` and `npm --prefix app run build` pass; no console errors in the browser.

**Reading test** (do it with someone from the team who is not on the code side, or ask Owen to): they open the page, read two explanations of their choice and can say in their own words what that slider does. Note in the logbook who tested it and what they said was unclear; fix the copy if needed.

---

## 7. Commits and docs

1. `T17: plain-language explanations in the Scenario panel` (code + `explanations.ts`).
2. Logbook entry in `docs/logbook.md` (English): what changed, why, the reading test and its result, screenshots not needed.

Do not change the pipeline, the export or the data in this task.
