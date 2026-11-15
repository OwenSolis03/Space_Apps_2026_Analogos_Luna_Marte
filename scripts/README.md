# scripts/

Everything that processes data.

| Folder | Content |
| --- | --- |
| `pipeline/` | The v2 Python package (`python -m pipeline.<module>`): patch extraction, features, sweeps, context layers, matching and export |
| `jobs/` | Slurm jobs, one per task, plus the data downloads |
| `tools/` | Downloaders, dataset explorer, verification and sensitivity scripts, the v1-to-v2 sample converter |
| `legacy_v1/` | The v1 prototype, kept as reference and never imported |

Run from the repository root. The jobs add `scripts/` to `PYTHONPATH` themselves:

```bash
sbatch scripts/jobs/t3_planet_features.slurm
```

By hand, and for the tests (`pytest.ini` at the root does the same):

```bash
PYTHONPATH=scripts python -m pipeline.targets --help
```
