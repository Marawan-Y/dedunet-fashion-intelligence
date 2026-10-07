import { describe, expect, it } from "vitest";
import { applyToggle, nextStatus, saveErrorMessage } from "./savedState";

/* The saved-set arithmetic, tested without a browser.
 *
 * The context itself is React and belongs in the Playwright suite; the decisions it makes
 * are pure and belong here. The one that matters is ROLLBACK: an optimistic update whose
 * failure path is wrong leaves a control showing "saved" for a request the server refused,
 * which is a lie with good latency.
 */

const EMPTY = { products: [], brands: [], looks: [] };

describe("applyToggle", () => {
  it("adds a slug that was not saved", () => {
    const next = applyToggle(EMPTY, "products", "the-source-tee");
    expect(next.products).toEqual(["the-source-tee"]);
    expect(next.brands).toEqual([]);
  });

  it("removes a slug that was saved", () => {
    const state = { ...EMPTY, products: ["the-source-tee", "the-passage-shirt"] };
    expect(applyToggle(state, "products", "the-source-tee").products).toEqual([
      "the-passage-shirt",
    ]);
  });

  it("never duplicates a slug, even if called twice", () => {
    /* The server is idempotent; the client must be too, or a double tap shows the item
       twice in a count derived from the set's length. */
    const once = applyToggle(EMPTY, "brands", "dedunet");
    const twice = applyToggle(once, "brands", "dedunet");
    expect(twice.brands).toEqual([]);
    const thrice = applyToggle(twice, "brands", "dedunet");
    expect(thrice.brands).toEqual(["dedunet"]);
  });

  it("does not mutate the previous state, which is what makes rollback possible", () => {
    const state = { ...EMPTY, products: ["a"] };
    const next = applyToggle(state, "products", "b");
    expect(state.products).toEqual(["a"]);
    expect(next.products).toEqual(["a", "b"]);
  });

  it("touches only the kind being toggled", () => {
    const state = { products: ["p"], brands: ["b"], looks: ["l"] };
    const next = applyToggle(state, "looks", "l2");
    expect(next.products).toEqual(["p"]);
    expect(next.brands).toEqual(["b"]);
    expect(next.looks).toEqual(["l", "l2"]);
  });
});

describe("nextStatus", () => {
  it("reports saving when adding and unsaving when removing", () => {
    expect(nextStatus(false)).toBe("saving");
    expect(nextStatus(true)).toBe("unsaving");
  });
});

describe("saveErrorMessage", () => {
  it("asks for sign-in on 401 rather than reporting a failure", () => {
    expect(saveErrorMessage({ status: 401 })).toMatch(/sign in/i);
  });

  it("says the target is gone on 404", () => {
    expect(saveErrorMessage({ status: 404 })).toMatch(/no longer available/i);
  });

  it("asks for a retry on 429 without blaming the customer", () => {
    const message = saveErrorMessage({ status: 429 });
    expect(message).toMatch(/try again/i);
    expect(message).not.toMatch(/error|fail/i);
  });

  it("reports a server failure honestly on 5xx", () => {
    expect(saveErrorMessage({ status: 500 })).toMatch(/could not save/i);
    expect(saveErrorMessage({ status: 503 })).toMatch(/could not save/i);
  });

  it("names offline as offline rather than as a server error", () => {
    /* A transport failure has no status. Telling someone the server failed when their
       connection dropped sends them to the wrong remedy. */
    expect(saveErrorMessage(new Error("network"))).toMatch(/offline/i);
  });

  it("says nothing when there is no error", () => {
    expect(saveErrorMessage(null)).toBe("");
    expect(saveErrorMessage(undefined)).toBe("");
  });

  it("never claims success for a failure", () => {
    for (const status of [401, 403, 404, 409, 429, 500, 502, 503]) {
      expect(saveErrorMessage({ status })).not.toBe("");
    }
  });
});
