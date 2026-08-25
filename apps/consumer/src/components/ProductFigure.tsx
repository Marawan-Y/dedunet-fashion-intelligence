import { useCallback, useState } from "react";
import { mediaUrl } from "../api/client";
import { cx } from "./primitives";
import styles from "./ProductFigure.module.css";

export interface ProductFigureProps {
  src?: string | null;
  /** Required. An unlabelled image is unusable to a screen reader and a default would let
   *  one ship. Pass "" only when the figure is genuinely decorative. */
  alt: string;
  /** Identifies the slot for the rendering regression suite. */
  slot: string;
  /** CSS aspect-ratio for the plate. Portrait by default: garments are taller than wide. */
  ratio?: string;
  /** Overrides the crop for artwork composed differently from the product plates. */
  zoom?: number;
  focus?: string;
  /** A lookbook annotation over the plate, e.g. "Preview". */
  mark?: string;
  priority?: boolean;
  className?: string;
}

/**
 * A garment plate.
 *
 * Distinct from `Media`, which frames an editorial composition whole. This one CROPS into
 * its subject, because the delivered product artwork carries a baked-in caption in its
 * lower quarter that duplicates what the card already prints — and showing it left the
 * garment small in a large pale field.
 *
 * Like `Media`, it is never empty: a missing or failed source renders a composed fallback
 * that names its subject, not a blank rectangle.
 */
export function ProductFigure({
  src,
  alt,
  slot,
  ratio = "3 / 4",
  zoom,
  focus,
  mark,
  priority = false,
  className,
}: ProductFigureProps) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  /* A cached image can complete before React attaches onLoad, in which case the fade-in
     never fires and the plate stays blank — the very defect this component exists to
     prevent, reintroduced by the polish. The ref settles it at attach time. */
  const attach = useCallback((node: HTMLImageElement | null) => {
    if (!node) return;
    if (node.complete) {
      if (node.naturalWidth > 0) setLoaded(true);
      else setFailed(true);
    }
  }, []);

  const resolved = src ? mediaUrl(src) : "";
  const showFallback = !resolved || failed;

  const style: Record<string, string> = { ["--figure-ratio"]: ratio };
  if (zoom !== undefined) style["--figure-zoom"] = String(zoom);
  if (focus !== undefined) style["--figure-focus"] = focus;

  return (
    <div
      className={cx(styles.figure, className)}
      style={style}
      data-media-slot={slot}
      data-media-placeholder={showFallback ? "true" : undefined}
    >
      {resolved && !failed ? (
        <img
          ref={attach}
          className={cx(styles.image, loaded && styles.loaded)}
          src={resolved}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          decoding={priority ? "sync" : "async"}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : null}

      {showFallback ? (
        <div className={styles.fallback}>
          <div className={styles.fallbackInner}>
            <span className={styles.fallbackRule} aria-hidden="true" />
            <span className={styles.fallbackText}>Imagery to come</span>
            <span className="sr-only">{alt}</span>
          </div>
        </div>
      ) : null}

      {mark ? (
        <span className={styles.mark}>
          <span className={styles.markDot} aria-hidden="true" />
          {mark}
        </span>
      ) : null}
    </div>
  );
}
