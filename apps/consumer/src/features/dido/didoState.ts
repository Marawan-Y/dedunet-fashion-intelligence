import type { BriefEntry, DidoSessionPayload, StylingBrief } from "../../api/types";

/* The Dido page's decisions, as pure functions.
 *
 * Same reasoning as `savedState.ts` and `styleDraft.ts`: what a status means, how a brief
 * field is worded for a human, and which error message a failure deserves are decisions,
 * and decisions should be testable without a DOM.
 *
 * NOTHING HERE INVENTS CONTENT. Every label is derived from a value the server sent. The
 * page cannot say "I'll keep it under €200" unless the brief holds 20000 minor units,
 * because the sentence is assembled from the field.
 */

/** What the conversation surface is doing right now. */
export type DidoUiState =
  | "loading"
  | "signed-out"
  | "welcome"
  | "listening"
  | "interpreting"
  | "asking"
  | "conflict"
  | "brief-ready"
  | "completed"
  | "degraded"
  | "rate-limited"
  | "error";

/**
 * Money by integer arithmetic, never division.
 *
 * `minor / 100` cannot represent most cent values exactly, so a budget shown back to the
 * customer could differ by a cent from what they typed. Slicing digits cannot.
 */
export function formatMinorUnits(minor: number, currency = "EUR"): string {
  if (!Number.isInteger(minor)) return `${minor} ${currency}`;
  const symbol = currency === "EUR" ? "€" : `${currency} `;
  const sign = minor < 0 ? "-" : "";
  const digits = String(Math.abs(minor)).padStart(3, "0");
  const major = digits.slice(0, digits.length - 2);
  const cents = digits.slice(digits.length - 2);
  return `${sign}${symbol}${major}.${cents}`;
}

const FIELD_LABELS: Record<string, string> = {
  occasion: "Occasion",
  dress_code: "Dress level",
  setting: "Setting",
  temperature: "Weather, as you described it",
  colour_preferences: "Colours you want",
  colour_avoidances: "Colours to avoid",
  material_preferences: "Materials you want",
  material_avoidances: "Materials to avoid",
  brand_preferences: "Brands you follow",
  brand_avoidances: "Brands to exclude",
  fit_preferences: "Fit",
  requested_categories: "Pieces you mentioned",
  budget_total: "Budget for the whole look",
  budget_per_piece: "Budget per piece",
  budget_skipped: "Budget",
};

export function labelFor(field: string): string {
  return FIELD_LABELS[field] ?? field.replace(/_/g, " ");
}

/** A brief value as a person would read it. Money formatted; lists joined; nothing invented. */
export function valueFor(entry: BriefEntry, currency = "EUR"): string {
  const { field, value } = entry;
  if (field === "budget_skipped") return value ? "You would rather not say" : "";
  if ((field === "budget_total" || field === "budget_per_piece") && typeof value === "number") {
    return formatMinorUnits(value, currency);
  }
  if (Array.isArray(value)) {
    return value.map((v) => String(v).replace(/-/g, " ")).join(", ");
  }
  return String(value).replace(/-/g, " ");
}

/** True when the brief holds nothing at all — used to tell "new" from "in progress". */
export function isBriefEmpty(brief: StylingBrief): boolean {
  return (
    brief.from_session.length === 0 &&
    brief.from_style_dna.length === 0 &&
    brief.derived_from_your_words.length === 0
  );
}

export function countedEntries(brief: StylingBrief): number {
  return (
    brief.from_session.length +
    brief.from_style_dna.length +
    brief.derived_from_your_words.length
  );
}

/**
 * Which UI state a server response implies.
 *
 * Derived from the payload rather than tracked separately, so the screen cannot disagree
 * with the session. A conflict outranks everything else, because collecting more
 * constraints on top of two that contradict produces a longer brief that is still wrong.
 */
export function stateFor(
  session: DidoSessionPayload | null,
  options: { pending?: boolean; signedIn: boolean } = { signedIn: true },
): DidoUiState {
  if (!options.signedIn) return "signed-out";
  if (!session) return "welcome";
  if (options.pending) return "interpreting";
  if (session.status === "BRIEF_READY") return "completed";
  if (session.brief.contradictions.length > 0) return "conflict";
  if (session.interpretation?.degraded) return "degraded";
  if (session.next_question) return "asking";
  if (session.brief.ready) return "brief-ready";
  return "listening";
}

/** Plain language. Never a status code, never a provider name, never a server trace. */
export function didoErrorMessage(error: unknown): string {
  const status = (error as { status?: number } | null)?.status;
  if (status === 401) return "Your session has expired. Sign in again to carry on.";
  if (status === 409) return "This conversation moved on somewhere else. Reload to catch up.";
  if (status === 429) return "That was a lot at once. Give it a moment and try again.";
  if (status === 404) return "That styling session is no longer there. Start a new one.";
  if (status === 400) {
    const message = (error as { message?: string }).message;
    return message ? `That could not be sent: ${message}` : "That could not be sent.";
  }
  if (typeof status === "number" && status >= 500) {
    return "DEDUNET could not reach Dido. Try again shortly.";
  }
  return "DEDUNET could not reach the server. Check your connection and try again.";
}

/**
 * What to say when the interpreter could not read a message.
 *
 * Deliberately NOT an apology that hides the fact. The customer is told the message was
 * not understood and given the controlled choices the client already holds — inventing a
 * plausible interpretation would be the single most damaging thing this surface could do.
 */
export function degradedNotice(reason: string): string {
  if (reason === "rate_limited") {
    return "Dido is busy just now. Pick from the options below, or try again in a moment.";
  }
  return "I could not read that reliably. Pick one of the options below and we will carry on.";
}

/** A new idempotency key per submission. A retry reuses it; a new message gets a new one. */
export function newMessageId(): string {
  return `m-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
