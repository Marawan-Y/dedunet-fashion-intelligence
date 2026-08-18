/**
 * Persistence and migration of the saved API endpoint.
 *
 * `api-base-lifecycle.test.ts` covers the PRECEDENCE rule as a pure function. This covers
 * the record on disk: that a v1 value written by an older install is retired rather than
 * trusted, that a current record round-trips, and -- the part with the most room to go
 * quietly wrong -- that none of it touches the session or the cart.
 *
 * Native Android acceptance had exactly one workaround for the stale override: clearing the
 * app's storage from Android settings, which also destroyed the signed-in session and the
 * basket. A migration that did the same thing would be that workaround wearing a nicer hat.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

import { API_BASE_OVERRIDE_VERSION } from "../config";
import {
  clearApiBaseOverride,
  loadApiBaseOverride,
  loadCartToken,
  loadSession,
  saveApiBaseOverride,
  saveCartToken,
  saveSession,
} from "../storage";

const KEY_LEGACY = "dedunet.apiBase.v1";
const KEY_CURRENT = "dedunet.apiBase.v2";

const NEW_BUILD = "http://10.0.2.2:18080";
const OLD_BUILD = "http://10.0.2.2:18000";

const SESSION = { accessToken: "tok-not-a-credential", role: "customer", email: "a@b.example" };

beforeEach(async () => {
  await AsyncStorage.clear();
  jest.restoreAllMocks();
});

describe("the current record", () => {
  it("round-trips with the build it was saved against", async () => {
    await saveApiBaseOverride(NEW_BUILD, NEW_BUILD);

    await expect(loadApiBaseOverride()).resolves.toEqual({
      version: API_BASE_OVERRIDE_VERSION,
      value: NEW_BUILD,
      buildBase: NEW_BUILD,
    });
  });

  it("returns null when nothing has been saved", async () => {
    await expect(loadApiBaseOverride()).resolves.toBeNull();
  });

  it("is forgotten by a reset", async () => {
    await saveApiBaseOverride(NEW_BUILD, NEW_BUILD);
    await clearApiBaseOverride();

    await expect(loadApiBaseOverride()).resolves.toBeNull();
  });
});

describe("retiring a v1 record", () => {
  it("reports it as legacy rather than as a usable override", async () => {
    // What an older install left behind: a bare string with no provenance.
    await AsyncStorage.setItem(KEY_LEGACY, OLD_BUILD);

    const loaded = await loadApiBaseOverride();

    expect(loaded).not.toBeNull();
    expect(loaded?.version).toBe(1);
    expect(loaded?.buildBase).toBe("");
  });

  it("removes the legacy key so the same question is not asked every launch", async () => {
    await AsyncStorage.setItem(KEY_LEGACY, OLD_BUILD);

    await loadApiBaseOverride();

    await expect(AsyncStorage.getItem(KEY_LEGACY)).resolves.toBeNull();
    await expect(loadApiBaseOverride()).resolves.toBeNull();
  });

  it("prefers a current record and leaves the legacy one alone", async () => {
    // Both present: the v2 record is authoritative and the v1 read never happens.
    await AsyncStorage.setItem(KEY_LEGACY, OLD_BUILD);
    await saveApiBaseOverride(NEW_BUILD, NEW_BUILD);

    const loaded = await loadApiBaseOverride();

    expect(loaded?.value).toBe(NEW_BUILD);
    expect(loaded?.version).toBe(API_BASE_OVERRIDE_VERSION);
  });
});

describe("unreadable records", () => {
  it.each([
    ["not json", "{{{"],
    ["a json array", "[1,2,3]"],
    ["a json string", '"http://10.0.2.2:18080"'],
    ["an object missing fields", '{"value":"http://10.0.2.2:18080"}'],
    ["an object with wrong types", '{"version":"2","value":1,"buildBase":null}'],
  ])("surfaces %s as a discardable record rather than as no override", async (_label, raw) => {
    await AsyncStorage.setItem(KEY_CURRENT, raw);

    const loaded = await loadApiBaseOverride();

    // Not null: silently treating a corrupt store as "nothing saved" would hide it. The
    // resolver refuses this shape and the caller discards it visibly.
    expect(loaded).not.toBeNull();
    expect(loaded?.value).toBe("");
  });
});

describe("the migration touches nothing else", () => {
  it("leaves the session and cart intact when a legacy override is retired", async () => {
    await saveSession(SESSION);
    await saveCartToken("cart-token-not-a-credential");
    await AsyncStorage.setItem(KEY_LEGACY, OLD_BUILD);

    await loadApiBaseOverride();

    await expect(loadSession()).resolves.toEqual(SESSION);
    await expect(loadCartToken()).resolves.toBe("cart-token-not-a-credential");
  });

  it("leaves the session and cart intact when the override is reset", async () => {
    // The whole point of the reset button: the old cure was clearing app storage, which
    // signed the operator out and emptied their basket as collateral.
    await saveSession(SESSION);
    await saveCartToken("cart-token-not-a-credential");
    await saveApiBaseOverride(OLD_BUILD, OLD_BUILD);

    await clearApiBaseOverride();

    await expect(loadApiBaseOverride()).resolves.toBeNull();
    await expect(loadSession()).resolves.toEqual(SESSION);
    await expect(loadCartToken()).resolves.toBe("cart-token-not-a-credential");
  });

  it("removes only the two API keys", async () => {
    await saveSession(SESSION);
    await saveCartToken("cart-token-not-a-credential");
    await AsyncStorage.setItem(KEY_LEGACY, OLD_BUILD);
    await saveApiBaseOverride(NEW_BUILD, NEW_BUILD);

    await clearApiBaseOverride();

    const keys = await AsyncStorage.getAllKeys();
    expect(keys).not.toContain(KEY_CURRENT);
    expect(keys).not.toContain(KEY_LEGACY);
    expect(keys).toContain("dedunet.session.v1");
    expect(keys).toContain("dedunet.cart.v1");
  });
});

describe("storage being unavailable", () => {
  it("degrades to no override rather than crashing the boot path", async () => {
    jest.spyOn(AsyncStorage, "getItem").mockRejectedValue(new Error("storage gone"));

    await expect(loadApiBaseOverride()).resolves.toBeNull();
  });
});
