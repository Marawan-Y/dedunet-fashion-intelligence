import type { ElementType, ReactNode } from "react";
import styles from "./primitives.module.css";

/* Layout primitives.
 *
 * Every one takes an `as` so the right ELEMENT can be chosen for the meaning while the
 * styling stays the same. A section that is really a <nav> should be a <nav>; making that
 * awkward is how landmark structure quietly degrades into a page of divs.
 */

export function cx(...parts: Array<string | false | null | undefined>): string | undefined {
  const joined = parts.filter(Boolean).join(" ");
  /* Return undefined rather than "" so React omits the attribute entirely. An empty
     class attribute is harmless but it is also noise in every snapshot and DOM dump. */
  return joined || undefined;
}

interface BoxProps {
  as?: ElementType;
  className?: string;
  children?: ReactNode;
  [key: string]: unknown;
}

export function Container({ as: As = "div", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.container, className)} {...rest}>
      {children}
    </As>
  );
}

export function Editorial({ as: As = "div", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.editorial, className)} {...rest}>
      {children}
    </As>
  );
}

export function Section({
  as: As = "section",
  tight = false,
  className,
  children,
  ...rest
}: BoxProps & { tight?: boolean }) {
  return (
    <As className={cx(tight ? styles.sectionTight : styles.section, className)} {...rest}>
      {children}
    </As>
  );
}

export function Stack({
  as: As = "div",
  gap = "base",
  className,
  children,
  ...rest
}: BoxProps & { gap?: "tight" | "base" | "loose" }) {
  const spacing =
    gap === "tight" ? styles.stackTight : gap === "loose" ? styles.stackLoose : undefined;
  return (
    <As className={cx(styles.stack, spacing, className)} {...rest}>
      {children}
    </As>
  );
}

export function Row({ as: As = "div", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.row, className)} {...rest}>
      {children}
    </As>
  );
}

export function Grid({
  as: As = "div",
  variant = "base",
  className,
  children,
  ...rest
}: BoxProps & { variant?: "base" | "wide" | "two" }) {
  const layout =
    variant === "wide" ? styles.gridWide : variant === "two" ? styles.gridTwo : styles.grid;
  return (
    <As className={cx(layout, className)} {...rest}>
      {children}
    </As>
  );
}

/**
 * A horizontal rail on a phone, a grid on a desktop.
 *
 * Labelled as a group so a screen reader announces what the swipeable region contains, and
 * keyboard-scrollable because an overflow container that only responds to touch strands
 * anyone not using a finger.
 */
export function Rail({ label, className, children, ...rest }: BoxProps & { label: string }) {
  return (
    <div
      className={cx(styles.rail, className)}
      role="group"
      aria-label={label}
      tabIndex={0}
      {...rest}
    >
      {children}
    </div>
  );
}

export function Eyebrow({ as: As = "p", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.eyebrow, className)} {...rest}>
      {children}
    </As>
  );
}

export function Lede({ as: As = "p", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.lede, className)} {...rest}>
      {children}
    </As>
  );
}

export function Muted({ as: As = "p", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.muted, className)} {...rest}>
      {children}
    </As>
  );
}

/** Small print. Uses the corrected contrast role, never the low-contrast brand token. */
export function Subtle({ as: As = "p", className, children, ...rest }: BoxProps) {
  return (
    <As className={cx(styles.subtle, className)} {...rest}>
      {children}
    </As>
  );
}

export function Divider({ className, ...rest }: { className?: string }) {
  return <hr className={cx(styles.divider, className)} {...rest} />;
}

/**
 * A section heading with its eyebrow and an optional trailing action.
 *
 * `level` is a required prop rather than a default, because the heading level is a document
 * structure decision and a default is how a page ends up jumping from h1 to h3. A test
 * asserts no level is skipped on any route.
 */
export function SectionHead({
  eyebrow,
  title,
  level,
  action,
  id,
}: {
  eyebrow?: string;
  title: string;
  level: 2 | 3 | 4;
  action?: ReactNode;
  id?: string;
}) {
  const Heading = `h${level}` as ElementType;
  return (
    <div className={styles.sectionHead}>
      <div className={styles.sectionHeadText}>
        {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
        <Heading id={id}>{title}</Heading>
      </div>
      {action}
    </div>
  );
}
