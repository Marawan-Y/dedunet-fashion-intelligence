import type { SaveKind, SavedState } from "../../api/types";

/* The pure decisions behind the saved context, extracted so they can be tested without a
 * browser and so there is exactly one implementation of each.
 *
 * `applyToggle` returns a NEW state and never mutates its argument. That is not style: the
 * optimistic update keeps the previous object to restore on failure, and a mutating
 * implementation would have already destroyed it.
 */

export type SaveStatus = "idle" | "saving" | "unsaving" | "error";

/** Add or remove a slug for one kind, leaving the other two untouched. */
export function applyToggle(state: SavedState, kind: SaveKind, slug: string): SavedState {
  const current = state[kind];
  const saved = current.includes(slug);
  return {
    ...state,
    [kind]: saved ? current.filter((s) => s !== slug) : [...current, slug],
  };
}

export function nextStatus(wasSaved: boolean): SaveStatus {
  return wasSaved ? "unsaving" : "saving";
}

/** What to tell the customer. Each status gets the remedy that actually applies to it. */
export function saveErrorMessage(error: unknown): string {
  if (!error) return "";
  const status = (error as { status?: number }).status;
  if (typeof status === "number") {
    if (status === 401) return "Sign in to save.";
    if (status === 404) return "No longer available.";
    if (status === 429) return "Too many changes — try again in a moment.";
    if (status >= 500) return "Could not save. Try again.";
    return "Could not save.";
  }
  /* No status means no response: a transport failure, and offline is the common case.
     Reporting a server error here would send someone to the wrong remedy. */
  return "You appear to be offline.";
}
