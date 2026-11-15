// Challenge page copy. Sources: the README ("The challenge"), docs/value_proposition.md §4 and §5,
// and the official challenge page (read on 2026-11-14), summarised as in the plan §10.1.

export const HACKATHON_COPY =
  "NASA Space Apps Challenge is an annual global hackathon led by NASA. Over one weekend, teams around the world use open data from NASA and its space agency partners to build solutions to challenges about Earth and space. It runs through local events hosted in cities worldwide.";

export const LOCAL_EVENT = {
  name: "NASA Space Apps Sonora 2026",
  place: "Tec de Monterrey, Campus Sonora Norte, Hermosillo",
  dates: "13–15 November 2026",
  url: "https://spaceappssonora.org/",
};

export const CALENDAR: { label: string; value: string }[] = [
  { label: "FRIDAY 13", value: "Bootcamp and opening" },
  { label: "SATURDAY 14", value: "Hackathon, 9:00–21:00" },
  { label: "SUNDAY 15", value: "Pitches, 9:00–14:00" },
];

export const CHALLENGE_TITLE = "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars";
export const OFFICIAL_URL = "https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/";

/** The three things the challenge asks every team to explain (README, "The challenge"). */
export const OUR_CHALLENGE: { code: string; title: string }[] = [
  { code: "01", title: "WHAT MAKES THE ANALOGY STRONG" },
  { code: "02", title: "WHERE IT BREAKS" },
  { code: "03", title: "HOW THE ANALOG WOULD HELP PREPARE MOON OR MARS EXPLORATION" },
];

export const WARNINGS: string[] = [
  "Visual resemblance is not enough.",
  "Scale matters.",
  "Well-known analogs (Atacama, Antarctica, Iceland, Hawaii) are already studied.",
  "Earth cannot reproduce reduced gravity, vacuum, the thin Martian atmosphere or space radiation.",
];

export const DIFFERENTIATOR =
  "Our differentiator in one sentence: we are the team that measures the analogy at planetary scale, with supercomputing, and shows just as clearly where it breaks.";

export const NASA_ASKS_ROWS: { ask: string; does: string; different: string }[] = [
  { ask: "\"Identify one or more locations\"", does: "A systematic search over every bare-land 32 km patch on Earth (~45,000 candidates after the vegetation filter), against 76 lunar and Martian targets", different: "We do not start from a list of sites; the sites come out of the computation" },
  { ask: "\"Go beyond visual similarity\"", does: "A score built from measured terrain features: slope, relief, hypsometry, roughness; plus aridity and, for Mars, thermal contrast", different: "The analogy can be audited and repeated" },
  { ask: "\"Go beyond known sites\"", does: "The method does not know what Atacama is. Sites inside 12 famous analog regions are labelled KNOWN_ANALOG, the rest NEW_CANDIDATE", different: "New candidates are a consequence of the method, not of intuition" },
  { ask: "\"Consider scale\"", does: "The same 32 km patch at 500 m/px on all three bodies, reprojected around its own centre", different: "The analog is a specific valley or range, and the comparison is fair across bodies" },
  { ask: "\"Where the analogy breaks\"", does: "Every site lists the features that do not match, in physical units, plus what Earth cannot reproduce (gravity, vacuum, atmosphere, radiation)", different: "Most teams will add it as a footnote; for us it is part of the result" },
  { ask: "\"Connect with exploration\"", does: "Real targets: the Artemis III candidate regions and the Mars landing sites. Mission presets: mobility, base construction, dust and thermal", different: "The ranking answers an engineering question" },
  { ask: "\"Use open data\"", does: "MOLA, THEMIS, LOLA, LROC WAC, Diviner, Copernicus GLO-90, MODIS, Natural Earth and IAU nomenclature", different: "Every target has an official name and every analog verifiable coordinates" },
];
