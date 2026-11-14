# Submission and timeline (NASA Space Apps Sonora, 14–15 November)

What has to be submitted, who does it and in what order, following our venue's rules: [spaceappssonora.org](https://spaceappssonora.org/) and its [pitch guide](https://spaceappssonora.org/pitches), checked on 2026-11-13. This replaces the 48-hour timeline in [implementation_plan.md](implementation_plan.md) §6, which assumed two full working days.

**Real time available:** Saturday the 14th from 9:00 to 21:00, plus Sunday morning. Pitches run Sunday from 9:00 to 14:00, so **everything must be submitted and published before our turn**. Confirm the exact deadline and our team number in the participants' WhatsApp group.

---

## 1. What is submitted

| # | Deliverable | Language | Venue requirement | Suggested owner |
| --- | --- | --- | --- | --- |
| 1 | **Project page** on spaceappschallenge.org | English | Project documentation; the submission is made there | P3 (documentation) with Owen |
| 2 | **YouTube video** | English | **≤ 30 s**: problem (5 s), solution (15 s), impact (10 s) | P4 (media) |
| 3 | **Pitch** | Spanish allowed | **≤ 3 min**, no questions. Slides in **Canva**; slide 1 with the project name and the **team number** | P1 (speaker) and P4 |
| 4 | **Deployed web app** | English | Judges must be able to try it; check the link before submitting | Javier (T10) |
| 5 | **Repository** with install instructions | English | Installation, code and dependencies, cited data and sources, screenshots | Owen and Gemini (code), Claude (docs) |
| 6 | **Use of AI** ("Super Intelligence") | English | Required by the global submission: describe how AI was used | Owen, based on [HISTORY.md](HISTORY.md) and the README |

**Venue judging criteria:**

| Criterion | What supports it | What is missing |
| --- | --- | --- |
| Technological innovation | Same metric at the same scale on three bodies (32 km local AEQD patches), computed on Yuca | — |
| Social impact | Section 3 of [value_proposition.md](value_proposition.md): accessible, cheap analog sites in Mexico and Latin America for training, instrument tests and outreach | Make it the third minute of the pitch |
| Documentation | `docs/` complete in English, with the history and every plan | Project page in English |
| Scalability | The pipeline is generic: another body or layer is another configuration entry, and it runs on HPC | Say it with a concrete example (for example, adding Mercury or a radar layer) |

---

## 2. Timeline

| When | Pipeline (Owen + Gemini, Yuca through OOD) | App (Javier) | Content (P1, P3, P4) |
| --- | --- | --- | --- |
| **Fri 13, night** | T6 done; T5 code done and smoke-tested. Launch the full T5 run. Gemini writes T7/T8 | Test deployment (GitHub Pages or Vercel) with `sample.json` | Confirm the team number; Canva skeleton |
| **Sat 9:00–11:00** | Check the full T5 run. T7/T8 smoke test on the T5 smoke output | Weights panel, site card and "Where the analogy breaks" | `limits.json` (T11) and test protocol texts |
| **Sat 11:00–14:00** | Real T7/T8 run; download `analogs_universe.json` through OOD | Connect the real JSON as soon as it exists | Pitch script (3 min) |
| **Sat 14:00** | **Decision point**: if there is no real JSON, use plan B (§4) | — | — |
| **Sat 14:00–18:00** | Sanity review (Olympus Mons check, score distribution, σ decision); a second run if needed | Deploy with the real JSON; test at 1366 × 768 | Canva slides; project page in English |
| **Sat 18:00–21:00** | **Freeze data.** Screenshots for the README; text on the use of AI | **Freeze code.** Check the public link | Record and upload the 30 s video; rehearse the pitch with a timer |
| **Sun, before the pitch** | Check the links on the project page | Check that the app opens from another network (phone) | **Submit** and a last rehearsal |

---

## 3. Checklist before submitting

**Project page (English):**

- [ ] Problem, solution and results, with real numbers from the run.
- [ ] The NASA and other agency data used, with links (see the README data table).
- [ ] What was **not** solved: the physical limits of each analog, roughness below 500 m, and no mineralogy. Base: "what we must not claim" in [value_proposition.md](value_proposition.md).
- [ ] Links to the app, the repository and the video.
- [ ] Use of AI: Claude (plans, documentation, review), Gemini (pipeline code) and whatever the rest of the team used. Base: [HISTORY.md](HISTORY.md).

**Repository:**

- [ ] README in English: what it is, how to install and run the app and the pipeline. Done; screenshots are still missing.
- [ ] Data and sources cited (README data table and [pipeline.md](pipeline.md)).
- [ ] Do not reorganise folders at the last minute. The venue *suggests* `/data`, `/models`, `/scripts` and `/docs`, but does not require them.

**App:**

- [ ] The public link opens without an account and from another network.
- [ ] It loads the real `analogs_universe.json`, or `sample.json` with a notice under plan B.
- [ ] Moving a slider re-orders the list in under 50 ms (T10 criterion).

**Pitch and video:**

- [ ] Slide 1: "Planetary Analog Finder" and the team number.
- [ ] Minute 1: problem and context. Minute 2: solution and technology (demo). Minute 3: social impact and scalability.
- [ ] The video is 30 s or less, in English, on YouTube (public or unlisted), with its link on the project page.
- [ ] Rehearsed with a timer: 3:00 or less.

---

## 4. Plan B (decide on Saturday at 14:00)

| Situation | What is submitted |
| --- | --- |
| T5 finished but T7/T8 did not | The app with the real T4 targets and the T5 Earth patches, ranked in a simple way. Say so on the page |
| T5 did not finish | The app on `sample.json` (v1 converted); T3 and T4 shown as v2 results (maps and targets). Say "full Earth run pending" |
| No access to Yuca | Same as the previous row; the offline kit has T3 and the gazetteers |

In every case: **do not claim results that were not run.**

---

## 5. Risks

- **Venue network:** SSH is blocked, and OOD works ([working_without_ssh.md](working_without_ssh.md)). The app deployment does not depend on Yuca.
- **A single working day:** if a run fails, diagnose it before resubmitting. There is no time for several blind attempts.
