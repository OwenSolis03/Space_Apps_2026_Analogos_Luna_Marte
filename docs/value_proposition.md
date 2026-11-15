# Value proposition: PROTOTERRA

*Grounded in Earth. Built for beyond.*

Base material for the pitch and video team. It covers:

- what problem we solve and what we offer;
- what we do beyond what NASA asks;
- how we differ from other teams on the same challenge.

Checked on 2026-11-13 against the [challenge page](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/), and updated for the v2 pipeline. The evaluation criteria of our venue are technological innovation, social impact, documentation and scalability ([submission.md](submission.md)).

## 1. The problem

The challenge itself says it: the terrestrial analogs used today (Atacama, Haughton, Death Valley, Antarctica, Iceland, Hawaii) **are not well characterised**. They were chosen from experience or visual resemblance, not by a systematic search.

That causes three concrete problems:

1. **Always the same sites.** Missions prepare in a handful of famous, expensive and remote places. Better or cheaper analogs may exist that nobody has looked for.
2. **"It looks similar" is not data.** Without a metric you cannot say *how* analogous a site is, *in what way*, and *in what way not*.
3. **One analog does not fit every test.** A site can be good for rover mobility tests and poor for thermal ones. Today there is no quick way to pick the analog for the test you want to run.

## 2. Value proposition

**In one line:**

> A search engine that sweeps the whole Earth with open data and tells you which place resembles a Moon or Mars site, in numbers: in what way it is similar, in what way it is not, and what test it is good for.

**30-second version:**

> Before going to the Moon or Mars, mission teams rehearse on Earth, but almost always in the same five places, chosen because they "look similar". Planetary Analog Finder measures the terrain of the Moon, Mars and Earth in exactly the same way, with NASA, USGS and ESA data processed on the Yuca supercomputer at the University of Sonora. It ranks Earth sites against the Artemis III landing regions and the Mars landing sites. For each one it shows the similarity score, what matches, where the analogy breaks, and how far it is from a road. Users can re-weight the ranking for their mission. It does not rediscover Atacama: it finds candidates nobody had looked at.

**For whom** (the user is the hero, the tool is the guide):

| User | What they gain |
| --- | --- |
| Mission engineer | Choose where to test a rover, a suit or a manoeuvre for the terrain it will face |
| Planetary geologist | New candidates with metrics to justify fieldwork |
| Agencies and universities outside the US and Europe | Analogs close to home, without depending on distant and expensive sites |
| Public and students | See that a place they know "is" a piece of Mars or the Moon, and why not entirely |

## 3. Social impact

This is one of the four judging criteria at our venue.

- **Cheaper access to analog research.** Most analog campaigns go to remote polar or island sites. A ranked list of accessible sites, with distances to roads and airports, lets universities, small agencies and student teams in Mexico and Latin America test instruments and train people close to home.
- **Local scientific capacity.** The pipeline runs on a public university supercomputer (Yuca, UniSon) with open data, and it is open source. Others can reproduce it, audit it and extend it.
- **Education and outreach.** "This valley near you behaves like this region of Mars, and here is why it does not entirely" is a concrete, data-backed hook for science education.

## 4. What we do beyond what NASA asks

| What NASA asks | What the project does | Why it is different |
| --- | --- | --- |
| "Identify one or more locations" | A systematic search over every bare-land 32 km patch on Earth (~45,000 candidates after the vegetation filter), against 76 lunar and Martian targets | We do not start from a list of sites; the sites come out of the computation |
| "Go beyond visual similarity" | A score built from measured terrain features: slope, relief, hypsometry, roughness; plus aridity and, for Mars, thermal contrast | The analogy can be audited and repeated |
| "Go beyond known sites" | The method does not know what Atacama is. Sites inside 12 famous analog regions are labelled `KNOWN_ANALOG`, the rest `NEW_CANDIDATE` | New candidates are a consequence of the method, not of intuition |
| "Consider scale" | The same 32 km patch at 500 m/px on all three bodies, reprojected around its own centre | The analog is a specific valley or range, and the comparison is fair across bodies |
| "Where the analogy breaks" | Every site lists the features that do not match, in physical units, plus what Earth cannot reproduce (gravity, vacuum, atmosphere, radiation) | Most teams will add it as a footnote; for us it is part of the result |
| "Connect with exploration" | Real targets: the Artemis III candidate regions and the Mars landing sites. Mission presets: mobility, base construction, dust and thermal | The ranking answers an engineering question |
| "Use open data" | MOLA, THEMIS, LOLA, LROC WAC, Diviner, Copernicus GLO-90, MODIS, Natural Earth and IAU nomenclature | Every target has an official name and every analog verifiable coordinates |

**What we add that the challenge does not ask for:**

- **Real supercomputing.** Tens of GB of rasters processed on Yuca. That is why the search can be global instead of regional.
- **A ranking that re-orders.** We do not deliver "the" analog, but a tool to choose it for the mission.
- **Logistics as a criterion.** Each site shows its distance to the nearest road and airport, and the app can favour accessible sites.

## 5. Differentiators against other teams

We cannot see other teams' projects before submission, so this rests on the approaches the challenge itself suggests and on the most likely ones in a hackathon. These are hypotheses, not data.

| Likely approach of other teams | Its limit | Our answer |
| --- | --- | --- |
| A report on a famous site (Atacama, Pinacate, Río Tinto) | It is exactly what the challenge asks to go beyond | Sites come from a global computation, not a prior choice |
| Image comparison or visual ML | The challenge warns that "looking similar" is not enough | We compare physical terrain metrics, not pixels |
| A map or catalogue of known analogs | It organises what exists; it does not discover | We propose new candidates with their score |
| A chatbot or AI app that explains | It explains, but does not measure | Every statement comes from a computed number |
| A similarity ranking without limits | It gives a percentage that looks absolute | We show what matches, what does not, and what Earth cannot reproduce |

**Our differentiator in one sentence:** we are the team that *measures* the analogy at planetary scale, with supercomputing, and shows just as clearly where it breaks.

**A local advantage nobody else has:** the team is in Sonora, with access to Yuca. If the final results include candidates in northwest Mexico, we can say "this is a few hours from here".

## 6. Example candidates

The v1 prototype produced candidates in Sonora and Baja California. Those numbers are **not valid anymore**: v1 compared windows of different sizes per body, had no vegetation mask, and doubled every lunar vertical metric. The v2 results come from the T7 run. Pick the examples for the pitch from `analogs_universe.json` once T7 has run, and check each point on a map before naming it.

## 7. What we must not claim

To survive questions from the judges:

- **Do not say "we found the best analog".** The score measures terrain at 32 km / 500 m scale, aridity and (for Mars) relative thermal contrast. It does not measure mineralogy, rock size or dust.
- **Do not present the score as an absolute percentage.** It is a similarity relative to Earth's variability, and it depends on the weights. Lunar scores are low because Earth has very little arid terrain as rugged as the lunar south pole at this scale. That is a finding, not a bug.
- **Do not claim that a site is ice-free.** Our data cannot tell an ice sheet from bare ground in Antarctica and Greenland. The ranking caps those sites at 3 per list.
- **Do not claim the Artemis III region coordinates are official.** NASA publishes only the names; we anchor each region on the IAU feature of the same name and say so.
- **Do not claim results that were not run.** If the full Earth run or T7 does not finish, say which parts of the app use sample data.

Details and history: [HISTORY.md](HISTORY.md) and [logbook.md](logbook.md).
