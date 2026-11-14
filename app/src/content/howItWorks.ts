// Copy for How It Works. Plain language, no formulas and no code. Source: docs/plan_t18_website.md §9.

export interface StageCopy {
  code: string;
  title: string;
  lead: string;
  body: string[];
}

export const STAGES: StageCopy[] = [
  {
    code: "STAGE.01",
    title: "INPUT",
    lead: "Three worlds, one question.",
    body: [
      "In: elevation maps of the Moon (LOLA), Mars (MOLA) and Earth (Copernicus), plus vegetation, temperature, rock type, dust and ice layers.",
    ],
  },
  {
    code: "STAGE.02",
    title: "SAME SQUARE",
    lead: "Every place is cut into the same square.",
    body: ["Each square is 32 by 32 km, with one height value every 500 metres. The same square is used on the Moon, on Mars and on Earth."],
  },
  {
    code: "STAGE.03",
    title: "MEASURE",
    lead: "From each square we take six numbers that describe the terrain.",
    body: ["How steep it is, how much relief it has, how bumpy it is. Elevation itself is never compared, because the reference levels of each planet differ."],
  },
  {
    code: "STAGE.04",
    title: "FILTER",
    lead: "The Moon and Mars have no plants.",
    body: ["So Earth squares with vegetation are removed. What remains is bare ground, which is where a Moon or Mars analog can be."],
  },
  {
    code: "STAGE.05",
    title: "COMPARE",
    lead: "Each Earth square gets a similarity from 0 to 100 on seven aspects.",
    body: [
      "You choose which aspects matter for your mission. The example below is Jezero crater, the Perseverance landing site, and its best Earth analog for the rover mobility preset.",
    ],
  },
  {
    code: "STAGE.06",
    title: "OUTPUT",
    lead: "Out: a ranked list of Earth places.",
    body: ["Each place comes with what matches, where the analogy breaks, and how far it is from a road."],
  },
];

export const CLOSING = {
  title: "WHAT EARTH CANNOT REPRODUCE: GRAVITY, VACUUM, RADIATION",
  text: "Earth cannot reproduce reduced gravity, vacuum, the thin Martian atmosphere or space radiation. The limits of each body are listed on the Results page.",
};
