import type { ReactNode } from "react";
import { ApiError, NetworkError } from "../api/types";
import { Button, ButtonLink } from "./Button";
import { Grid, cx } from "./primitives";
import styles from "./States.module.css";

/* Section 23. Every surface supports loading, success, empty, offline, validation error,
 * 401, 403, 404, 409, 429 and 5xx — and none of them is a blank page, a raw exception or
 * an undefined.
 *
 * The copy is deliberately specific per status. "Something went wrong" is the same
 * sentence for a rate limit, an expired session and a server fault, and it tells a
 * customer nothing about whether waiting, signing in or giving up is the right response.
 */

interface StatusCopy {
  title: string;
  body: string;
  tone: "error" | "warning" | "info";
  /** Retrying a 403 just repeats the refusal. */
  retryable: boolean;
}

function copyFor(error: unknown): StatusCopy {
  if (error instanceof NetworkError) {
    return {
      title: "Cannot reach DEDUNET",
      body: "Check your connection and try again.",
      tone: "error",
      retryable: true,
    };
  }

  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return {
          title: "Please sign in again",
          body: "Your session has ended. Sign in to pick up where you left off.",
          tone: "info",
          retryable: false,
        };
      case 403:
        return {
          title: "Not available to this account",
          body: "You are signed in, but this is not something your account can reach.",
          tone: "warning",
          retryable: false,
        };
      case 404:
        return {
          title: "Not found",
          body: "This does not exist, or is no longer published.",
          tone: "info",
          retryable: false,
        };
      case 409:
        return {
          title: "That changed while you were deciding",
          body: "Something moved underneath this request. Reload to see the current state.",
          tone: "warning",
          retryable: true,
        };
      case 429:
        return {
          title: "Too many requests",
          body: "You have been rate limited. Wait a moment and try again.",
          tone: "warning",
          retryable: true,
        };
      default:
        if (error.status >= 500) {
          return {
            title: "DEDUNET could not answer",
            body: "The problem is on our side, not yours. Try again in a moment.",
            tone: "error",
            retryable: true,
          };
        }
        return {
          title: "That request was refused",
          body: "The request did not go through.",
          tone: "error",
          retryable: true,
        };
    }
  }

  return {
    title: "Something failed",
    body: "This did not load. Trying again may work.",
    tone: "error",
    retryable: true,
  };
}

/** The raw failure text, so a report is actionable rather than a description of a mood. */
function detailOf(error: unknown): string {
  if (error instanceof ApiError || error instanceof NetworkError) return error.message;
  if (error instanceof Error) return error.message;
  return String(error);
}

export function ErrorState({
  error,
  onRetry,
  testId = "error-state",
}: {
  error: unknown;
  onRetry?: () => void;
  testId?: string;
}) {
  const copy = copyFor(error);
  const isSession = error instanceof ApiError && error.status === 401;

  return (
    <div
      className={cx(styles.state, styles[copy.tone])}
      /* alert, not status: a failure that replaces the content the customer asked for
         should interrupt, and a polite region would let it pass unannounced. */
      role="alert"
      data-testid={testId}
    >
      <p className={styles.title}>{copy.title}</p>
      <p className={styles.body}>{copy.body}</p>
      <p className={styles.detail}>{detailOf(error)}</p>

      <div className={styles.actions}>
        {copy.retryable && onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
        {isSession ? (
          <ButtonLink to="/account" variant="primary">
            Sign in
          </ButtonLink>
        ) : null}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
  testId = "empty-state",
}: {
  title: string;
  body: string;
  action?: ReactNode;
  testId?: string;
}) {
  return (
    <div className={cx(styles.state, styles.info)} data-testid={testId}>
      <p className={styles.title}>{title}</p>
      <p className={styles.body}>{body}</p>
      {action ? <div className={styles.actions}>{action}</div> : null}
    </div>
  );
}

/**
 * A surface that is deliberately not built yet.
 *
 * Section 22 and section 47: a shell must say it is a shell. This is the component that
 * says so, rather than each unbuilt feature inventing its own way of implying it works.
 */
export function NotBuiltState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className={cx(styles.state, styles.info)} data-testid="not-built-state">
      <p className={styles.title}>{title}</p>
      <p className={styles.body}>{body}</p>
      {action ? <div className={styles.actions}>{action}</div> : null}
    </div>
  );
}

/* --------------------------------------------------------------------- skeletons */

export function SkeletonCard() {
  return (
    <div className={styles.skeletonCard} aria-hidden="true">
      <div className={cx(styles.skeleton, styles.skeletonMedia)} />
      <div className={styles.skeletonCardBody}>
        <div className={cx(styles.skeleton, styles.skeletonLineShort)} />
        <div className={cx(styles.skeleton, styles.skeletonLine)} />
      </div>
    </div>
  );
}

/**
 * A loading grid.
 *
 * Sized to what is coming so the layout does not jump when it arrives — the CLS budget in
 * section 28 is mostly won or lost here. The status role and label are what make the wait
 * perceivable to a screen reader, for which a shimmering rectangle is nothing at all.
 */
export function SkeletonGrid({ count = 6, label = "Loading" }: { count?: number; label?: string }) {
  /* aria-busy, NOT a live region.
   *
   * A page with two loading grids used to declare two live regions on top of the app's
   * one, and several regions competing is how a status message ends up announced by none
   * of them. aria-busy is the correct pattern for "this region is being populated": it
   * describes the region rather than shouting about it, and the app's single #ds-live
   * region stays the one place anything is announced from. */
  return (
    <div role="status" aria-busy="true" aria-label={label} data-testid="loading-state">
      <Grid>
        {Array.from({ length: count }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </Grid>
    </div>
  );
}
