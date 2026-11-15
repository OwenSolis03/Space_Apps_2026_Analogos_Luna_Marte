// Copy for the Results page. Source of the five claims: docs/value_proposition.md §7 ("What we must not claim"), copied as written.

export interface Claim {
  lead: string;
  body: string;
}

export const NOT_TO_CLAIM: Claim[] = [
  {
    lead: 'Do not say "we found the best analog".',
    body: "The score measures terrain at 32 km / 500 m scale, aridity and (for Mars) relative thermal contrast. It does not measure mineralogy, rock size or dust.",
  },
  {
    lead: "Do not present the score as an absolute percentage.",
    body: "It is a similarity relative to Earth's variability, and it depends on the weights. Lunar scores are systematically lower because terrestrial arid terrain rarely matches the extreme slope and relief of the lunar south pole at 32 km scale (see Algorithm for geomorphometry details).",
  },
  {
    lead: "Do not claim that a site is ice-free.",
    body: "Our data cannot tell an ice sheet from bare ground in Antarctica and Greenland. The ranking caps those sites at 3 per list.",
  },
  {
    lead: "Do not claim the Artemis III region coordinates are official.",
    body: "NASA publishes only the names; we anchor each region on the IAU feature of the same name and say so.",
  },
  {
    lead: "Do not claim results that were not run.",
    body: "If the full Earth run or T7 does not finish, say which parts of the app use sample data.",
  },
];
