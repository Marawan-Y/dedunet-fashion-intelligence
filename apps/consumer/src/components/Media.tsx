import { useCallback, useState } from "react";
import { mediaUrl } from "../api/client";
import { cx } from "./primitives";
import styles from "./Media.module.css";

export type MediaRatio = "portrait" | "editorial" | "hero" | "square";

const RATIO_VAR: Record<MediaRatio, string> = {
  portrait: "var(--ds-ratio-portrait)",
  editorial: "var(--ds-ratio-editorial)",
  hero: "var(--ds-ratio-hero)",
  square: "var(--ds-ratio-square)",
};

export interface MediaProps {
  /** Server-relative path or absolute URL. Empty or missing renders the placeholder. */
  src?: string | null;
  /** Required, and not optional-with-a-default: an unlabelled image is unusable to a
   *  screen reader, and a default would let one ship. Pass "" only for pure decoration. */
  alt: string;
  ratio?: MediaRatio;
  /** Identifies the slot for the rendering regression suite. */
  slot: string;
  /** contain for line-drawn concept artwork, cover for photography. */
  fit?: "cover" | "contain";
  /** Above the fold. Everything else stays lazy. */
  priority?: boolean;
  zoom?: boolean;
  /** Sits over the foot of the image, e.g. the concept-artwork note. */
  note?: string;
  className?: string;
}

/**
 * An image well that is never empty.
 *
 * Three outcomes, and all three are visible:
 *   - a src that loads          the image
 *   - no src at all             a labelled placeholder
 *   - a src that fails to load  the same labelled placeholder, via onError
 *
 * The third is the one that matters most. An `img` whose request 404s renders as a broken
 * icon or as nothing at all depending on the browser, and "nothing at all" is precisely the
 * empty rectangle this component exists to make impossible.
 */
export function Media({
  src,
  alt,
  ratio = "portrait",
  slot,
  fit = "cover",
  priority = false,
  zoom = false,
  note,
  className,
}: MediaProps) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  /* Catch an image that finished loading before React attached the handler.
   *
   * The fade-in starts at opacity 0 and only `onLoad` clears it. A cached image can
   * complete between the element being created and the listener being attached, in which
   * case onLoad never fires and the image stays invisible forever — an empty image well,
   * which is the exact defect this component exists to prevent, reintroduced by the
   * animation meant to polish it.
   *
   * The ref callback reads `complete` at attach time, which is the one moment that
   * settles it either way. */
  const attach = useCallback((node: HTMLImageElement | null) => {
    if (!node) return;
    if (node.complete) {
      if (node.naturalWidth > 0) setLoaded(true);
      else setFailed(true);
    }
  }, []);

  const resolved = src ? mediaUrl(src) : "";
  const showPlaceholder = !resolved || failed;

  return (
    <div
      className={cx(styles.slot, className)}
      style={{ ["--slot-ratio" as string]: RATIO_VAR[ratio] }}
      data-media-slot={slot}
      data-media-placeholder={showPlaceholder ? "true" : undefined}
    >
      {resolved && !failed ? (
        <img
          className={cx(
            styles.image,
            loaded && styles.loaded,
            fit === "contain" && styles.contain,
            zoom && styles.zoom,
          )}
          ref={attach}
          src={resolved}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          decoding={priority ? "sync" : "async"}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : null}

      {showPlaceholder ? <MediaPlaceholder label={alt} /> : null}

      {note && !showPlaceholder ? <p className={styles.note}>{note}</p> : null}
    </div>
  );
}

/**
 * The placeholder.
 *
 * `aria-hidden` on the mark, and the text says what is missing rather than decorating the
 * gap. Section 47: nothing here may pretend to be content that does not exist.
 */
function MediaPlaceholder({ label }: { label: string }) {
  return (
    <div className={styles.placeholder}>
      <svg
        className={styles.placeholderMark}
        viewBox="0 0 48 48"
        width="32"
        height="32"
        aria-hidden="true"
        focusable="false"
      >
        {/* Two vertical rules and a horizontal passage — the brand's own line language,
            reduced to the smallest mark that still reads as DEDUNET rather than as a
            generic broken-image glyph. */}
        <path
          d="M12 6v36M36 6v36M4 24h40"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
      <span className={styles.placeholderText}>Image not available</span>
      <span className="sr-only">{label}</span>
    </div>
  );
}
