/**
 * Runtime API configuration.
 *
 * The base URL is resolved at runtime, in this order:
 *   1. a value the operator saved in the app (Settings screen),
 *   2. `EXPO_PUBLIC_API_BASE` baked in at build time,
 *   3. a platform-appropriate default.
 *
 * The default differs per platform and that is not incidental: an Android emulator reaches
 * the host machine at 10.0.2.2, never at 127.0.0.1, which resolves to the emulator itself.
 * A single hard-coded default is the most common reason a working API looks unreachable
 * from a device.
 */

import { Platform } from "react-native";

export const API_TIMEOUT_MS = 10_000;

/** Development API port used by `docker-compose.yml`. Staging is 18080. */
const DEV_API_PORT = 18000;

function platformDefault(): string {
  if (Platform.OS === "android") return `http://10.0.2.2:${DEV_API_PORT}`;
  // iOS simulator and web both share the host's loopback.
  return `http://127.0.0.1:${DEV_API_PORT}`;
}

/** Compile-time override. `EXPO_PUBLIC_*` is inlined by Metro. */
export const BUILD_TIME_API_BASE: string = process.env.EXPO_PUBLIC_API_BASE ?? "";

export function defaultApiBase(): string {
  return BUILD_TIME_API_BASE.trim() !== "" ? BUILD_TIME_API_BASE.trim() : platformDefault();
}

/**
 * Normalise an operator-entered base URL.
 *
 * Returns `null` when the value is unusable, so the settings screen can refuse it rather
 * than letting every later request fail with an opaque network error.
 */
export function normaliseApiBase(value: string): string | null {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (trimmed === "") return null;
  if (!/^https?:\/\//i.test(trimmed)) return null;
  try {
    // eslint-disable-next-line no-new
    new URL(trimmed);
  } catch {
    return null;
  }
  return trimmed;
}
