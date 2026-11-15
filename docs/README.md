# PROTOTERRA Documentation Index

Comprehensive documentation repository for **PROTOTERRA: Planetary Analog Finder for the Moon and Mars**, developed by **Team Endurance CXXV** for the **NASA Space Apps Challenge 2026**.

---

## Strategic & Challenge Guides

| Document | Description & Target Audience |
| :--- | :--- |
| **[`../README.md`](../README.md)** | **Main Project Overview:** Challenge summary, differentiators, supercomputing, tech stack, and installation. |
| **[`value_proposition.md`](value_proposition.md)** | **Mission Value & Pitch Deck Strategy:** Core problem, scientific differentiators, and non-substitutable planetary boundaries. |
| **[`submission.md`](submission.md)** | **NASA Space Apps Submission Audit:** Ready-to-paste text for the 7 official submission portal fields and compliance checklists. |
| **[`HISTORY.md`](HISTORY.md)** | **Phase-by-Phase Development Narrative:** Detailed engineering log from initial conception through HPC pipeline execution. |
| **[`logbook.md`](logbook.md)** | **Daily Operational Logbook:** Chronological engineering diary documenting cluster runs, decisions, and AI oversight. |

---

## Interactive Architecture Blueprints (Archify)

All six technical architecture blueprints are rendered with the **RETÍCULA Design System** and hosted live on our Firebase deployment:

| Diagram Blueprint | Live Interactive Viewer | Source Spec | Focus & Key Insights |
| :--- | :---: | :---: | :--- |
| **System Architecture** | [🏛 View Live](https://prototerra.web.app/diagrams/system-architecture.html) | [`src/system-architecture.json`](diagrams/src/system-architecture.json) | High-level component overview: HPC cluster, data store, web console, and user flows. |
| **Pipeline Lineage & Data Flow** | [🔄 View Live](https://prototerra.web.app/diagrams/pipeline-lineage.html) | [`src/pipeline-lineage.json`](diagrams/src/pipeline-lineage.json) | Complete provenance tracking from raw NASA/ESA/USGS rasters down to final JSON contract. |
| **Pipeline Execution Stages** | [⚙️ View Live](https://prototerra.web.app/diagrams/pipeline-stages.html) | [`src/pipeline-stages.json`](diagrams/src/pipeline-stages.json) | Step-by-step Slurm job execution sequence (Tasks T1 through T8) on the Yuca supercomputer. |
| **Frontend Sequence & Event Bus** | [⚡ View Live](https://prototerra.web.app/diagrams/app-sequence.html) | [`src/app-sequence.json`](diagrams/src/app-sequence.json) | Client-side reactive lifecycle: 3D orbit picking, weight adjustments, and in-memory re-ranking. |
| **Data Contract Specification** | [📋 View Live](https://prototerra.web.app/diagrams/data-contract.html) | [`src/data-contract.json`](diagrams/src/data-contract.json) | Strict JSON schema definitions for `Universe`, `Target`, `AnalogMatch`, and `MismatchVector`. |
| **Repository Layout** | [📂 View Live](https://prototerra.web.app/diagrams/repository-layout.html) | [`src/repository-layout.json`](diagrams/src/repository-layout.json) | Structural mapping of source files, configuration manifests, and test suites. |

---

## Technical Specifications & Pipeline

| Document | Purpose |
| :--- | :--- |
| **[`pipeline.md`](pipeline.md)** | **End-to-End Pipeline Manual:** Input rasters, scales, coordinate transforms (AEQD 32 km), run stages, and Yuca HPC compute allocations. |
| **[`CODEBASE_DOCUMENTATION.md`](CODEBASE_DOCUMENTATION.md)** | **Module-by-Module Technical Reference:** Detailed API documentation for Python modules in `scripts/pipeline/`. |
| **[`implementation_plan.md`](implementation_plan.md)** | **V2 Architecture Plan:** Morphometric patch method, scale-invariant features, MSI formulation, and data contracts. |
| **[`weights_justification.md`](weights_justification.md)** | **Mission Preset Weights Rationale:** Sensitivity analysis and physical justification for the 5 mission profiles. |

---

## Slurm Tasks Specifications (Pre-Code Design)

| Document | Task Name | Scope & Methodology |
| :--- | :--- | :--- |
| **[`plan_t4.md`](plan_t4.md)** | **Task T4: Targets & Clusters** | Ingestion of 16 curated exploration targets + k-means clustering for 60 representative terrain medoids. |
| **[`plan_t5.md`](plan_t5.md)** | **Task T5: Earth Sweep** | Global scanning of Copernicus DEM GLO-90 to extract ~45,000 candidate bare-land patches. |
| **[`plan_t6.md`](plan_t6.md)** | **Task T6: Earth Context Layers** | MODIS NDVI vegetation masking, MODIS LST thermal profiles, and accessibility vector calculations. |
| **[`plan_t7_t8.md`](plan_t7_t8.md)** | **Tasks T7 & T8: Match & Export** | Multi-dimensional Gaussian RBF kernel scoring, 150 km spatial diversity enforcement, and packaging. |
| **[`plan_t12_t15.md`](plan_t12_t15.md)** | **Tasks T12–T15: Specialized Layers** | Geologic unit harmonization, seasonal dust climatology, and cryospheric/ice stability indicators. |
| **[`plan_t16_missing_data.md`](plan_t16_missing_data.md)**| **Task T16: Missing Data Policy** | Mathematical rules for handling missing coverage without introducing bias in the MSI score. |

---

## High-Performance Supercomputing Operations

| Document | Description |
| :--- | :--- |
| **[`working_without_ssh.md`](working_without_ssh.md)** | Protocol for interacting with the **Yuca supercomputer (ACARUS)** via Open OnDemand web terminals when direct SSH connections are blocked by institutional firewalls. |
| **[`handoff.md`](handoff.md)** | Continuity guide summarizing active cluster jobs, intermediate data locations, and verification checklists. |
