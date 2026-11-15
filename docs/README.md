# Documentation index

Where to find what. The newest state of the project is in the [logbook](logbook.md); the plans describe what was asked, and the logbook says what was done.

## Start here

| Document | What it is |
| --- | --- |
| [../README.md](../README.md) | What the project is, how to run it, the data and the team |
| [value_proposition.md](value_proposition.md) | Problem, value, what sets the project apart and what not to claim |
| [submission.md](submission.md) | What is submitted, who does it, the timeline and the checklist |
| [deployment.md](deployment.md) | Publishing the app on GitHub Pages, and the custom domain |

## How it works

| Document | What it is |
| --- | --- |
| [pipeline.md](pipeline.md) | The pipeline step by step: data, scales and types of every file, runs and Yuca resources |
| [CODEBASE_DOCUMENTATION.md](CODEBASE_DOCUMENTATION.md) | Module-by-module technical reference |
| [implementation_plan.md](implementation_plan.md) | The v2 plan: patch method, dimensions, MSI and the export contract |
| [diagrams/](diagrams/) | Six HTML diagrams: architecture, data lineage, stages, app sequence, data contract and repository layout |
| [master_plan.md](master_plan.md) | The original plan. It describes the goal, not the current state |

## Task plans (specifications written before the code)

| Document | Task |
| --- | --- |
| [plan_t4.md](plan_t4.md) | Curated targets and clusters |
| [plan_t5.md](plan_t5.md) | Earth sweep |
| [plan_t6.md](plan_t6.md) | Earth layers: NDVI, temperature, logistics, countries, known analogs |
| [plan_t7_t8.md](plan_t7_t8.md) | Matching, scoring and export |
| [plan_t12_t15.md](plan_t12_t15.md) | Geology, dust and seasons, water and ice |
| [plan_t16_missing_data.md](plan_t16_missing_data.md) | Missing-data policy for the MSI |
| [plan_t17_plain_language.md](plan_t17_plain_language.md) | Plain-language explanations in the app |
| [plan_mineralogy_context.md](plan_mineralogy_context.md) | Mineralogy as display-only context (T18) |

## Decisions and analysis

| Document | What it is |
| --- | --- |
| [weights_justification.md](weights_justification.md) | Where the mission-case weights come from, what supports them, and a sensitivity test |
| [plan_mineral_dimension.md](plan_mineral_dimension.md) | Experiment: a scored Mars-only mineral dimension. Dropped for the submission; read the correction in the logbook, because the experiment never used EMIT data |
| [ideas.md](ideas.md) | The team's idea log and its evaluation |

## Working practices

| Document | What it is |
| --- | --- |
| [working_without_ssh.md](working_without_ssh.md) | How the team works with Yuca through Open OnDemand when SSH is blocked |
| [handoff.md](handoff.md) | Progress summary written for whoever continues the work |
| [gemini_prompt.md](gemini_prompt.md) | The prompt given to the coding agent for each task |

## History

| Document | What it is |
| --- | --- |
| [logbook.md](logbook.md) | Day-by-day record, newest first. Also the base of the use-of-AI description |
| [HISTORY.md](HISTORY.md) | The same story by phase, with the reasoning behind each decision |

The v1 prototype (scripts, jobs, outputs and logs) lives in [`../scripts/legacy_v1/`](../scripts/legacy_v1/) and is kept as reference only.
