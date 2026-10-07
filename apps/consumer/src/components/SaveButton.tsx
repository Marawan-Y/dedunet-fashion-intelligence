import { useNavigate } from "react-router-dom";
import type { SaveKind } from "../api/types";
import { useSaved } from "../features/saved/SavedContext";
import { saveErrorMessage } from "../features/saved/savedState";
import styles from "./SaveButton.module.css";

/* THE save control. One implementation, used everywhere.
 *
 * The alternative is three heart icons that drift: one that forgets the accessible name,
 * one that forgets the loading state, one that shows "saved" after a failed request.
 *
 * ACCESSIBILITY IS NOT OPTIONAL HERE. An icon-only button with no accessible name is a
 * button a screen reader announces as "button" — the control is present and unusable. The
 * name says what it does AND to what: "Save The Source Tee", not "Save". `aria-pressed`
 * carries the state, so the toggle is announced rather than inferred from a colour change.
 *
 * SIGNED OUT, IT DOES NOT PRETEND. There is no local list to write to, so the control sends
 * the visitor to sign in with a return path. Storing a "saved" item in the browser and
 * calling it saved is the fake persistence this phase exists to replace.
 */

export interface SaveButtonProps {
  kind: SaveKind;
  slug: string;
  /** The thing's name, for the accessible label. Never omit it. */
  name: string;
  /** `icon` for a card corner, `inline` for a row of controls on a detail page. */
  variant?: "icon" | "inline";
  testId?: string;
}

export function SaveButton({
  kind,
  slug,
  name,
  variant = "icon",
  testId = "save-button",
}: SaveButtonProps) {
  const { isSaved, statusOf, errorOf, signedIn, toggle } = useSaved();
  const navigate = useNavigate();

  const saved = isSaved(kind, slug);
  const status = statusOf(kind, slug);
  const error = errorOf(kind, slug);
  const busy = status === "saving" || status === "unsaving";

  /* The label is the state, not the action-in-progress. A button that reads "Saving…" while
     `aria-pressed` still says false gives a screen reader two answers. */
  const label = saved ? `Remove ${name} from saved items` : `Save ${name}`;

  async function onClick() {
    if (!signedIn) {
      /* Honest sign-in-required flow. `next` brings them back to where they were, so the
         save is one tap away rather than a navigation puzzle. Resume-after-login is NOT
         implemented in this phase and is not implied: the visitor returns and saves. */
      navigate(`/account?next=${encodeURIComponent(window.location.pathname)}`);
      return;
    }
    await toggle(kind, slug);
  }

  const message = saveErrorMessage(error);

  return (
    <span className={variant === "icon" ? styles.iconWrap : styles.inlineWrap}>
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        aria-pressed={saved}
        aria-label={label}
        title={label}
        data-testid={testId}
        data-saved={saved ? "true" : "false"}
        data-status={status}
        className={[
          variant === "icon" ? styles.icon : styles.inline,
          saved ? styles.isSaved : "",
          busy ? styles.isBusy : "",
          status === "error" ? styles.isError : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <Bookmark filled={saved} />
        {variant === "inline" ? (
          <span className={styles.text}>{saved ? "Saved" : "Save"}</span>
        ) : null}
      </button>

      {/* The failure has to be readable, and it has to be announced. `role="status"` rather
          than an alert: a failed save is worth saying once, not interrupting for. */}
      {message ? (
        <span role="status" className={styles.error} data-testid="save-error">
          {message}
        </span>
      ) : null}
    </span>
  );
}

/** A bookmark rather than a heart: this is "keep for later", not "love". */
function Bookmark({ filled }: { filled: boolean }) {
  return (
    <svg
      className={styles.glyph}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M6.5 3.5h11a1 1 0 0 1 1 1v15.2a.6.6 0 0 1-.93.5L12 16.6l-5.57 3.6a.6.6 0 0 1-.93-.5V4.5a1 1 0 0 1 1-1z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}
