import styles from "./DidoFigure.module.css";

/* Dido's states. Section 10.
 *
 * Ordered roughly by the arc of a styling session, because that is how they are read in
 * the code that drives them. */
export const DIDO_STATES = [
  "idle",
  "welcome",
  "listening",
  "asking",
  "thinking",
  "searching",
  "styling",
  "comparing",
  "assembling",
  "presenting",
  "success",
  "error",
  "offline",
] as const;

export type DidoState = (typeof DIDO_STATES)[number];

/** What a screen reader is told Dido is doing. The state is not visual-only. */
const STATE_LABEL: Record<DidoState, string> = {
  idle: "Dido is waiting",
  welcome: "Dido is ready",
  listening: "Dido is listening",
  asking: "Dido is asking a question",
  thinking: "Dido is thinking",
  searching: "Dido is searching the catalogue",
  styling: "Dido is styling",
  comparing: "Dido is comparing options",
  assembling: "Dido is assembling a look",
  presenting: "Dido is presenting a look",
  success: "Dido has finished",
  error: "Dido could not continue",
  offline: "Dido is unavailable",
};

/** The states that show the scan line, i.e. the ones where Dido is working. */
const WORKING: ReadonlySet<DidoState> = new Set([
  "thinking",
  "searching",
  "styling",
  "comparing",
  "assembling",
]);

export interface DidoFigureProps {
  state: DidoState;
  /** Suppresses the accessible label where a caption already carries it. */
  decorative?: boolean;
  className?: string;
}

/**
 * The renderer seam.
 *
 * This is deliberately one component with a single `state` input and no animation API of
 * its own. Swapping SVG for Rive, Lottie or WebGL later means replacing the body of this
 * function — nothing that calls it passes a timeline, a frame or a duration, so nothing
 * that calls it has to change. Section 10 asks for that abstraction and this is the whole
 * of it: an enum in, a picture out.
 *
 * V1 is inline SVG on purpose. It is a few hundred bytes, it inherits the design system's
 * colours through currentColor, it needs no runtime, and it does not cost a phone anything
 * — which is the constraint section 28 puts on Dido specifically.
 */
export function DidoFigure({ state, decorative = false, className }: DidoFigureProps) {
  const classes = [styles.figure, styles[state], className].filter(Boolean).join(" ");

  return (
    <svg
      viewBox="0 0 120 148"
      className={classes}
      role={decorative ? "presentation" : "img"}
      aria-label={decorative ? undefined : STATE_LABEL[state]}
      aria-hidden={decorative || undefined}
      data-dido-state={state}
      focusable="false"
    >
      {/* The cartouche: a hard vertical frame with cut corners. Egyptian by proportion and
          by the flat-topped arch, not by ornament. */}
      <path className={styles.frame} d="M22 14h76v92l-38 30-38-30z" />

      {/* An inner frame at a tight offset. Two rules a few millimetres apart is the single
          most characteristic move in the brand's line language. */}
      <path className={styles.frame} d="M30 22h60v80l-30 24-30-24z" opacity="0.45" />

      {/* Passage lines: the horizontal rhythm from the delivered pattern asset. */}
      <g className={styles.rules}>
        <path d="M30 40h60M30 52h60M30 96h60" />
      </g>

      {/* The aperture. Reads as attention without being an eye. */}
      <rect className={styles.aperture} x="46" y="58" width="28" height="32" />

      {/* The scan, only while Dido is working. */}
      {WORKING.has(state) ? <path className={styles.scan} d="M30 40h60" /> : null}
    </svg>
  );
}

export function didoStateLabel(state: DidoState): string {
  return STATE_LABEL[state];
}
