import type { ReactNode } from "react";
import { cx } from "./primitives";
import styles from "./Badge.module.css";

export type BadgeTone = "neutral" | "accent" | "success" | "warning" | "info";

export function Badge({
  tone = "neutral",
  dot = false,
  children,
}: {
  tone?: BadgeTone;
  dot?: boolean;
  children: ReactNode;
}) {
  return (
    <span className={cx(styles.badge, styles[tone])}>
      {dot ? <span className={styles.dot} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

/**
 * Marks content that is demonstration material rather than a real offering.
 *
 * Section 47. Where a surface shows fixture data it must say so on the surface, not in a
 * footnote — a reviewer who cannot tell the difference will assume the flattering reading.
 */
export function FixtureBadge({ children = "Demo content" }: { children?: ReactNode }) {
  return (
    <Badge tone="warning" dot>
      {children}
    </Badge>
  );
}

/**
 * A filter chip.
 *
 * A button with aria-pressed rather than a styled div, so its state is announced and it is
 * operable from a keyboard without anything extra.
 */
export function Chip({
  selected = false,
  onClick,
  children,
  testId,
}: {
  selected?: boolean;
  onClick: () => void;
  children: ReactNode;
  /** An explicit prop rather than a spread: a chip should not accept arbitrary attributes. */
  testId?: string;
}) {
  return (
    <button
      type="button"
      className={cx(styles.chip, selected && styles.chipSelected)}
      aria-pressed={selected}
      onClick={onClick}
      data-testid={testId}
    >
      {children}
    </button>
  );
}

export function ChipRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.chipRow} role="group" aria-label={label}>
      {children}
    </div>
  );
}
