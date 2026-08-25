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
      viewBox="0 0 120 168"
      className={classes}
      role={decorative ? "presentation" : "img"}
      aria-label={decorative ? undefined : STATE_LABEL[state]}
      aria-hidden={decorative || undefined}
      data-dido-state={state}
      focusable="false"
    >
      {/* A STELA, not a face.
        *
        * Egyptian by proportion rather than by iconography: an upright slab with an arched
        * head, the doubled rule at a tight offset that runs through the whole brand, and a
        * rhythm of passage lines across it. There is no pharaoh here and nothing to
        * mistake for a mascot.
        *
        * An earlier attempt used a rectangle with a V-notch cut from the foot. At small
        * sizes that read as a shield or a badge, which is a different object entirely. */}
      <path className={styles.frame} d="M24 158 V60 A36 36 0 0 1 96 60 V158 Z" />
      <path className={styles.frame} d="M34 148 V62 A26 26 0 0 1 86 62 V148 Z" opacity="0.45" />

      {/* Passage lines: the horizontal rhythm from the delivered pattern asset. */}
      <g className={styles.rules}>
        <path d="M34 84h52M34 100h52M34 138h52" />
      </g>

      {/* The aperture: a tall vertical slot. Attention without an eye — and vertical, so
          the states that narrow it read as concentration rather than as a wink. */}
      <rect className={styles.aperture} x="52" y="76" width="16" height="46" />

      {/* The scan, only while Dido is working. */}
      {WORKING.has(state) ? <path className={styles.scan} d="M34 84h52" /> : null}
    </svg>
  );
}

export function didoStateLabel(state: DidoState): string {
  return STATE_LABEL[state];
}
