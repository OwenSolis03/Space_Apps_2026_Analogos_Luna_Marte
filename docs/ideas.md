# Idea log

The team's ideas, discussed before the hackathon, with a general evaluation made with Claude. There is no data, tooling or site work here. The evaluations were provisional until the official resources came out on 13 November. This log is part of the use-of-AI description in the submission. How the final design came out of these ideas is in [HISTORY.md](HISTORY.md) §1.

## Idea 1: analog-site app with an adjustable score

**Proposed by:** Owen

**Idea:**

- Take the full planetary map, with every available information layer, and use image-processing models to identify sites analogous to Earth.
- Then compare layer by layer, giving each site a score that updates as the layers are processed. It would take into account resources, radiation, accessibility, altitude and other parameters.
- The result is a list that can be re-ordered by how much each parameter matters.
- The app would show the site, its terrestrial analog and the similar parameters, and could say what kind of mission the site suits.

**Evaluation:** feasible if the scope is reduced; doubtful as stated.

| Part | Evaluation | Reason |
| --- | --- | --- |
| Whole planet with every layer | Doubtful | Too much scope for 48 hours |
| Image-processing models | Doubtful | Training and validating them takes a long time, and the challenge asks to go beyond visual resemblance |
| Layer-by-layer score | Feasible | The logic is simple if the layers are comparable |
| List re-ordered by priorities | Feasible | It only recomputes a score with other weights |
| Radiation and other parameters with no Earth equivalent | Doubtful | They cannot be scored like the comparable ones |
| App showing site, analog and parameters | Feasible | Reachable if the results are pre-computed |
| Mission type per site | Feasible | Reachable as a minor addition |

**Fit with the challenge:** it does not show where the analogy breaks, which the challenge asks for explicitly.

### Version 2: trimmed

**Sent by:** Owen

**Idea:**

- Drop model training and the whole-planet scope.
- Use a pre-computed database of key sites, with weights to re-order the list by mission.
- Each place gets a "Limits of the analog" section. It explains which variables do match, such as mineralogy or terrain, and which have no point of comparison on Earth, such as the atmosphere or the radiation dose.

**Evaluation:** feasible.

| Part | Evaluation | Reason |
| --- | --- | --- |
| Pre-computed database of key sites | Feasible | Manageable scope, as long as it is built from 14 November on |
| Weights to re-order by mission | Feasible | It only recomputes a score with other weights |
| "Limits of the analog" section | Feasible | It answers the challenge directly |
| Matches without computation | Doubtful | The challenge asks for the analogy to be justified with data, not only described |
| Choice of sites | Doubtful | Picking them by hand can repeat known analogs, and the challenge wants to go beyond them |

### Version 3: numeric index and clustering

**Sent by:** Owen

**Idea:**

- Build a normalised numeric vector per site (elevation, slope, albedo, mineral abundance and thermal range).
- Compute a similarity index, such as cosine similarity or normalised Euclidean distance, against terrestrial sites.
- To avoid picking sites by hand, run unsupervised clustering, such as K-Means or DBSCAN, on a wider sample.
- Process the heavy part on the Yuca supercomputer, and bring only the resulting clusters into the app.

**Evaluation:** feasible at its core; doubtful if it depends on Yuca or on every metric.

| Part | Evaluation | Reason |
| --- | --- | --- |
| Similarity index with a testable formula | Feasible | Little code, verifiable result |
| Elevation, slope and albedo in the vector | Feasible | Comparable if scale and measurement method are equalised |
| Mineral abundance in the vector | Doubtful | It may not be measured equivalently across bodies |
| Thermal range in the vector | Doubtful | Moon or Mars ranges may fall outside Earth's and dominate the distance |
| Similarity percentage | Doubtful | It depends on the chosen metrics and weights, so it is not an absolute measure |
| Clustering on a wide sample | Feasible | Reachable if the sample is bounded and the groups are reviewed |
| Getting "novel" clusters | Doubtful | A cluster groups data; it does not prove a site is novel or a good analog |
| Processing on Yuca | Doubtful | Queues, data transfer and access from the venue can fail in 48 hours; whether its use is allowed also needed confirming |

**What the final design kept** (v2, see [HISTORY.md](HISTORY.md)):

- the testable index, as a per-dimension RBF;
- equalised scale, as 32 km patches at 500 m on every body;
- clustering, as 30 archetypes per body plus curated targets;
- Yuca, which worked.

Mineralogy was left out. The thermal comparison is done by rank within each body, not with absolute temperatures.

## Complementary ideas for each site's card

**Sent by:** Owen

| Idea | Description | Evaluation | Reason |
| --- | --- | --- | --- |
| Fictional mission log | A tab written as an astronaut's or planetary geologist's diary, contrasting the experience at the Earth site and at the target | Feasible | Cheap, but it must be labelled as fiction so it is not mistaken for results |
| Earth training protocol | A card saying what an agency could use the site for, such as rover mobility tests or isolation simulations | Feasible | Connects with the challenge, as long as each recommendation follows from the site's parameters |
| Logistics and human factor | A qualitative hostility scale for a person: visual fatigue from albedo, psychological complexity of the landscape, difficulty of moving in a suit | Doubtful | Easy to show but hard to justify with data; it could look like opinion |
| History and pop culture | One line with facts such as missions that trained at the analog or works inspired by the site | Feasible | Little work, but it needs cited sources, and a little-known site may have no story |
