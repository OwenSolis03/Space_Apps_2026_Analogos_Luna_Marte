import { onScopeDispose, ref, type Ref } from "vue";

/** Reactive `matchMedia` result. Updates when the media query changes. */
export function useMediaQuery(query: string): Ref<boolean> {
  const list = typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(query)
    : null;
  const matches = ref(list?.matches ?? false);
  const onChange = (event: MediaQueryListEvent) => {
    matches.value = event.matches;
  };
  list?.addEventListener("change", onChange);
  onScopeDispose(() => list?.removeEventListener("change", onChange));
  return matches;
}
