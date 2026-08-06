/**
 * Session and cart-token persistence.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

import {
  clearCartToken,
  clearSession,
  loadCartToken,
  loadSession,
  saveCartToken,
  saveSession,
} from "../storage";

beforeEach(async () => {
  await AsyncStorage.clear();
  jest.restoreAllMocks();
});

describe("session persistence", () => {
  it("round-trips a session", async () => {
    await saveSession({ accessToken: "tok", role: "customer", email: "a@b.example" });
    await expect(loadSession()).resolves.toEqual({
      accessToken: "tok",
      role: "customer",
      email: "a@b.example",
    });
  });

  it("returns null when nothing is stored", async () => {
    await expect(loadSession()).resolves.toBeNull();
  });

  it("clears the session on sign-out", async () => {
    await saveSession({ accessToken: "tok", role: "customer", email: "a@b.example" });
    await clearSession();
    await expect(loadSession()).resolves.toBeNull();
  });

  it("discards a corrupt record instead of crashing the boot path", async () => {
    await AsyncStorage.setItem("dedunet.session.v1", "{not json");
    await expect(loadSession()).resolves.toBeNull();
  });

  it("discards a record missing the access token", async () => {
    await AsyncStorage.setItem("dedunet.session.v1", JSON.stringify({ role: "customer", email: "a@b" }));
    await expect(loadSession()).resolves.toBeNull();
  });

  it("degrades to signed-out when storage itself throws", async () => {
    // Swapped and restored by hand rather than with jest.spyOn.
    //
    // Two false passes came out of this one test. First, a leaked spy left getItem
    // rejecting for the rest of the file, so every later assertion expecting `null`
    // passed because the store was BROKEN, not because it was empty. Then mockRestore()
    // left getItem as a bare jest.fn() returning undefined -- the async-storage mock's
    // function is not a plain method, so restoring the spy did not restore its behaviour.
    // Direct assignment is the only form that actually puts the mock back.
    const storage = AsyncStorage as unknown as { getItem: unknown };
    const original = storage.getItem;
    storage.getItem = jest.fn().mockRejectedValue(new Error("unavailable"));
    try {
      await expect(loadSession()).resolves.toBeNull();
    } finally {
      storage.getItem = original;
    }
    // Prove the restore worked; otherwise this test silently poisons the rest of the file.
    await AsyncStorage.setItem("probe", "ok");
    await expect(AsyncStorage.getItem("probe")).resolves.toBe("ok");
  });
});

describe("cart-token persistence", () => {
  it("round-trips a cart token", async () => {
    await saveCartToken("cart-abc");
    await expect(loadCartToken()).resolves.toBe("cart-abc");
  });

  it("survives sign-out, because the bag belongs to the device", async () => {
    await saveSession({ accessToken: "tok", role: "customer", email: "a@b.example" });
    await saveCartToken("cart-abc");

    await clearSession();

    await expect(loadSession()).resolves.toBeNull();
    await expect(loadCartToken()).resolves.toBe("cart-abc");
  });

  it("ignores an empty token rather than storing one", async () => {
    await saveCartToken("");
    await expect(loadCartToken()).resolves.toBeNull();
  });

  it("clears on demand", async () => {
    await saveCartToken("cart-abc");
    await clearCartToken();
    await expect(loadCartToken()).resolves.toBeNull();
  });
});
