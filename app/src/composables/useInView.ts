import { onBeforeUnmount, onMounted, type Ref } from "vue";

/**
 * Calls `onEnter` once, when at least `threshold` of the element is visible.
 * Without IntersectionObserver the callback runs immediately, so the content is never left unplayed.
 */
export function useInView(target: Ref<Element | null>, onEnter: () => void, threshold = 0.4): void {
  let observer: IntersectionObserver | undefined;
  let done = false;

  const fire = () => {
    if (done) return;
    done = true;
    observer?.disconnect();
    onEnter();
  };

  onMounted(() => {
    const el = target.value;
    if (!el) return fire();
    if (typeof IntersectionObserver === "undefined") return fire();
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) fire();
      },
      { threshold },
    );
    observer.observe(el);
  });

  onBeforeUnmount(() => observer?.disconnect());
}
