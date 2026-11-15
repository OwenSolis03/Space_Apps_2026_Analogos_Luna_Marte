import type { Ref } from "vue";
import { useMediaQuery } from "./useMediaQuery";

/** True when the visitor asks for reduced motion. Animations then render their final state. */
export function useReducedMotion(): Ref<boolean> {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}
