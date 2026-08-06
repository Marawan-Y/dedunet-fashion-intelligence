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

const KEY_SESSION = "dedunet.session.v1";
const KEY_CART = "dedunet.cart.v1";
const KEY_API_BASE = "dedunet.apiBase.v1";

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

export async function loadApiBase(): Promise<string | null> {
  const value = await readString(KEY_API_BASE);
  return value === null || value === "" ? null : value;
}

export async function saveApiBase(value: string): Promise<void> {
  await writeString(KEY_API_BASE, value);
}

export async function clearApiBase(): Promise<void> {
  await remove(KEY_API_BASE);
}
