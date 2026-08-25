import type { ElementType, ReactNode } from "react";
import { Link } from "react-router-dom";
import { Media, type MediaRatio } from "./Media";
import { cx } from "./primitives";
import styles from "./Card.module.css";

export interface CardProps {
  to: string;
  title: string;
  /** The brand the piece comes from. Section 16: attribution is not optional. */
  brand?: string;
  meta?: string;
  image?: string | null;
  imageAlt: string;
  ratio?: MediaRatio;
  fit?: "cover" | "contain";
  slot: string;
  note?: string;
  footer?: ReactNode;
  testId?: string;
  /**
   * The heading level for the card title.
   *
   * Explicit, with a default of 3, because a card's correct level depends on what is above
   * it: under a section h2 it is an h3, but in a grid that follows the page h1 directly it
   * must be an h2 or the outline jumps h1 -> h3. Hard-coding h3 is what produced exactly
   * that skip on Shop and Brands, and a screen-reader user loses the page structure to it.
   */
  headingLevel?: 2 | 3 | 4;
}

/**
 * The card.
 *
 * One object used by the product grid, the looks rail and the brand list, because they are
 * the same thing with different labels — and three near-identical cards is how three
 * different hover behaviours end up on one page.
 *
 * The whole card is clickable through a stretched pseudo-element on the link, so the target
 * is the card while the accessible name stays the title. Anything interactive in the footer
 * is lifted above it.
 */
export function Card({
  to,
  title,
  brand,
  meta,
  image,
  imageAlt,
  ratio = "portrait",
  fit = "contain",
  slot,
  note,
  footer,
  testId,
  headingLevel = 3,
}: CardProps) {
  const Heading = `h${headingLevel}` as ElementType;

  return (
    <article className={styles.card} data-testid={testId}>
      <div className={styles.media}>
        <Media src={image} alt={imageAlt} ratio={ratio} slot={slot} fit={fit} note={note} zoom />
      </div>

      <div className={styles.body}>
        {brand ? <span className={styles.brandName}>{brand}</span> : null}
        <Heading className={styles.title}>
          <Link to={to} className={styles.link}>
            {title}
          </Link>
        </Heading>
        {meta ? <p className={styles.meta}>{meta}</p> : null}
      </div>

      {footer ? <div className={styles.foot}>{footer}</div> : null}
    </article>
  );
}

/**
 * An occasion tile.
 *
 * A link rather than a button: it navigates to a styling context, and the browser's own
 * link affordances (open in a new tab, copy the address) are worth keeping.
 */
export function OccasionCard({
  to,
  name,
  hint,
  className,
}: {
  to: string;
  name: string;
  hint: string;
  className?: string;
}) {
  return (
    <Link to={to} className={cx(styles.occasion, className)} data-testid="occasion-card">
      <span className={styles.occasionName}>{name}</span>
      <span className={styles.occasionHint}>{hint}</span>
    </Link>
  );
}
