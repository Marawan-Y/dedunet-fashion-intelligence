import { useEffect, useRef, useState } from "react";
import { mediaUrl } from "../../api/client";
import { ButtonLink } from "../../components/Button";
import { brand } from "../../lib/brand";
import { useReveal } from "../../lib/useReveal";
import { DidoFigure, didoStateLabel, type DidoState } from "./DidoFigure";
import styles from "./DidoMoment.module.css";

/* The staged sequence.
 *
 * Each step is a real DidoState from the existing character architecture — nothing new was
 * invented for the animation, which is what section 5 means by using the existing
 * character and motion architecture. `pieces` is how many garment plates have arrived by
 * that point, so the assembly and the character stay in step. */
const SEQUENCE: { state: DidoState; hold: number; pieces: number }[] = [
  { state: "welcome", hold: 900, pieces: 0 },
  { state: "listening", hold: 1100, pieces: 0 },
  { state: "thinking", hold: 1300, pieces: 0 },
  { state: "searching", hold: 1200, pieces: 1 },
  { state: "assembling", hold: 1200, pieces: 2 },
  { state: "presenting", hold: 2600, pieces: 3 },
];

export interface DidoMomentPiece {
  /** Server-relative artwork path for a REAL catalogue piece. */
  image?: string | null;
  label: string;
  alt: string;
}

/**
 * Dido, as the signature moment on Home.
 *
 * A cinematic sequence rather than a decorative loop: the character moves through the
 * states of an actual styling pass while three real catalogue plates assemble beside it,
 * joined by a rule that draws itself. It is the platform's core promise shown rather than
 * described.
 *
 * THREE THINGS IT DELIBERATELY DOES NOT DO.
 *
 * It does not start until it is on screen, so a phone spends nothing on it while the
 * reader is still in the hero. It does not loop forever — it runs once and rests on
 * `presenting`, because a section that keeps re-animating is a section nobody can read
 * past. And it does not claim Dido works: the copy says plainly that the intelligence is
 * not built, because a convincing animation of a capability that does not exist is the
 * most misleading thing this page could contain.
 */
export function DidoMoment({ pieces }: { pieces: DidoMomentPiece[] }) {
  const { ref, revealed } = useReveal<HTMLElement>({ threshold: 0.25 });
  const [step, setStep] = useState(-1);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    if (!revealed) return;

    /* Under reduced motion, land on the finished state immediately. The tokens already
       zero every duration, but stepping through six states with zero-length holds is a
       burst of re-renders for no visible benefit. */
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduced) {
      setStep(SEQUENCE.length - 1);
      return;
    }

    let elapsed = 0;
    SEQUENCE.forEach((entry, index) => {
      const id = window.setTimeout(() => setStep(index), elapsed);
      timers.current.push(id);
      elapsed += entry.hold;
    });

    const pending = timers.current;
    return () => {
      for (const id of pending) window.clearTimeout(id);
      pending.length = 0;
    };
  }, [revealed]);

  const current = SEQUENCE[Math.max(0, Math.min(step, SEQUENCE.length - 1))]!;
  const started = step >= 0;
  const state: DidoState = started ? current.state : "idle";
  const arrived = started ? current.pieces : 0;

  return (
    <section ref={ref} className={styles.moment} aria-labelledby="dido-moment-title">
      <img className={styles.ground} src={mediaUrl(brand.assets.pattern)} alt="" aria-hidden="true" />

      <div className={styles.inner}>
        <div className={styles.copy}>
          <p className={styles.eyebrow}>
            <span className={styles.eyebrowRule} aria-hidden="true" />
            Meet Dido
          </p>

          <h2 id="dido-moment-title" className={styles.title}>
            Tell it where you are going. <em>It does the rest.</em>
          </h2>

          <p className={styles.body}>
            Dido reads the occasion, not just the catalogue. It asks what you are dressing
            for, what you already own and what you are willing to spend, then assembles
            complete looks and explains every choice.
          </p>

          <div className={styles.actions}>
            <ButtonLink to="/dido" variant="accent">
              Style with Dido
            </ButtonLink>
          </div>

          <p className={styles.note}>
            The conversation is built. The intelligence behind it is not — Dido will tell you
            so itself rather than inventing a recommendation.
          </p>
        </div>

        {/* aria-hidden: this is an illustration of a capability described in full by the
            copy beside it. Announcing six state changes and three unlabelled plates would
            be noise, and the honest summary is already in the text. */}
        <div className={styles.stage} aria-hidden="true">
          <div className={styles.figureColumn}>
            <DidoFigure state={state} decorative className={styles.figure} />
            <span className={styles.state}>{started ? didoStateLabel(state) : ""}</span>
          </div>

          <span
            className={`${styles.thread} ${arrived > 0 ? styles.threadIn : ""}`}
            style={{ width: "var(--ds-space-5)" }}
          />

          <div className={styles.pieces}>
            {pieces.slice(0, 3).map((piece, index) => (
              <div
                key={piece.label}
                className={`${styles.piece} ${index < arrived ? styles.pieceIn : ""}`}
                style={{ transitionDelay: `${index * 90}ms` }}
              >
                {piece.image ? (
                  <img src={mediaUrl(piece.image)} alt="" loading="lazy" decoding="async" />
                ) : null}
                <span className={styles.pieceLabel}>{piece.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
