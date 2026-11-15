# data/

Hand-written definitions the pipeline reads. They are small, reviewed by people, and versioned with the code.

| File | Read by | Content |
| --- | --- | --- |
| `targets.json` | `scripts/pipeline/targets.py` | The 16 curated targets (8 Moon, 8 Mars) with coordinates, anchors and sources |
| `known_analogs.json` | `scripts/pipeline/earth_layers.py` | The 12 well-studied analog regions on Earth, used to label `KNOWN_ANALOG` |
| `limits.json` | `scripts/pipeline/export.py` | Fixed physical limits per body, with sources |
| `geology_overrides.json` | `scripts/pipeline/geology.py` | Expert overrides for lunar and Martian map units |
| `ice_hints.json` | `scripts/pipeline/ice.py` | Curated ice hints for Mars targets |

**Not here.**

- **Raw rasters and derived caches** (about 80 GB) live on Yuca at `/lustre/proyectos/p089/data` and are ignored by git (`/data/raw/` and `/data/derived/` in `.gitignore`). Each file's source, units and nodata value are in [docs/pipeline.md](../docs/pipeline.md).
- **The exported result** the website reads is `app/public/data/analogs_universe.json`; it has to sit under `app/public/` so the site can serve it.
