import type { Dimension } from "./types";

// Plain-language copy for the Scenario panel (docs/plan_t17_plain_language.md, section 3).
// Copy only: no JSX here. If a dimension's sources change in the export, update "measure" in the same commit.

export interface Explanation {
  what: string;
  measure: string;
  slider: string;
  why: string;
  note?: string; // optional extra line, shown muted (limits, availability)
}

export const INTRO =
  "Each Earth place gets a similarity score from 0 to 100 (the MSI) against the Moon or Mars site you pick. Choose a mission case, or move the sliders to decide which aspects count most.";

export const DIM_EXPLANATION: Record<Dimension, Explanation> = {
  topography: {
    what: "The shape of the land: how steep it is and how much it rises and falls.",
    measure:
      "We cut every place into a 32 by 32 km square with one height value every 500 m, the same on Earth, the Moon and Mars. From that we take the average slope, the steepest parts, the difference between the highest and lowest points, and whether the square is mostly high ground or mostly low ground. Heights come from laser altimeters (MOLA on Mars, LOLA on the Moon) and the Copernicus elevation model on Earth.",
    slider: "The higher it is, the more the ranking prefers Earth places whose land has the same shape as the target.",
    why: "Landers need gentle slopes, rovers have a maximum slope they can climb, and the shape of the land decides where you can drive, land and build.",
  },
  roughness: {
    what: "How bumpy the ground is once the general tilt is removed: hills, ridges and crater rims inside the square.",
    measure:
      "From the same 32 km height grid: how much the ground goes up and down around a flat fit, and how different each point is from its neighbours.",
    slider: "The higher it is, the more the ranking prefers places with the same amount of bumpiness.",
    why: "Bumpy ground is harder to drive and riskier to land on. Smooth ground is good for long drives and for testing how a rover keeps track of where it is.",
    note: "With one value every 500 m this sees hills and ridges, not individual rocks.",
  },
  environment: {
    what: "Whether the Earth place is bare ground, like the Moon and Mars, or covered with plants.",
    measure:
      "NASA's MODIS satellite measures how green the ground is every month. We take the greenest month of 2023: the greener the place, the lower this score. Ice sheets count as bare because nothing grows there.",
    slider: "The higher it is, the more it pushes down places with vegetation.",
    why: "The Moon and Mars have no plants. A field test on bare rock and soil is much closer to the real thing than one in a forest or a field.",
  },
  thermal: {
    what: "How much the ground temperature changes between day and night.",
    measure:
      "Mars: the THEMIS camera on Mars Odyssey, which sees heat. Earth: NASA's MODIS satellite. The two planets have very different temperatures, so we do not compare degrees: we compare how extreme each place is within its own planet, from 0 (smallest swing) to 1 (largest swing).",
    slider: "The higher it is, the more it prefers Earth places that are as extreme at home as the target is on Mars.",
    why: "On Mars a large swing usually means fine dust or sand, and a small swing means solid rock that keeps the heat. Equipment also has to survive being heated and cooled every day.",
    note: "Only for Mars. There is no matching dataset for the Moon, so it is switched off there.",
  },
  geology: {
    what: "The type of rock that covers the region: for example volcanic, sedimentary, crystalline or impact rock.",
    measure:
      "Geologic maps of each body (GLiM for Earth, USGS maps for the Moon and Mars), translated into 8 rock families shared by the three bodies. Similar families score high, different ones score low.",
    slider: "The higher it is, the more it prefers Earth places with the same kind of rock as the target.",
    why: "The rock decides the soil the wheels drive on, what the instruments will find, and what could be used as building material.",
    note: "These are regional maps: they say what most of the region is made of, not what each outcrop is.",
  },
  dust: {
    what: "How dusty the air is and how that changes through the year.",
    measure:
      "Mars: a record of dust in the Martian atmosphere over several years. Earth: dust and haze measured by NASA's MODIS satellite. As with temperature, each place is compared within its own planet: how dusty it is, how much the dust changes between seasons, and when its dusty season comes.",
    slider: "The higher it is, the more it prefers Earth places whose dust behaves like the target's.",
    why: "Dust covers solar panels, wears out moving parts and, in storms, blocks the light. Dusty places on Earth are where those problems can be tested.",
    note: "Only for Mars. Places with no dust measurement on Earth (for example ice sheets, where the satellite cannot measure it) score 0 here instead of being skipped.",
  },
  ice: {
    what: "Whether there is water ice, and very cold spots (cold traps) where ice can last.",
    measure:
      "Moon: temperatures from the Diviner instrument on NASA's Lunar Reconnaissance Orbiter near the south pole. Mars: mapped shallow ice. Earth: temperatures from MODIS and mapped ice.",
    slider: "The higher it is, the more it prefers cold, icy Earth places for targets that have ice.",
    why: "Water can be turned into drinking water, oxygen and rocket fuel. Finding and extracting it is key for a permanent base.",
    note: 'Only sites with ice data can be scored on this. In the "Water ice and cold traps" case, sites without ice data are not ranked, and a note under the ranking lists them.',
  },
};

export const CONTROL_EXPLANATION: {
  minScore: Explanation;
  road: Explanation;
  newOnly: Explanation;
  weightsShare: string;
} = {
  weightsShare:
    "The percentage is how much of the score each aspect counts right now. They always add up to 100%, so raising one lowers the share of the others.",
  minScore: {
    what: "A filter on the score.",
    measure:
      'The MSI goes from 0 to 100. 100 means the Earth place matches the target on everything the mission case looks at; it does not mean the place is "better" in general.',
    slider: "Hides targets whose best Earth match scores below the number you choose.",
    why: "It lets you focus on the clearest matches. Scores are only comparable within the same mission case.",
  },
  road: {
    what: "A bonus for Earth places that are easy to reach.",
    measure: "Distance from each place to the nearest road (Natural Earth map).",
    slider:
      "At 0, distance is ignored. At the maximum, a place 50 km from a road keeps about 88% of its score, one 100 km away about 81%, and one 300 km away about 72%. Places next to a road keep their full score.",
    why: "Field campaigns near a road are cheaper, safer and can be repeated more often than expeditions to remote places.",
  },
  newOnly: {
    what: "A switch to hide places that are already famous as Moon or Mars analogs.",
    measure:
      "We mark Earth places inside nine well-known analog regions: the Atacama Desert, Iceland, the McMurdo Dry Valleys, Devon Island, Svalbard, Utah (MDRS), the Mojave Desert, Meteor Crater and the Pilbara.",
    slider: "When it is on, those places disappear from the results and only new candidates remain.",
    why: "The challenge asks to go beyond the sites everyone already uses. This shows what is left when the famous ones are taken out.",
  },
};

/** Headings of the four blocks, always in this order. The third one changes for the switch. */
export const EXPLANATION_HEADINGS = {
  what: "What it is",
  measure: "How we measure it",
  slider: "What the slider does",
  switch: "What the switch does",
  why: "Why it matters",
} as const;

export const PRESET_EXPLANATION: Record<string, string> = {
  mobility_and_traction: "Where to test how rovers drive: mostly the shape and bumpiness of the land, plus rock type.",
  construction_and_base: "Where to rehearse landing and building a base: mostly gentle, stable land and the type of rock.",
  geology_and_materials: "Where to train geologists and test instruments: mostly the type of rock.",
  dust_and_seasons: "Where to test equipment against dust and seasonal storms: mostly dust and temperature swings. Mars only.",
  isru_and_ice: "Where to practise finding and using water ice: mostly ice and very cold spots. Only sites with ice data are ranked.",
};
