# T16: missing-data policy for the MSI

Specification written by Claude on 2026-11-14 for the coding agent. Implement it task by task, in order. Do not change anything that is not listed here; if something here looks wrong, stop and report instead of improvising.

**Read first:** [plan_t7_t8.md](plan_t7_t8.md) (MSI, presets, selection), [plan_t12_t15.md](plan_t12_t15.md) (geology, dust, ice), [pipeline.md](pipeline.md) (runs), and the code in `pipeline/match.py` (`msi`, `select_by_preset`, `match_all`), `pipeline/export.py` (`sub_scores`, `run_t7_checks`), `pipeline/dust.py` (`S_dust`), `pipeline/ice.py` (`S_ice`).

---

## 0. Summary

Today, when a sub-score is missing, `msi()` **drops that dimension and renormalises the weights over the rest**. Missing data therefore acts as a free pass:

- **Dust preset sends Mars targets to Antarctica.** MODIS Deep Blue AOD has no retrievals over ice and snow, so 739 Antarctic patches have no dust score. The preset puts 40% of its weight on dust; for those patches that 40% vanishes and they win on terrain, aridity and thermal.
- **Ice preset sends Mars targets to the Sahara.** Only 1 of 38 Mars targets has mapped ice. For the other 37 the preset's 50% ice weight vanishes and the ranking is decided by terrain and aridity: deserts.

T16 separates three different reasons for a missing value and treats each one explicitly:

| Case | Example | New rule |
| --- | --- | --- |
| **A. Not applicable to the body** | Dust or thermal for a Moon target | Dimension is ignored (as today). Presets whose `applies_to` excludes the body are not computed for that body |
| **B. Missing on the target** | Mars target with no mapped ice; Moon target outside Diviner coverage | Dimension is ignored, but the preset's **coverage** drops. If coverage < `MIN_PRESET_COVERAGE` (0.6) the target is **not ranked** for that preset |
| **C. Missing on the Earth patch while the target has it** | Antarctic patch with no dust value for a Mars target that has dust | Sub-score counts as **`EARTH_MISSING_SCORE` = 0.0** ("no evidence, no credit") instead of being dropped |

The selection of the top 30 analogs per preset changes with the new MSI, so the fix must be made in the pipeline and the export re-run on Yuca. The app only mirrors the rule.

---

## 1. Evidence (from `app/public/data/analogs_universe.json`, run 2242490)

Measured on 2026-11-14 with the scoring formula the app and the pipeline share (`Σ w·S / Σ w` over non-null sub-scores; it reproduces `msi_by_preset` for all 25,050 analog-preset pairs, max error 0.0009).

**Top-1 analog per target (using all exported analogs):**

| Body / preset | Top-1 countries | Top-1 analogs with the preset's key dimension null |
| --- | --- | --- |
| Mars / `dust_and_seasons` | Antarctica 17, Mali 3, Algeria 3, … | dust null in 19/38; **all 17 Antarctic ones have dust null** |
| Mars / `isru_and_ice` | Antarctica 17, China 6, Libya 3, Saudi Arabia 3, … | ice null in 37/38 (target side) |
| Moon / `isru_and_ice` | Antarctica 11, USA 3, China 3, … | ice null in 30/38 (target side) |
| Moon / `dust_and_seasons` | (computed today although `applies_to = ["Mars"]`) | dust null in 38/38 |

**Where values are missing:**

| Body | Target side (targets that have the dimension) | Earth side (analog null while the target has the dimension) |
| --- | --- | --- |
| Mars (38 targets) | topography, roughness, environment, geology, dust: 38; thermal: 32 (THEMIS night only 60°N–60°S); **ice: 1** (Arcadia SWIM) | **dust: 1,057 / 2,908** (739 Antarctica, 82 Greenland, 78 Canada, 100 no country); **geology: 180 / 2,908**; thermal 0; ice 0 |
| Moon (38 targets) | topography, roughness, environment, geology: 38; **ice: 8** (Diviner, 76–90°S); dust, thermal: not applicable | geology: 16 / 2,102; ice 0 |

**Preset coverage today** (share of the preset's weight, over the dimensions that apply to the body, that the target can actually be scored on):

| Body | Preset | Min | Median | Targets below 0.6 |
| --- | --- | --- | --- | --- |
| Mars | `dust_and_seasons` | 0.80 | 1.00 | 0 |
| Mars | `isru_and_ice` | 0.50 | 0.50 | **37** |
| Moon | `isru_and_ice` | 0.50 | 0.50 | **30** |
| both | mobility, construction, geology | ≥ 0.95 | 1.00 | 0 |

The verification script in §9.3 is for the new export: on run 2242490 it runs without errors but prints `status={'?': 38}` for every preset, because `preset_status` does not exist yet. Hard check 12 already passes on 2242490 (0 violations, legacy rule).

---

## 2. Definitions

All of these live in `pipeline/match.py` next to the other constants.

```python
EARTH_MISSING_SCORE: float = 0.0       # case C
MIN_PRESET_COVERAGE: float = 0.6       # case B
DIMENSION_BODIES: dict[str, tuple[str, ...]] = {d["key"]: tuple(d["bodies"]) for d in DIMENSIONS}
```

**Dimensions that apply to a body** (case A): `DIMENSION_BODIES[dim]` contains the body. Today: thermal and dust are Mars-only; the rest apply to both.

**Dimensions available for a target** (case B). A dimension is available when it applies to the body **and** the target has the inputs that dimension needs:

| Dimension | Available when |
| --- | --- |
| `topography`, `roughness` | always (targets with non-finite terrain are already skipped in `match_all`) |
| `environment` | always (it only uses the Earth patch's NDVI) |
| `thermal` | body is Mars **and** `tv.zt_t` is finite |
| `geology` | `tv.geo_class` is not None **and** is a key of `GEO_SIMILARITY` |
| `dust` | body is Mars **and** `tv.dust_level_rank` and `tv.dust_season_rank` are finite (phase may be NaN: `S_dust` already handles it) |
| `ice` | `tv.ice_t` is finite **and**: Moon → `tv.cold_rank` finite; Mars → `tv.ice_t > 0` |

These rules must match exactly when `S_*` functions return NaN for target-side reasons (see `ice_scores`, `dust_scores`, `geology_scores`, `dimension_scores`). If you find a difference, the rule in this table wins and the scorer must be aligned, with a test.

**Preset coverage** for a target:

```
applicable_w = Σ w_d  over d with w_d > 0 and body ∈ DIMENSION_BODIES[d]
available_w  = Σ w_d  over d with w_d > 0 and d ∈ available_dims(target)
coverage     = available_w / applicable_w        (1.0 if applicable_w == 0)
```

**Preset status** for a target, one of:

| Status | When |
| --- | --- |
| `ok` | body ∈ preset `applies_to` and coverage ≥ `MIN_PRESET_COVERAGE` |
| `not_applicable_body` | body ∉ preset `applies_to` (today: `dust_and_seasons` on the Moon) |
| `insufficient_target_data` | coverage < `MIN_PRESET_COVERAGE` |

**Environment exception (keep as is).** When the Earth patch has no NDVI (`ndvi_missing`, mostly ice sheets), `dimension_scores` sets `S_environment = 1.0`. This is *not* case C: MODIS fills NDVI over permanent snow and ice, where there is no vegetation, so "bare ground" holds. Do not change this. Ice-covered surfaces are handled by the geology dimension (class `ICE`) and the ice cap in `select_diverse`. Mention it in `metadata.scoring_policy` (§5).

---

## 3. Task T16.1: scoring in `pipeline/match.py`

### 3.1 `available_dims(tv: TargetVec) -> frozenset[str]`

New pure function implementing the table in §2. Place it after `target_vec_from_row`. Use `np.isfinite` on floats and `_as_class` semantics for geology.

### 3.2 `preset_status(weights, body, applies_to, available) -> tuple[str, float, list[str]]`

New pure function. Returns `(status, coverage, missing_dims)` where `missing_dims` is the sorted list of dimensions with `w > 0` that apply to the body but are not available (empty for `ok` with coverage 1.0). For `not_applicable_body` return coverage `0.0` and `missing_dims = []`. Round coverage to 3 decimals only at export time, not here.

### 3.3 `msi()` gets the case-C rule

New signature (keyword-only additions, so existing calls keep working):

```python
def msi(
    scores: dict[str, np.ndarray | float],
    weights: dict[str, float],
    *,
    target_dims: frozenset[str] | set[str] | None = None,
    earth_missing_score: float = EARTH_MISSING_SCORE,
) -> np.ndarray | float:
```

Behaviour, for every dimension `d` with `w_d > 0` and `d in scores`:

- If `target_dims is None`: **old behaviour** (skip non-finite). Keep it only for backwards compatibility and existing tests; production code must always pass `target_dims`.
- If `d not in target_dims`: skip it (cases A and B), exactly like today.
- If `d in target_dims` and the value is finite: add `w_d · S`, `w_d` to num and den.
- If `d in target_dims` and the value is not finite: add `w_d · earth_missing_score` to num and `w_d` to den (case C).

Both the scalar branch and the vector branch must implement it. The result stays `nan` only when `den == 0`.

Pseudocode for the vector branch:

```python
for dim, w in weights.items():
    if w <= 0.0 or dim not in raw_arrays:
        continue
    if target_dims is not None and dim not in target_dims:
        continue
    arr = np.broadcast_to(raw_arrays[dim], (length,))
    finite = np.isfinite(arr)
    if target_dims is None:
        num_arr[finite] += w * arr[finite]
        den_arr[finite] += w
    else:
        num_arr += w * np.where(finite, arr, earth_missing_score)
        den_arr += w
```

### 3.4 `select_by_preset()` respects status

New signature:

```python
def select_by_preset(
    scores: dict[str, np.ndarray],
    ea: EarthArrays,
    presets: dict[str, dict[str, object]] | None = None,
    *,
    body: str | None = None,
    target_dims: frozenset[str] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, list[int]], dict[str, dict[str, object]]]:
```

For each preset:

1. If `body` and `target_dims` are given, compute `(status, coverage, missing)` with `preset_status`.
2. If `status != "ok"`: `msi_by_preset[pkey] = np.full(n, np.nan)`, `selected[pkey] = []`.
3. Else: `msi_vals = msi(scores, weights, target_dims=target_dims)` and the selection exactly as today (ordering, `select_diverse`, ice cap except `ICE_CAP_EXEMPT_PRESETS`).
4. Return a third dict `status_by_preset[pkey] = {"status": ..., "coverage": ..., "missing_dims": [...]}`.

When `body`/`target_dims` are `None` keep today's behaviour (status `ok`, coverage `1.0`) so older tests keep passing.

### 3.5 `match_all()` wiring

- After `tv = target_vec_from_row(...)`: `tdims = available_dims(tv)`.
- Call `select_by_preset(scores, ea, body=tv.body, target_dims=tdims)`.
- For every exported row add:
  - `earth_missing_dims`: comma-separated sorted list of `d in tdims` where `scores[d][g_idx]` is not finite (case C for this pair). Empty string if none.
  - `msi_{pkey}`: the value from the new `msi_by_preset` (NaN for presets not `ok`).
- Collect per-target status in a list of dicts `{"target_id", "preset", "status", "coverage", "missing_dims", "available_dims"}` and write it as `target_presets.csv` in `OUT_DIR` (from `main()`, next to the existing outputs). Also pass it to `meta_out["preset_status"]`.
- `S_{dim}` columns keep the raw value (NaN stays NaN). The 0.0 is applied only inside `msi`; the export shows the raw `null` plus `earth_missing_dims`, so the app can explain it.

### 3.6 Mismatches for case C

In the loop that builds `mm`, after `layer_mismatches(...)`, append one entry per dimension in `earth_missing_dims`:

```python
{"feature": f"no_earth_data:{dim}", "earth": None, "target": None, "z_diff": None}
```

Keep `json.dumps(mm, allow_nan=False)` working (no NaN in these entries).

---

## 4. Task T16.2: export contract in `pipeline/export.py`

Additive changes only; nothing existing is removed or renamed.

**Per target** (`targets[i]`):

```json
"available_dims": ["topography", "roughness", "environment", "thermal", "geology", "dust"],
"preset_status": {
  "mobility_and_traction": {"status": "ok", "coverage": 1.0, "missing_dims": []},
  "dust_and_seasons":      {"status": "ok", "coverage": 1.0, "missing_dims": []},
  "isru_and_ice":          {"status": "insufficient_target_data", "coverage": 0.5, "missing_dims": ["ice"]}
}
```

For Moon targets `dust_and_seasons` has `{"status": "not_applicable_body", "coverage": 0.0, "missing_dims": []}`. Every preset key must be present for every target.

**Per analog** (`targets[i].analogs[j]`):

- `"earth_missing_dims": ["dust"]`: list, empty when none.
- `msi_by_preset[pkey]` is `null` for presets whose status is not `ok` for this target.
- `selected_by` only lists presets where the analog was actually selected (already true; it can now be empty for none, which means the analog came from another preset).
- `sub_scores` unchanged (raw values, `null` where missing).
- `mismatches` may include the new `no_earth_data:<dim>` entries.

**Sorting of `analogs`.** Today they are sorted by `msi_by_preset["mobility_and_traction"]`. Keep that key, treating `null` as −1 (already handled).

**Metadata.** Add:

```json
"scoring_policy": {
  "earth_missing_score": 0.0,
  "min_preset_coverage": 0.6,
  "rules": [
    "A dimension that does not apply to the target's body is ignored, and presets are only computed for the bodies in applies_to.",
    "A dimension the target has no data for is ignored, but if the preset weight left is below 60% the target is not ranked for that preset.",
    "If the target has a dimension and the Earth patch does not, that dimension scores 0 (no evidence, no credit).",
    "Missing NDVI (permanent snow and ice) still counts as bare ground for the aridity dimension."
  ]
}
```

and `"preset_status_summary"`: for each body and preset, counts of targets by status (e.g. `{"Mars": {"isru_and_ice": {"ok": 1, "insufficient_target_data": 37}}, ...}`).

Update the `Universe` description at the top of `export.py` and the schema section in `plan_t7_t8.md` (or wherever the export schema is documented) with these fields.

---

## 5. Task T16.3: checks in `run_t7_checks`

Keep all existing checks. If an existing check fails *only* because of T16 (for example a soft check that expected an Antarctic analog), do not loosen it silently: report it in the logbook with the before/after values and propose the change.

Add:

| # | Kind | Check |
| --- | --- | --- |
| 12 | hard | For every analog and every preset with status `ok`, recomputing MSI from `sub_scores`, the preset weights, the target's `available_dims` and `earth_missing_score` gives `msi_by_preset` within 0.002 |
| 13 | hard | For every preset with status ≠ `ok` for a target: no analog of that target lists the preset in `selected_by`, and every `msi_by_preset[pkey]` is `null` |
| 14 | hard | No Moon target has status `ok` for `dust_and_seasons` |
| 15 | soft | For every target and preset with status `ok`: count targets whose 1st-ranked analog has the preset's **highest-weight** dimension in `earth_missing_dims`. Expected 0; it is soft because it can legitimately happen if no Earth patch has that measurement near the target's values |
| 16 | soft | Mars `dust_and_seasons`: number of targets whose top-1 analog is in Antarctica. Report it; expected ≤ 5 (was 17) |
| 17 | soft | `isru_and_ice`: targets with status `ok` per body. Expected Mars 1 (Arcadia), Moon 8 (Diviner targets). Report the IDs |

---

## 6. Task T16.4: tests

Add to `tests/test_match.py` (synthetic arrays only, no Yuca data):

1. `test_msi_case_c_counts_zero`: two Earth rows, weights `{topography: 0.6, dust: 0.4}`, `target_dims = {topography, dust}`; row 0 has dust 1.0, row 1 has dust NaN; both topography 1.0. Expect `[1.0, 0.6]`.
2. `test_msi_case_b_skips_target_missing`: same rows, `target_dims = {topography}`. Expect `[1.0, 1.0]`.
3. `test_msi_legacy_when_target_dims_none`: `target_dims=None` gives today's result (`[1.0, 1.0]`).
4. `test_msi_scalar_branch_matches_vector_branch` for cases B and C.
5. `test_available_dims_rules`: one `TargetVec` per row of the table in §2 (Mars with/without `zt_t`, with/without ice, Moon with/without Diviner, geology class unknown) and the expected set.
6. `test_preset_status`: Mars `isru_and_ice` without ice gives `("insufficient_target_data", 0.5, ["ice"])`; Mars with ice gives `("ok", 1.0, [])`; Moon `dust_and_seasons` gives `("not_applicable_body", 0.0, [])`; Mars `dust_and_seasons` without thermal gives `("ok", 0.8, ["thermal"])`.
7. `test_select_by_preset_skips_not_ok`: a preset with status not `ok` returns an all-NaN MSI array and an empty selection.
8. `test_dust_preset_does_not_reward_missing_earth_dust`: a reproduction of the bug. Three Earth rows whose sub-scores are all 1.0 except dust: row 0 dust 0.9, row 1 dust 0.2, row 2 dust NaN (the "Antarctic" row). Use `PRESETS["dust_and_seasons"]["weights"]` and `target_dims` = all seven dimensions except `ice`. Expected MSI `[0.96, 0.68, 0.60]`, order `[0, 1, 2]`. With `target_dims=None` the MSI is `[0.96, 0.68, 1.00]` and the order `[2, 0, 1]`: assert that too, to document the bug.

Add to `tests/test_export.py`:

9. `test_export_preset_status_and_missing_dims`: run the export on the existing small fixture (or extend it) and assert that every target has all preset keys in `preset_status`, Moon `dust_and_seasons` is `not_applicable_body`, `earth_missing_dims` is a list on every analog, and `msi_by_preset` is `null` for non-`ok` presets.

Run the tests in a short job, not on the login node:

```bash
cd /lustre/proyectos/p089/code && git pull && sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -J p089-t16-tests -o /lustre/proyectos/p089/output/t16_tests_%j.log --wrap "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && python -m pytest -q tests"
```

All existing tests must still pass.

---

## 7. Task T16.5: app (after `feat/app-seven-dimensions` is merged)

The app work starts from branch `feat/app-seven-dimensions` (it already loads the final export and handles seven dimensions). Merge it into `main` first, or branch from it. Do not redo that work.

### 7.1 `app/src/lib/types.ts`

- `Target`: add `available_dims?: Dimension[]` and `preset_status?: Record<string, { status: "ok" | "not_applicable_body" | "insufficient_target_data"; coverage: number; missing_dims: Dimension[] }>`.
- `Analog`: add `earth_missing_dims?: Dimension[]`.
- `Preset`: add `applies_to?: Body[]`.
- `Universe.metadata`: add `scoring_policy?: { earth_missing_score: number; min_preset_coverage: number; rules: string[] }`.

### 7.2 `app/src/lib/msi.ts`

Mirror §3.3 exactly. `msi(a, w, targetDims, earthMissing)`:

- If `targetDims` is undefined (old exports), keep today's rule.
- Skip `d` not in `targetDims`.
- If `d` in `targetDims` and `sub_scores[d]` is null, use `earthMissing` (from `metadata.scoring_policy.earth_missing_score`, default 0).

`rankTargets` gets the target's `available_dims` and also needs to know if the **current weights** leave enough coverage. Compute coverage in the browser with the same formula as §2 (custom slider weights can change it). Targets with coverage < `min_preset_coverage` are excluded from the ranking and returned in a separate list `unranked: { target, missingDims }[]`.

### 7.3 Presets per body (`ScenarioPanel.tsx`, `App.tsx`)

- Only show preset buttons whose `applies_to` includes the selected body. When switching body, if the active preset does not apply, switch to the first preset that does.
- Below the ranking (in `RankList.tsx`), if `unranked.length > 0`, show a short note, for example: *"7 targets are not ranked for this case: no ice data at these sites (Jezero crater, Gale crater, …)."* Use the dimension labels from `DIM_LABEL`.

### 7.4 Site sheet (`Dossier.tsx`, `Radar.tsx`)

- Radar: for a dimension in `earth_missing_dims`, draw the point at 0 with a hollow marker. The axis label gets a small "no Earth data" note. Dimensions not in `available_dims` stay dashed as today.
- Feature table: for each dimension in `earth_missing_dims`, add a row "*<Dimension label>*: no Earth measurement, scored 0" with status `differs`.
- "Where the analogy breaks": treat `no_earth_data:<dim>` mismatches as "no Earth data for <dim>".

### 7.5 Methodology section

Render `metadata.scoring_policy.rules` as a short list under the dimensions.

### 7.6 App checks

- `npx tsc -b` and `npm --prefix app run build` pass.
- In the browser: Mars + dust preset: count Antarctic top-1 targets (should match soft check 16). Mars + ice preset: 1 target ranked and a note listing the others. Moon: no dust preset button. Moon + ice preset: 8 targets ranked.
- The MSI shown for any analog equals `msi_by_preset` of the export (use the check in §9.3 against the JSON).

---

## 8. Task T16.6: production run on Yuca

Same inputs as run 2242490, so only the scoring changes:

```bash
cd /lustre/proyectos/p089/code && git pull
```

```bash
cd /lustre/proyectos/p089/code && sbatch --export=ALL,T5_DIR=/lustre/proyectos/p089/runs/2242438,T12_DIR=/lustre/proyectos/p089/runs/2242487,T13_DIR=/lustre/proyectos/p089/runs/2242484,T14_DIR=/lustre/proyectos/p089/runs/2242486 jobs/t7_match.slurm
```

Check before trusting the output: the T12, T13 and T14 directories above are the ones listed in the run 2242490 metadata (`metadata.runs`). If the export metadata of the new run lists different inputs, stop.

Bring `runs/<new job>/analogs_universe.json` into `app/public/data/` the same way as for run 2242490 (see [working_without_ssh.md](working_without_ssh.md)), and commit it with the run ID in the message.

---

## 9. Acceptance

### 9.1 Expected results

| Measure | Run 2242490 | Expected after T16 |
| --- | --- | --- |
| Mars `dust_and_seasons`: top-1 analogs with dust null | 19 / 38 | **0** |
| Mars `dust_and_seasons`: top-1 analogs in Antarctica | 17 | ≤ 5 (soft; report the real number) |
| Mars `isru_and_ice`: targets ranked | 38 | **1** (Arcadia SWIM) |
| Moon `isru_and_ice`: targets ranked | 38 | **8** (Diviner targets) |
| Moon `dust_and_seasons`: targets ranked | 38 | **0** |
| `mobility_and_traction`, `construction_and_base`, `geology_and_materials`: targets ranked | 38 + 38 | 38 + 38 (unchanged) |
| Hard checks | 7/7 | all, including 12–14 |

If any expected value is off, stop and report it with the numbers. Do not tune constants to hit the table.

### 9.2 Things that must not change

- Terrain sub-scores, normalisation, σ, the tropical dust rule, the ice cap, `select_diverse`, `TOP_N`, `MIN_SEP_KM`.
- Presets and their weights.
- The environment exception for missing NDVI (§2).
- Any upstream run (T3–T14). Only matching and export are re-run.

### 9.3 Verification script

Run against the exported JSON (on Yuca inside a short job, or locally against `app/public/data/analogs_universe.json` after it is committed). It prints the measures of §9.1 and checks hard check 12 independently of the pipeline code.

```python
import json, collections, sys
u = json.load(open(sys.argv[1], encoding="utf-8"))
P = u["mission_presets"]; pol = u["metadata"].get("scoring_policy", {}); zero = pol.get("earth_missing_score", 0.0)

def msi(a, w, dims):
    num = den = 0.0
    for d, wd in w.items():
        if wd <= 0 or (dims is not None and d not in dims):
            continue
        s = a["sub_scores"].get(d)
        if s is None:
            if dims is None:
                continue
            s = zero
        num += wd * s; den += wd
    return num / den if den else None

bad = 0
for body in ("Mars", "Moon"):
    T = [t for t in u["targets"] if t["body"] == body]
    for p, spec in P.items():
        st = collections.Counter(t.get("preset_status", {}).get(p, {}).get("status", "?") for t in T)
        ranked = [t for t in T if t.get("preset_status", {}).get(p, {}).get("status") == "ok"]
        tops = [max(t["analogs"], key=lambda a: a["msi_by_preset"][p] if a["msi_by_preset"][p] is not None else -1) for t in ranked]
        ant = sum(1 for a in tops if a["country"] == "Antarctica")
        key = max(spec["weights"], key=spec["weights"].get)
        nul = sum(1 for a in tops if key in (a.get("earth_missing_dims") or []))
        print(f"{body:4} {p:24} status={dict(st)} ranked={len(ranked)} top1_antarctica={ant} top1_missing_{key}={nul}")
        for t in ranked:
            for a in t["analogs"]:
                ref = a["msi_by_preset"][p]
                got = msi(a, spec["weights"], set(t.get("available_dims", [])) or None)
                if ref is not None and got is not None and abs(ref - got) > 0.002:
                    bad += 1
print("hard check 12 violations:", bad)
```

---

## 10. Documentation

In the same commits as the code:

- `docs/logbook.md`: one entry per task (T16.1 to T16.6) with what changed, why, the job IDs and the numbers of §9.1.
- `docs/pipeline.md`: add the new run to the runs table; describe `target_presets.csv` and the new export fields.
- `docs/HISTORY.md`: a short paragraph: missing data was a free pass; the three cases; the decision.
- `README.md`: if it describes the score, add one sentence on how missing data is treated.

---

## 11. Commits

One commit per task, in English, each with its logbook entry:

1. `T16.1: missing-data policy in MSI and preset selection`
2. `T16.2: export available_dims, preset_status and earth_missing_dims`
3. `T16.3: hard checks 12-14 and soft checks 15-17`
4. `T16.4: tests for the missing-data policy`
5. `T16.5: app mirrors the missing-data policy` (on top of `feat/app-seven-dimensions`)
6. `Data: analogs_universe.json from T16 run <job id>`

Do not push `--force`, do not rewrite history, do not touch the raw data on Yuca.
