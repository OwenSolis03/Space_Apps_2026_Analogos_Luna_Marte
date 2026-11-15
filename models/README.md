# models/

There are no trained neural networks in this project, and nothing is learned from labels. The "model" is a score that can be audited end to end.

| Part | Where it lives | What it is |
| --- | --- | --- |
| Similarity score (MSI) | `scripts/pipeline/match.py` | Per-dimension similarity from 0 to 1 between a target and each of the 40,244 Earth patches, combined with the weights of five mission presets |
| Terrain clusters | `scripts/pipeline/targets.py` | k-means with k = 30 per body on six terrain features; the patch nearest each centre becomes a target |
| Weights | `PRESETS` in `scripts/pipeline/match.py` | The team's judgment, tested for stability: [docs/weights_justification.md](../docs/weights_justification.md) |
| Browser side | `app/src/lib/msi.ts` | The same weighted mean, recomputed live when the user moves a slider |

Both parts are deterministic and rerun from the data. How they work is explained step by step on the website's Algorithm page and in [docs/pipeline.md](../docs/pipeline.md).
