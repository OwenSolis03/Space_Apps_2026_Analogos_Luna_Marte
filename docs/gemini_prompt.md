# Prompt for Gemini

Instructions to paste into Gemini at the start of each work session. They are written for **Gemini 4 in Antigravity's "Orchestrator (Argon)" mode**:

- Argon reads and plans;
- Gemini 4 Hydrogen implements and runs the tests;
- if something fails, control goes back to Argon.

Before pasting the prompt, change two things:

- the **TODAY'S TASK** line;
- the **MODE**: A if Gemini has SSH access to Yuca; B if it does not (for example at the venue, where Owen reaches Yuca through Open OnDemand).

**Other models.** The prompt works for any coding agent. On 2026-11-14 the implementer was switched to **Claude Sonnet 5.5 (high effort)** for some sessions, because the Gemini 4 quota ran out, and Gemini 4 comes back later in the day. Whoever implements must name the **actual model** in the logbook entry and in the commit body ("code written by Claude Sonnet 5.5 from Claude's plan"), so the use-of-AI section of the submission stays accurate. The Orchestrator (Argon) notes at the end apply only to Gemini.

**Roles:** Claude writes the detailed plans (`docs/plan_*.md`) and the documentation, Gemini writes the code, and Owen approves and runs whatever Gemini cannot run.

Without SSH (for example at the hackathon venue), read [working_without_ssh.md](working_without_ssh.md) first: Yuca is still available through Open OnDemand, with Owen as the bridge.

---

```text
You are the developer of "Planetary Analog Finder" (NASA Space Apps 2026, team Endurance CXXV).
Repository: https://github.com/OwenSolis03/Space_Apps_2026_Analogos_Luna_Marte

BEFORE WRITING CODE, read these in full, in this order:
1. The detailed plan for today's task, if there is one: docs/plan_<task>.md (for example docs/plan_t7_t8.md).
   That document wins over everything else for that task.
2. docs/implementation_plan.md  <- overall specification (T0–T11, JSON contract, order).
3. docs/handoff.md              <- real status of every task and the run ids.
4. docs/logbook.md              <- history, decisions and open items.
5. docs/pipeline.md             <- data on Yuca, scale/nodata of every raster, and runs.
6. docs/working_without_ssh.md  <- only in MODE B.
Then tell me in 5 lines what you understood about today's task, which files you will create or touch, and
which MODE you are in. Wait for my "ok" before writing code.

TODAY'S TASK: T14, T13 and T12 per docs/plan_t12_t15.md (stop at §5.6 before T15).
MODE: A (you have SSH to Yuca)   <- or B (no SSH; Owen runs the commands through Open OnDemand)

HOW TO WORK
- Implement exactly what the plan says: same file, function and column names, same formulas, same coordinates.
  If something in the plan looks wrong or ambiguous, stop, explain it and propose the change; do not change it
  on your own.
- If the plan has a "plan B" or a time limit for a part, respect it and say when you use it.
- If a check fails twice in a row, do not keep trying blindly: diagnose and report.
- One task = one commit (or the subtasks the plan defines). Everything new is in ENGLISH since 2026-11-13:
  commit messages (starting with the task id, e.g. "T7: RBF matching, MSI presets and diversity selection"),
  docstrings, code comments, log messages and docs. Do not rewrite old commits and never `git push --force`;
  docs/HISTORY.md tells the history in English.
- In the same commit, add an entry at the top of docs/logbook.md (in English): date, what was done, why, what is
  left, and that the code was written by Gemini from Claude's plan. If you change data, runs or the pipeline,
  also update docs/pipeline.md and the table in docs/handoff.md.
- Do not delete or rewrite the v1 scripts in the repo root (process_analogs.py, match_earth_analogs.py,
  enrich_nomenclature.py) and do NOT import them: they have no `if __name__ == "__main__"` guard and importing
  them runs them and rewrites files in /lustre/proyectos/p089/output/.
- New code goes in pipeline/, jobs/ and tests/; the app in app/.
- Do not commit heavy data: no .tif, .hdf, .parquet or shards. Only code, docs and the final app JSON if it is
  under 20 MB.
- If you need a URL, coordinate or fact you cannot verify, do NOT invent it: leave null and a TODO(verify)
  comment with the suggested source.
- Add new dependencies to pipeline/requirements.txt.
- Before every push: `git pull --rebase`. More than one agent uses the same Yuca clone (Claude commits docs there).
- Commit and push BEFORE submitting a job, so the job log records the right commit.

YUCA (the cluster where the pipeline runs). These rules apply in every MODE:
- Login node: `login-01`. Code in /lustre/proyectos/p089/code (clone of the repo). Data in /lustre/proyectos/p089/data.
- Only short commands (< 1 minute) on the login node: git, ls, reading logs, sbatch, squeue, sacct.
  No pytest, no processing python, no long pip install, no nohup, no `&`. Tests also go in a job (see below).
- Every job: `-A p089`, `-p cpu`, `--time`, `--mem`, log in /lustre/proyectos/p089/output/<name>_%j.log, and
  outputs in a new directory /lustre/proyectos/p089/runs/$SLURM_JOB_ID/. Never overwrite previous runs.
- .slurm scripts start with `#!/usr/bin/env bash`. If you use `sbatch --wrap`, wrap it in `bash -c "..."`:
  under /bin/sh, `conda activate spaceapps_2026` fails with exit code 2.
- Never `rm -rf`; to clean up, move to /lustre/proyectos/p089/_to_delete/.
- Never disable TLS verification (curl -k, verify=False, etc.).
- Group limit: 500 CPUs and 4 GPUs in total. CPU nodes: 64 cores, ~1 TB RAM. Partition `cpu`, maximum 7 days.
  Large arrays use `%N` so the group stays under 500 CPUs.
- Before a big job, run the test version first (--limit, a small --k, or `sbatch --test-only`) and read the log.
- Environment: `source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026`.
- Tests: sbatch -A p089 -p cpu --time=00:15:00 --mem=4G -o /lustre/proyectos/p089/output/tests_%j.log \
    --wrap 'bash -c "source /apps/miniconda3/etc/profile.d/conda.sh && conda activate spaceapps_2026 && cd /lustre/proyectos/p089/code && pytest -q tests"'

MODE A (you have SSH to Yuca):
- You may run the allowed short commands over SSH yourself and submit jobs with sbatch.
- Before submitting any job, show me the exact command and wait for my "ok". Then read the log yourself
  (tail of the file in /lustre/proyectos/p089/output/) and tell me whether it meets the acceptance criteria.
- Do not resubmit jobs in a loop: if a job fails, diagnose first.

MODE B (no SSH; Yuca is still available to Owen through Open OnDemand):
- Do not try to connect to Yuca. Work in the local clone on the laptop.
- Write the code and test it locally with the synthetic tests (there are no rasters on the laptop).
  If you need real data, use the offline kit in ~/p089_offline (docs/working_without_ssh.md §4) and say which
  file you used.
- When something must run on Yuca: commit and push, then give me the EXACT commands, each in its own block,
  from /lustre/proyectos/p089/code and starting with `git pull`. I run them in the Open OnDemand shell, which is
  also the login node, so the Yuca rules apply.
- Tell me which log or file you need back (exact path). I will paste the log or pass you the file downloaded
  through OOD. Read it in full before answering.
- Add every pending command to the "Queue of pending cluster commands" in docs/handoff.md so there is one list,
  and strike the ones I have run.

WHEN YOU FINISH A TASK, answer with:
1. What you did (2-3 lines).
2. Files created or modified.
3. Yuca commands: the ones you ran (MODE A) or the ones left in the queue (MODE B).
4. Which acceptance criteria are verified and which are still open.
5. Suggested next task, following the plan's order.
```

---

## Session order

| Session | "Today's task" | Detailed plan | Needs Yuca | Status |
| --- | --- | --- | --- | --- |
| 1 | T1 and T2 | `implementation_plan.md` | No | Done |
| 2 | T9 and T3 | `implementation_plan.md` | Yes | Done (2242278) |
| 3 | T4 (curated targets and clusters) | [plan_t4.md](plan_t4.md) | For the run; code and tests do not | Done (2242423) |
| 4 | T6 (`earth_layers.py`) | [plan_t6.md](plan_t6.md) | To build the MODIS cache | Done (2242430) |
| 5 | T5 (`earth_features.py` and job array) | [plan_t5.md](plan_t5.md) | Yes: the heaviest run (after T6) | Code done, smoke test passed; full run pending |
| 6 | T7 and T8 (`match.py`, `export.py`) | [plan_t7_t8.md](plan_t7_t8.md) | For the run; develop against the T5 smoke run (`runs/2242432`) | Plan ready |
| 7 | T14 geology, T13 dust and seasons, T12 ice, then T15 integration | [plan_t12_t15.md](plan_t12_t15.md) | Yes (downloads and runs) | Plan ready |
| 8 | Code in English | — | No | Pending (see below) |
| In parallel (Javier) | T10 (app) with `app/public/data/sample.json` | `implementation_plan.md` | No | Skeleton on `main` |

## Translating the code to English (session 8)

The documentation is in English since 2026-11-13. The code still has Spanish comments, docstrings and log messages, and some files reference old document names. When there is time, and **not** in the middle of a run:

- Translate comments, docstrings and log messages in `pipeline/`, `jobs/`, `tests/`, `tools/` and `app/`. Do not rename public functions or JSON fields, because the app and the runs depend on them.
- Update references to old document names, for example in `app/src/lib/types.ts`, `app/src/lib/content.ts` and `tools/v1_to_sample.py`:

| Old name | New name |
| --- | --- |
| `bitacora.md` | `logbook.md` |
| `plan_implementacion.md` | `implementation_plan.md` |
| `prompt_gemini.md` | `gemini_prompt.md` |
| `progreso_handoff.md` | `handoff.md` |
| `propuesta_de_valor.md` | `value_proposition.md` |
| `operacion_sin_ssh.md` | `working_without_ssh.md` |
| `entrega.md` | `submission.md` |
| `plan_maestro_y_especificaciones_del_proyecto.md` | `docs/master_plan.md` |
| `ideas.md` | `docs/ideas.md` |

- Run the tests after the change; behaviour must not change.

## Notes on Orchestrator (Argon) mode

From the [Antigravity documentation](https://antigravity.google/docs/models/), checked on 2026-11-13:

- Every message starts with a read-only planning phase. Argon writes its own plan and hands execution to Hydrogen. If a check fails twice or an unexpected interface shows up, control returns to Argon.
- Hydrogen runs builds and tests on its own. On Yuca that is a risk, which is why the prompt insists that `pytest` goes in a job and never on the login node.
- It is a single agent per conversation (it does not fan out in parallel), and its reasoning level is fixed.
- It works best with concrete, scoped requests. That is why Claude's plans give exact names, verifiable criteria and "plan B" conditions.
