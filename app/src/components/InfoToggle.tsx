import { EXPLANATION_HEADINGS, type Explanation } from "../lib/explanations";

export interface InfoToggleProps {
  id: string; // unique, e.g. "dim-topography"
  title: string; // e.g. "Topography" (used in the accessible name)
  open: boolean;
  onToggle: () => void;
  explanation: Explanation;
  actionHeading?: string; // default "What the slider does"
}

/** Circled "i" button. Sits next to the control's label, never inside the <label>. */
export function InfoButton({ id, title, open, onToggle }: Pick<InfoToggleProps, "id" | "title" | "open" | "onToggle">) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={`exp-${id}`}
      aria-label={`What does ${title} mean?`}
      onClick={onToggle}
      className="inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-full border border-frame text-fg transition-colors hover:border-fg active:bg-fg active:text-bg aria-expanded:border-fg aria-expanded:bg-accent aria-expanded:text-on-accent max-sm:size-8"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
    </button>
  );
}

/** The four-part explanation, placed right below the control. Hidden when closed. */
export function InfoPanel({ id, title, open, explanation, actionHeading = EXPLANATION_HEADINGS.slider }: Omit<InfoToggleProps, "onToggle">) {
  const parts: [string, string][] = [
    [EXPLANATION_HEADINGS.what, explanation.what],
    [EXPLANATION_HEADINGS.measure, explanation.measure],
    [actionHeading, explanation.slider],
    [EXPLANATION_HEADINGS.why, explanation.why],
  ];
  return (
    <div id={`exp-${id}`} role="region" aria-label={`${title}: explanation`} hidden={!open} className="info-panel grid gap-2 rounded-panel bg-surface-2 p-3 text-sm leading-relaxed text-fg">
      {parts.map(([h, t]) => (
        <div key={h}>
          <h4>{h}</h4>
          <p>{t}</p>
        </div>
      ))}
      {explanation.note && <p className="text-muted">{explanation.note}</p>}
    </div>
  );
}
