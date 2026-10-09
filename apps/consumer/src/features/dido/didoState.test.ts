import { describe, expect, it } from "vitest";
import type { BriefEntry, DidoSessionPayload, StylingBrief } from "../../api/types";
import {
  countedEntries,
  degradedNotice,
  didoErrorMessage,
  formatMinorUnits,
  isBriefEmpty,
  labelFor,
  newMessageId,
  stateFor,
  valueFor,
} from "./didoState";

const EMPTY_BRIEF: StylingBrief = {
  from_session: [],
  from_style_dna: [],
  derived_from_your_words: [],
  unplaced: [],
  contradictions: [],
  size_context: [],
  currency: "EUR",
  still_unset: [],
  ready: false,
};

function makeSession(overrides: Partial<DidoSessionPayload> = {}): DidoSessionPayload {
  return {
    session_id: 1,
    status: "ACTIVE",
    revision: 1,
    turn_count: 1,
    personalization_used: false,
    style_profile_revision_used: null,
    brief: EMPTY_BRIEF,
    next_question: null,
    capabilities: {
      understands_constraints: true,
      uses_style_dna: false,
      recommends_products: false,
      builds_outfits: false,
    },
    created_at: "2026-10-09T00:00:00Z",
    updated_at: "2026-10-09T00:00:00Z",
    ...overrides,
  };
}

const entry = (field: string, value: unknown): BriefEntry => ({ field, value, evidence: "" });

describe("money, by integer arithmetic only", () => {
  it("formats minor units without dividing", () => {
    expect(formatMinorUnits(20000)).toBe("€200.00");
    expect(formatMinorUnits(10050)).toBe("€100.50");
    expect(formatMinorUnits(5)).toBe("€0.05");
    expect(formatMinorUnits(0)).toBe("€0.00");
  });

  it("handles the value float division gets wrong", () => {
    // 19999 / 100 * 100 is not 19999 in binary floating point.
    expect(formatMinorUnits(19999)).toBe("€199.99");
  });

  it("refuses to pretend a non-integer is money", () => {
    expect(formatMinorUnits(199.99)).toBe("199.99 EUR");
  });
});

describe("brief values are read from the brief, never invented", () => {
  it("formats a budget from its minor units", () => {
    expect(valueFor(entry("budget_total", 30000))).toBe("€300.00");
    expect(valueFor(entry("budget_per_piece", 7200))).toBe("€72.00");
  });

  it("renders a list as the words the customer used", () => {
    expect(valueFor(entry("colour_avoidances", ["black", "orange"]))).toBe("black, orange");
  });

  it("renders a slug as readable text", () => {
    expect(valueFor(entry("dress_code", "business-casual"))).toBe("business casual");
  });

  it("says plainly when a budget was declined", () => {
    expect(valueFor(entry("budget_skipped", true))).toBe("You would rather not say");
  });

  it("labels every field a brief can hold", () => {
    for (const field of [
      "occasion", "dress_code", "setting", "temperature",
      "colour_preferences", "colour_avoidances",
      "material_preferences", "material_avoidances",
      "brand_preferences", "brand_avoidances",
      "fit_preferences", "requested_categories",
      "budget_total", "budget_per_piece", "budget_skipped",
    ]) {
      expect(labelFor(field)).not.toBe(field);
    }
  });

  it("falls back readably for a field it does not know", () => {
    expect(labelFor("some_new_field")).toBe("some new field");
  });
});

describe("brief emptiness", () => {
  it("knows an untouched brief from one with content", () => {
    expect(isBriefEmpty(EMPTY_BRIEF)).toBe(true);
    expect(countedEntries(EMPTY_BRIEF)).toBe(0);

    const filled = { ...EMPTY_BRIEF, from_session: [entry("occasion", "wedding")] };
    expect(isBriefEmpty(filled)).toBe(false);
    expect(countedEntries(filled)).toBe(1);
  });

  it("counts every source group", () => {
    const brief = {
      ...EMPTY_BRIEF,
      from_session: [entry("occasion", "wedding")],
      from_style_dna: [entry("colour_preferences", ["navy"])],
      derived_from_your_words: [entry("setting", "outdoors")],
    };
    expect(countedEntries(brief)).toBe(3);
  });
});

describe("ui state is derived from the payload, so it cannot disagree with it", () => {
  it("is signed-out before anything else", () => {
    expect(stateFor(null, { signedIn: false })).toBe("signed-out");
    expect(stateFor(makeSession(), { signedIn: false })).toBe("signed-out");
  });

  it("is welcome with no session", () => {
    expect(stateFor(null, { signedIn: true })).toBe("welcome");
  });

  it("is interpreting while a request is in flight", () => {
    expect(stateFor(makeSession(), { signedIn: true, pending: true })).toBe("interpreting");
  });

  it("puts a conflict above every other state", () => {
    // Collecting more constraints on top of two that contradict produces a longer brief
    // that is still wrong, so the conflict must win even when a question is pending.
    const session = makeSession({
      brief: {
        ...EMPTY_BRIEF,
        contradictions: [{ kind: "colour_conflict", detail: "d", question: "q" }],
      },
      next_question: { key: "budget", prompt: "p", why: "w" },
    });
    expect(stateFor(session, { signedIn: true })).toBe("conflict");
  });

  it("is asking when a question is outstanding", () => {
    const session = makeSession({ next_question: { key: "occasion", prompt: "p", why: "w" } });
    expect(stateFor(session, { signedIn: true })).toBe("asking");
  });

  it("is brief-ready when nothing is missing", () => {
    const session = makeSession({ brief: { ...EMPTY_BRIEF, ready: true } });
    expect(stateFor(session, { signedIn: true })).toBe("brief-ready");
  });

  it("is completed once the brief is agreed", () => {
    expect(stateFor(makeSession({ status: "BRIEF_READY" }), { signedIn: true })).toBe("completed");
  });

  it("is degraded when the interpreter failed", () => {
    const session = makeSession({
      interpretation: { degraded: true, reason: "unavailable", ambiguous: false },
    });
    expect(stateFor(session, { signedIn: true })).toBe("degraded");
  });
});

describe("failure is reported honestly, never papered over", () => {
  it("tells the customer the message was not understood", () => {
    expect(degradedNotice("unavailable")).toContain("could not read that");
    // And offers a real way forward rather than a guess.
    expect(degradedNotice("unavailable")).toContain("options below");
  });

  it("distinguishes busy from broken", () => {
    expect(degradedNotice("rate_limited")).toContain("busy");
  });

  it("never shows a status code or a provider name", () => {
    for (const status of [400, 401, 404, 409, 429, 500, 503]) {
      const message = didoErrorMessage({ status });
      expect(message).not.toMatch(/\d{3}/);
      expect(message.toLowerCase()).not.toContain("openai");
      expect(message.toLowerCase()).not.toContain("provider");
    }
  });

  it("explains a conflict rather than restating it", () => {
    expect(didoErrorMessage({ status: 409 })).toContain("moved on somewhere else");
  });

  it("never leaks a server trace", () => {
    const message = didoErrorMessage({ status: 500, message: "Traceback (most recent call last)" });
    expect(message).not.toContain("Traceback");
  });

  it("falls back to a connection message with no status", () => {
    expect(didoErrorMessage(new Error("boom"))).toContain("connection");
  });
});

describe("message identity", () => {
  it("is unique per call, so a new message is never mistaken for a retry", () => {
    const ids = new Set(Array.from({ length: 50 }, () => newMessageId()));
    expect(ids.size).toBe(50);
  });
});
