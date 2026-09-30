import type { ElementType, ReactNode } from "react";
import { Link } from "react-router-dom";
import { mediaUrl } from "../api/client";
import { ProductFigure } from "./ProductFigure";
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
  /** CSS aspect-ratio for the plate. Portrait by default. */
  ratio?: string;
  /** Crop overrides, for artwork composed differently from the product plates. */
  zoom?: number;
  focus?: string;
  slot: string;
  /** A lookbook annotation over the plate, e.g. "Preview". */
  mark?: string;
  priority?: boolean;
  footer?: ReactNode;
  /**
   * A save control, rendered over the plate's top-right corner.
   *
   * A slot rather than a `savable` boolean: the card should not know what a saved item is,
   * and the caller already knows the slug, the kind and the name the accessible label needs.
   */
  saveControl?: ReactNode;
  testId?: string;
  /**
   * The heading level for the card title.
   *
   * Explicit, with a default of 3, because a card's correct level depends on what is above
   * it: under a section h2 it is an h3, but in a grid that follows the page h1 directly it
   * must be an h2 or the outline jumps h1 -> h3.
   */
  headingLevel?: 2 | 3 | 4;
}

/**
 * The card.
 *
 * One object used by the product grid, the looks rail and the brand list, because they are
 * the same thing with different labels — and three near-identical cards is how three
 * different hover behaviours end up on one page.
 */
export function Card({
  to,
  title,
  brand,
  meta,
  image,
  imageAlt,
  ratio,
  zoom,
  focus,
  slot,
  mark,
  priority,
  footer,
  saveControl,
  testId,
  headingLevel = 3,
}: CardProps) {
  const Heading = `h${headingLevel}` as ElementType;

  return (
    <article className={styles.card} data-testid={testId}>
      <div className={styles.media}>
        <ProductFigure
          src={image}
          alt={imageAlt}
          slot={slot}
          ratio={ratio ?? "3 / 4"}
          zoom={zoom}
          focus={focus}
          mark={mark}
          priority={priority}
        />
        {/* Over the plate, not inside the link: a save control nested in the card's anchor
            would navigate on every tap. It is a sibling for that reason. */}
        {saveControl}
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
 * An occasion plate.
 *
 * A link rather than a button: it navigates to a styling context, and the browser's own
 * link affordances are worth keeping. The artwork behind it is real DEDUNET concept media —
 * an occasion has no photography of its own, so it borrows the lifestyle plate of a piece
 * that suits it rather than inventing an image for it.
 */
export function OccasionCard({
  to,
  name,
  hint,
  image,
  cue = "Style this",
  className,
}: {
  to: string;
  name: string;
  hint: string;
  image?: string | null;
  cue?: string;
  className?: string;
}) {
  return (
    <Link to={to} className={cx(styles.occasion, className)} data-testid="occasion-card">
      {image ? (
        <img
          className={styles.occasionMedia}
          src={mediaUrl(image)}
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
        />
      ) : null}

      <span className={styles.occasionName}>{name}</span>
      <span className={styles.occasionHint}>{hint}</span>
      <span className={styles.occasionCue}>
        <span className={styles.occasionCueRule} aria-hidden="true" />
        {cue}
      </span>
    </Link>
  );
}
