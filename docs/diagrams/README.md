# `docs/diagrams/` — Interactive Technical Architecture Blueprints

This directory contains the source definitions and standalone interactive HTML blueprints for **PROTOTERRA**, generated using **Archify** and styled with the **RETÍCULA Design System**.

Unlike static bitmap images, these diagrams feature deep-dive interactive capabilities: smooth infinite pan, semantic zoom, radar minimaps, node search indexing, and component inspectors.

---

## Live Interactive Blueprints

All diagrams are hosted live on our Firebase deployment:

| Diagram Blueprint | Live Hosted Viewer | Source JSON Spec | What it Illustrates |
| :--- | :---: | :---: | :--- |
| **System Architecture** | [🏛 View Live](https://prototerra.web.app/diagrams/system-architecture.html) | [`src/system-architecture.json`](src/system-architecture.json) | High-level system structure: HPC cluster, data stores, web console, and user interactions. |
| **Pipeline Lineage & Data Flow** | [🔄 View Live](https://prototerra.web.app/diagrams/pipeline-lineage.html) | [`src/pipeline-lineage.json`](src/pipeline-lineage.json) | End-to-end data provenance from raw NASA/ESA/USGS rasters to the published client contract. |
| **Pipeline Execution Stages** | [⚙️ View Live](https://prototerra.web.app/diagrams/pipeline-stages.html) | [`src/pipeline-stages.json`](src/pipeline-stages.json) | Chronological Slurm job execution sequence (Tasks T1 through T8) on the Yuca supercomputer. |
| **Frontend Sequence & Event Bus** | [⚡ View Live](https://prototerra.web.app/diagrams/app-sequence.html) | [`src/app-sequence.json`](src/app-sequence.json) | Client-side reactive lifecycle: 3D orbit picking, weight adjustments, and in-memory re-ranking. |
| **Data Contract Specification** | [📋 View Live](https://prototerra.web.app/diagrams/data-contract.html) | [`src/data-contract.json`](src/data-contract.json) | Strict JSON schema definitions for `Universe`, `Target`, `AnalogMatch`, and `MismatchVector`. |
| **Repository Layout** | [📂 View Live](https://prototerra.web.app/diagrams/repository-layout.html) | [`src/repository-layout.json`](src/repository-layout.json) | Structural mapping of source files, configuration manifests, and test suites. |

---

## Re-rendering Diagrams

The diagrams are rendered from deterministic JSON specifications in `src/` using the **Archify CLI**:

```bash
# Render all diagrams with git evidence verification
archify render docs/diagrams/src/system-architecture.json -o docs/diagrams/system-architecture.html --revision $(git rev-parse HEAD)
archify render docs/diagrams/src/pipeline-lineage.json -o docs/diagrams/pipeline-lineage.html --revision $(git rev-parse HEAD)
archify render docs/diagrams/src/pipeline-stages.json -o docs/diagrams/pipeline-stages.html --revision $(git rev-parse HEAD)
archify render docs/diagrams/src/app-sequence.json -o docs/diagrams/app-sequence.html --revision $(git rev-parse HEAD)
archify render docs/diagrams/src/data-contract.json -o docs/diagrams/data-contract.html --revision $(git rev-parse HEAD)
archify render docs/diagrams/src/repository-layout.json -o docs/diagrams/repository-layout.html --revision $(git rev-parse HEAD)
```

The HTML files are also mirrored to `app/public/diagrams/` for inclusion in the Firebase Hosting distribution.
