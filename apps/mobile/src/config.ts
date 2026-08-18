/**
 * Runtime API configuration, and the lifecycle of an operator's saved override.
 *
 * WHY THE PRECEDENCE IS WHAT IT IS
 * --------------------------------
 * It used to be: saved override, then `EXPO_PUBLIC_API_BASE`, then a platform default --
 * with the override winning unconditionally and forever. Native Android acceptance found
 * what that costs. The preview APK correctly carried `http://10.0.2.2:18080`, the manifest
 * correctly allowed local cleartext, and emulator Chrome reached the API; the app still
 * showed "Cannot reach the store" and the backend saw no request at all, because an
 * override saved by an OLDER build still pinned it to `:18000`. Clearing app storage fixed
 * it instantly, which is the signature of state outliving the build that created it.
 *
 * So the build's own endpoint is authoritative, and an override has to earn its precedence
 * by proving it is still current. It does that by recording the build default it was saved
 * AGAINST: if the build default has since changed, the operator was configuring a different
 * build and the override is stale.
 *
 * Nothing here reaches AsyncStorage. `resolveApiBase` is a pure function of (override,
 * build default) so the policy can be tested exhaustively without a device -- which is the
 * whole reason the original defect was invisible to the suite.
 */

import { Platform } from "react-native";

export const API_TIMEOUT_MS = 10_000;

/** Development API port used by `docker-compose.yml`. Staging is 18080. */
const DEV_API_PORT = 18000;

/**
 * Current schema version of a stored override.
 *
 * v1 was a bare string with no provenance. v2 records what it was saved against, which is
 * the fact the precedence rule needs and the fact v1 cannot supply.
 */
export const API_BASE_OVERRIDE_VERSION = 2;

export type ApiBaseOverride = {
  version: number;
  /** The address the operator entered, already normalised. */
  value: string;
  /** The build default in force when they saved it. */
  buildBase: string;
};

/** Why a stored override was not applied. `null` means it was, or there was none. */
export type OverrideRejection = "legacy" | "stale" | "malformed";

export type ApiBaseSource =
  | "operator-override"
  | "build-default"
  | "development-default"
  | "unconfigured";

export type ResolvedApiBase = {
  base: string;
  source: ApiBaseSource;
  /** Set when a stored override existed and was refused; the caller discards it. */
  rejected: OverrideRejection | null;
};

/**
 * The emulator loopback, for DEVELOPMENT ONLY.
 *
 * An Android emulator reaches the host at 10.0.2.2; 127.0.0.1 resolves to the emulator
 * itself. That makes it the right default for a developer running `expo start` and the
 * wrong one for anything shipped: a release build that fell through to it would carry a
 * hidden local endpoint and fail in a way that looks like a network fault. Real builds
 * supply `EXPO_PUBLIC_API_BASE` through `eas.json`, so they never reach this.
 */
function developmentDefault(): string {
  if (Platform.OS === "android") return `http://10.0.2.2:${DEV_API_PORT}`;
  // iOS simulator and web both share the host's loopback.
  return `http://127.0.0.1:${DEV_API_PORT}`;
}

/** Compile-time configuration. `EXPO_PUBLIC_*` is inlined by Metro. */
export const BUILD_TIME_API_BASE: string = process.env.EXPO_PUBLIC_API_BASE ?? "";

/**
 * The endpoint this build was made to talk to, before any operator override.
 *
 * Empty string means a build that was never configured AND is not a development run. That
 * is reported as `unconfigured` rather than silently substituted, because substituting the
 * emulator address there is precisely the hidden-local-endpoint failure being designed out.
 */
export function buildDefaultApiBase(isDevelopment: boolean = __DEV__): string {
  const built = BUILD_TIME_API_BASE.trim();
  if (built !== "") return built;
  return isDevelopment ? developmentDefault() : "";
}

/** Backwards-compatible name. The build's endpoint, ignoring any override. */
export function defaultApiBase(): string {
  return buildDefaultApiBase();
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

/**
 * Decide which endpoint this run uses, and say why.
 *
 * An override is applied only when all of it holds:
 *   - it is the current schema version (a v1 record cannot prove anything about itself),
 *   - its value is a usable absolute origin,
 *   - it records the build default it was saved against,
 *   - and that build default is the one in force now.
 *
 * The last clause is the fix. A newer build carrying a different endpoint means the saved
 * value was configured for a different application, so it is discarded and the build wins.
 * The alternative -- keeping it -- is what made a correct APK unusable until someone
 * thought to clear app data.
 */
export function resolveApiBase(
  override: ApiBaseOverride | null,
  buildDefault: string
): ResolvedApiBase {
  const source: ApiBaseSource =
    buildDefault === ""
      ? "unconfigured"
      : BUILD_TIME_API_BASE.trim() !== ""
        ? "build-default"
        : "development-default";

  const fallback: ResolvedApiBase = { base: buildDefault, source, rejected: null };

  if (override === null) return fallback;

  if (override.version !== API_BASE_OVERRIDE_VERSION) {
    // Includes every v1 record. It carries no provenance, so it cannot be shown to be
    // current, and "cannot be shown to be current" has to mean discarded -- the opposite
    // default is the defect.
    return { ...fallback, rejected: "legacy" };
  }

  const value = normaliseApiBase(override.value ?? "");
  if (value === null || typeof override.buildBase !== "string") {
    return { ...fallback, rejected: "malformed" };
  }

  if (override.buildBase !== buildDefault) {
    return { ...fallback, rejected: "stale" };
  }

  return { base: value, source: "operator-override", rejected: null };
}

/** Human-readable, for the settings screen. Never a URL -- the address is shown separately. */
export function describeApiBaseSource(source: ApiBaseSource): string {
  switch (source) {
    case "operator-override":
      return "Operator override";
    case "build-default":
      return "Build default";
    case "development-default":
      return "Development default";
    case "unconfigured":
    default:
      return "Not configured";
  }
}

/** Why a saved override was dropped, for the settings screen. `null` when none was. */
export function describeOverrideRejection(rejection: OverrideRejection | null): string | null {
  switch (rejection) {
    case "legacy":
      return "A saved endpoint from an older build was discarded. This build's endpoint is in use.";
    case "stale":
      return "A saved endpoint was saved against a different build and was discarded. This build's endpoint is in use.";
    case "malformed":
      return "A saved endpoint could not be read and was discarded. This build's endpoint is in use.";
    default:
      return null;
  }
}
