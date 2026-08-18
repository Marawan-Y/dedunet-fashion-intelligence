/**
 * Persistence for the session token, the cart token and the API base URL.
 *
 * AsyncStorage is unencrypted. The session token is HMAC-signed and not encrypted
 * (`docs/KNOWN_LIMITATIONS.md` §5) and there is no revocation list, so a token lifted from
 * device storage is valid until it expires. That is a recorded limitation of the platform,
 * not something this screen layer can fix; a real deployment wants `expo-secure-store`.
 * It is called out here so the next reader does not assume this is secure storage.
 *
 * Every function fails soft. Storage being unavailable must degrade the app to "signed
 * out", never crash it on boot.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

import { API_BASE_OVERRIDE_VERSION, type ApiBaseOverride } from "./config";

const KEY_SESSION = "dedunet.session.v1";
const KEY_CART = "dedunet.cart.v1";
/* v1 held a bare URL string with no record of the build it was saved against. It is read
   once, only to delete it -- see `loadApiBaseOverride`. */
const KEY_API_BASE_LEGACY = "dedunet.apiBase.v1";
const KEY_API_BASE = "dedunet.apiBase.v2";

export type StoredSession = {
  accessToken: string;
  role: string;
  email: string;
};

async function readString(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(key);
  } catch {
    return null;
  }
}

async function writeString(key: string, value: string): Promise<void> {
  try {
    await AsyncStorage.setItem(key, value);
  } catch {
    /* storage unavailable -- state stays in memory for this run */
  }
}

async function remove(key: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(key);
  } catch {
    /* nothing to do */
  }
}

// ------------------------------------------------------------------------------ session

export async function loadSession(): Promise<StoredSession | null> {
  const raw = await readString(KEY_SESSION);
  if (raw === null) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { accessToken, role, email } = parsed as Partial<StoredSession>;
    if (typeof accessToken !== "string" || accessToken === "") return null;
    if (typeof role !== "string" || typeof email !== "string") return null;
    return { accessToken, role, email };
  } catch {
    // A corrupt record is discarded rather than crashing the boot path.
    return null;
  }
}

export async function saveSession(session: StoredSession): Promise<void> {
  await writeString(KEY_SESSION, JSON.stringify(session));
}

export async function clearSession(): Promise<void> {
  await remove(KEY_SESSION);
}

// --------------------------------------------------------------------------- cart token

/**
 * The cart token survives sign-out on purpose: the cart belongs to the device until
 * checkout associates it with a customer. Clearing it on logout would silently discard a
 * basket the shopper still has.
 */
export async function loadCartToken(): Promise<string | null> {
  const token = await readString(KEY_CART);
  return token === null || token === "" ? null : token;
}

export async function saveCartToken(token: string): Promise<void> {
  if (token === "") return;
  await writeString(KEY_CART, token);
}

export async function clearCartToken(): Promise<void> {
  await remove(KEY_CART);
}

// ----------------------------------------------------------------------------- api base

/**
 * The operator's saved endpoint, or `null`.
 *
 * Reads the current record and, separately, retires any v1 record. v1 was a bare string:
 * it cannot say which build default it was chosen against, so it cannot be shown to be
 * current, and native Android acceptance showed what happens when such a value is trusted
 * anyway -- a correct APK pinned to a dead port until app data was cleared.
 *
 * A legacy record is REPORTED as well as removed, so `resolveApiBase` can explain the
 * discard on the settings screen instead of the endpoint appearing to change by itself.
 *
 * Only this key is touched. The session and cart keys are separate records and a migration
 * of the API configuration has no business signing anyone out or emptying a basket.
 */
export async function loadApiBaseOverride(): Promise<ApiBaseOverride | null> {
  const raw = await readString(KEY_API_BASE);

  if (raw === null || raw === "") {
    const legacy = await readString(KEY_API_BASE_LEGACY);
    if (legacy === null || legacy === "") return null;
    await remove(KEY_API_BASE_LEGACY);
    // Version 1 on purpose: `resolveApiBase` refuses it and reports it as legacy.
    return { version: 1, value: legacy, buildBase: "" };
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return { version: 0, value: "", buildBase: "" };
    const { version, value, buildBase } = parsed as Partial<ApiBaseOverride>;
    if (typeof version !== "number" || typeof value !== "string" || typeof buildBase !== "string") {
      // Structurally wrong rather than absent. Returned as a malformed record so the
      // caller can discard it visibly; silently treating it as "no override" would hide a
      // corrupted store.
      return { version: API_BASE_OVERRIDE_VERSION, value: "", buildBase: "" };
    }
    return { version, value, buildBase };
  } catch {
    return { version: API_BASE_OVERRIDE_VERSION, value: "", buildBase: "" };
  }
}

/**
 * Save an override, stamped with the build default it was chosen against.
 *
 * `buildBase` is the whole point of the record. Without it a later build has no way to tell
 * an endpoint someone deliberately set for THIS build from one left behind by a previous
 * install.
 */
export async function saveApiBaseOverride(value: string, buildBase: string): Promise<void> {
  const record: ApiBaseOverride = { version: API_BASE_OVERRIDE_VERSION, value, buildBase };
  await writeString(KEY_API_BASE, JSON.stringify(record));
}

/** Forget the override and fall back to the build default. Touches no other key. */
export async function clearApiBaseOverride(): Promise<void> {
  await remove(KEY_API_BASE);
  await remove(KEY_API_BASE_LEGACY);
}
