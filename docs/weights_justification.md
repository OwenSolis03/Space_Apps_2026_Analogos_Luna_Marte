# Where the mission-case weights come from, and what supports them

Written by Claude on 2026-11-14. Short version for the submission: **the weights are design priors chosen by the team, informed by published site-selection criteria, tested for stability, and adjustable by the user.** They are not taken from a NASA standard, and no source gives these exact numbers.

---

## 1. What they are

The five mission cases (`mobility_and_traction`, `construction_and_base`, `geology_and_materials`, `dust_and_seasons`, `isru_and_ice`) and their weights over the seven dimensions were chosen by the team, with Claude, between 2026-11-13 and 2026-11-14. The first three-case version came from the project's master plan; the current table is section 5.2 of [plan_t12_t15.md](plan_t12_t15.md) and `PRESETS` in `pipeline/match.py`. No document cites a source for the numbers, because there was none: they are judgment.

## 2. What published work says about the priorities

I read the titles and the search summaries of the works below, not the full papers. Check a figure in the source before quoting it.

| Our choice | What supports it | Source |
| --- | --- | --- |
| Terrain (topography and roughness) carries most of the weight when the case is driving or landing: 0.75 in mobility, 0.65 in construction | NASA judged the Artemis III candidate regions on slope, communication with Earth and lighting, so slope is a safety criterion before anything else. A 2024 machine-learning study of lunar landing sites reports slope as the most important safety factor. Mars landing sites are screened on slope, rock abundance, craters and dunes; for the Mars Science Laboratory the ellipse had to have slopes of 3 degrees or less over 2 to 5 km | [CollectSPACE on the Artemis III regions](https://www.collectspace.com/news/news-081922a-artemis-iii-moon-landing-regions.html), [AmericaSpace](https://www.americaspace.com/2022/08/20/nasa-announces-potential-landing-sites-for-historic-artemis-iii-mission/), [Remote Sensing 16(19), 3632](https://mdpi.com/2072-4292/16/19/3632), [GSA 2020 abstract on Mars sample return sites](https://gsa.confex.com/gsa/2020AM/webprogram/Paper358843.html), [MSL Engineering User Guide](https://marsoweb.nas.nasa.gov/landingsites/msl/memoranda/MSL_Eng_User_Guide_v2.pdf) |
| Thermal contrast has a small weight (0 to 0.20) | In Mars landing-site work, thermal inertia is a proxy for surface hardness (low values mean dust and a load-bearing risk), so it is a secondary engineering factor, not the main one. Values quoted are from the MSL era | [GSA 2020 abstract](https://gsa.confex.com/gsa/2020AM/webprogram/Paper358843.html) |
| The ice case puts half of its weight on ice | A GIS study of the Aristarchus Plateau gives resource layers twice the weight of limiting factors in a weighted sum (20% against 10%). It is a conference abstract, so provisional. NASA also required Artemis III sites to be close to a permanently shadowed region | [EPSC 2026 abstract](https://meetingorganizer.copernicus.org/EPSC2026/EPSC2026-1011.html), [CollectSPACE](https://www.collectspace.com/news/news-081922a-artemis-iii-moon-landing-regions.html) |
| Weighted scoring of several criteria, with the weights then tested | Multi-criteria methods (TOPSIS, AHP, weighted overlay) are the usual way to rank landing sites. One study ranks 1,247 candidate locations in the 13 Artemis III regions with TOPSIS and tests how the ranking changes when the weights change, which is what section 3 does for us | [arXiv 2406.19863](https://arxiv.org/html/2406.19863v2), [NOVA Lisbon thesis on Mars with AHP and Perseverance constraints](https://run.unl.pt/bitstream/10362/180554/1/TGEO4801.pdf) |

What this supports is the **order of priorities** in each case (terrain first for driving and landing, ice first for resources, thermal as a secondary factor). It does not support the exact figures, for instance 0.45 against 0.40.

Pass or fail limits (for example a maximum slope) are the other common practice in this literature. We use soft scores instead, so a site is never excluded outright; the physical limits are listed on the site sheet under "where the analogy breaks".

## 3. Does the exact number matter? Sensitivity test

`tools/weight_sensitivity.py` re-ranks the analogs of every target with perturbed weights and compares with the published weights. Result on run 2242506 plus the T18 data (300 draws per target):

| Mission case | Targets | `near`: top-10 kept | `near`: rank correlation | `random`: top-10 kept | `random`: rank correlation |
| --- | --- | --- | --- | --- | --- |
| Rover mobility and traction | 76 | 85% | 0.95 | 36% | 0.25 |
| Base construction and landing | 76 | 84% | 0.94 | 40% | 0.31 |
| Geology and surface materials | 76 | 92% | 0.97 | 37% | 0.27 |
| Dust storms and seasons | 38 | 78% | 0.96 | 37% | 0.39 |
| Water ice and cold traps (ISRU) | 9 | 68% | 0.87 | 34% | 0.22 |

- **`near`** multiplies each non-zero weight by a random factor of about plus or minus 50% and keeps the zeros. The ranking is stable: 68 to 92% of the best ten analogs stay in the best ten, and the rank correlation is 0.87 to 0.97. **The exact numbers are not critical.**
- **`random`** draws any weights over the dimensions that apply. Only about a third of the best ten survive and the correlation drops to 0.2 to 0.4. **Which dimension dominates matters a lot**, and this is the reason the mission cases exist and the sliders are on the page.
- The ice case is the least stable (9 targets, correlation 0.87), because only the Artemis regions and one Mars site have ice data.

Limit: only the analogs that the export keeps (30 per case, union over cases) are re-ranked, not the whole Earth, so this describes the ranking inside that pool.

## 4. What we cannot claim

- That any source gives these weights, or that they are optimal.
- That they were derived by expert pairwise comparison (AHP). They were not.
- That the model covers what NASA used for Artemis III: lighting and communication with Earth are not modelled.
- That the sensitivity result holds over the whole Earth; it holds inside the exported pool.

## 5. Suggested wording for the submission

> The mission cases are starting configurations defined by the team. Their priorities follow criteria used in published landing-site studies (terrain first for driving and landing, ice first for resource work, thermal behaviour as a secondary factor); the numbers themselves are our judgment. We tested them: changing every weight by about 50% keeps 68 to 92% of the top ten analogs and a rank correlation of at least 0.87, while unrelated weights would not. Users can change the weights with the sliders.

## 6. If there is time: derive the weights with the team (AHP)

About half an hour. Each teammate fills in a pairwise comparison table for the dimensions of one case (for example, "for rover mobility, is topography much more, more or equally important than roughness?"), the answers are combined, and the weights and a consistency ratio come out of the standard AHP calculation. That would turn "chosen by the team" into "derived from documented team judgments, with a consistency check", which is what the multi-criteria papers above do. It would replace the numbers but, given the sensitivity result, probably not the rankings.
