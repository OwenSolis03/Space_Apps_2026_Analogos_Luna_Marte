import { shallowRef, type ShallowRef } from "vue";
import type { Universe } from "@/lib/types";

export type Load =
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; data: Universe };

const DATA_URL = `${import.meta.env.BASE_URL}data/analogs_universe.json`;

// One shared load for every view that needs the universe (Results, How It Works, Data).
const load: ShallowRef<Load> = shallowRef({ state: "loading" });
let started = false;

function fetchUniverse(): void {
  load.value = { state: "loading" };
  fetch(DATA_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json() as Promise<Universe>;
    })
    .then((data) => {
      load.value = { state: "ready", data };
    })
    .catch((e: Error) => {
      load.value = { state: "error", message: e.message || "Failed to load data" };
    });
}

/** Triggers a reload of the analog universe data. */
export function retryUniverse(): void {
  fetchUniverse();
}

/** Returns the shared load state. The JSON is fetched once, on first use. */
export function useUniverse(): ShallowRef<Load> {
  if (!started) {
    started = true;
    fetchUniverse();
  }
  return load;
}
