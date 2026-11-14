// About page copy. The story text is the approved English translation (docs/plan_t18_website.md §10.2), copied as written.
import fernando from "@/assets/team/fernando_borquez.webp";
import elias from "@/assets/team/elias_peregrina.webp";
import emily from "@/assets/team/emily_beltran.webp";
import flor from "@/assets/team/flor_machado.webp";
import javier from "@/assets/team/javier_miranda.webp";
import owen from "@/assets/team/owen_solis.webp";

export const STORY: string[] = [
  "Endurance CXXV is a team of Computer Science students brought together by an interest in technology, innovation and building solutions to real-world problems.",
  "Our story began in 2024. Since then we have taken part in competitions, innovation events and research experiences.",
  "Each experience has helped us grow as a team, explore new technologies, face different challenges and find out how far we can go working together.",
  "We are eight students: a team that started as a group of friends and keeps looking for new challenges and opportunities to take our ideas further.",
];
export const STORY_CLOSING = "ENDURANCE CXXV — FROM DATA TO ACTION.";

export interface TrackRecord {
  year: string;
  event: string;
  award?: string;
  tone?: "signal" | "outline";
}

export const TRACK_RECORD: TrackRecord[] = [
  { year: "2024", event: "NASA Space Apps Challenge 2024" },
  { year: "2025", event: "Summer of Research 2025 — Universidad de Guadalajara" },
  { year: "2025", event: "NASA Space Apps Challenge 2025" },
  { year: "2026", event: "TE AI Cup 2026", award: "1ST PLACE · INTERNATIONAL", tone: "signal" },
  { year: "2026", event: "SmartCity Hackathon 2026", award: "PEOPLE'S CHOICE", tone: "signal" },
  { year: "2026", event: "Health Systems Innovation Lab Hackathon 2026", award: "3RD PLACE", tone: "signal" },
  { year: "2026", event: "NASA Space Apps Challenge 2026", award: "IN PROGRESS", tone: "outline" },
];

export interface Member {
  name: string;
  photo?: string;
  linkedin?: string;
}

/** Eight crew slots. Two are still pending: add a member by adding an object here. */
export const CREW: Member[] = [
  { name: "Ángel Fernando Bórquez Guerrero", photo: fernando, linkedin: "https://www.linkedin.com/in/fernandoborquez/" },
  { name: "Elías Peregrina Cázares", photo: elias, linkedin: "https://www.linkedin.com/in/el%C3%ADas-peregrina-c%C3%A1zares-4886503a7/" },
  { name: "Emily Margarita Beltrán Zazueta", photo: emily, linkedin: "https://www.linkedin.com/in/emily-beltran-b712a2421/" },
  { name: "Flor María Machado Félix", photo: flor, linkedin: "https://www.linkedin.com/in/flor-maria-machado-felix-a318633a8/" },
  { name: "Javier Leonardo Miranda Sánchez", photo: javier, linkedin: "https://www.linkedin.com/in/javier-miranda-sanchez-201aa1383/" },
  { name: "Owen Adiel Solis Zatarain", photo: owen, linkedin: "https://www.linkedin.com/in/owen-solis/" },
  { name: "" },
  { name: "" },
];

export const ACKNOWLEDGEMENTS =
  "This project was developed in collaboration with ACARUS (Área de Cómputo de Alto Rendimiento de la Universidad de Sonora), using Yuca, the University of Sonora's high-performance computing cluster. It would not have been possible without their support.";
