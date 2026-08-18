/**
 * The lifecycle of a saved API endpoint, and the wording of an empty order history.
 *
 * NATIVE ANDROID ACCEPTANCE, issue A. The preview APK correctly carried
 * `http://10.0.2.2:18080`, the manifest correctly allowed local cleartext traffic, and
 * emulator Chrome reached the API. The app still showed "Cannot reach the store" and the
 * backend received NO REQUEST AT ALL, because an override saved by an older build still
 * pinned it to `:18000`. Clearing app storage fixed it instantly, which is the signature of
 * state outliving the build that created it.
 *
 * The precedence was invisible to the old suite because it lived inside a `useEffect` that
 * read AsyncStorage. Extracting `resolveApiBase` as a pure function is what makes the rule
 * testable at all, so these tests are the point of that refactor rather than an afterthought.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  API_BASE_OVERRIDE_VERSION,
  buildDefaultApiBase,
  describeApiBaseSource,
  describeOverrideRejection,
  normaliseApiBase,
  resolveApiBase,
  type ApiBaseOverride,
} from "../config";

/** The endpoint the current preview APK is built with. */
const NEW_BUILD = "http://10.0.2.2:18080";
/** The endpoint an older build was built with, and which an operator saved against it. */
const OLD_BUILD = "http://10.0.2.2:18000";

function override(partial: Partial<ApiBaseOverride>): ApiBaseOverride {
  return {
    version: API_BASE_OVERRIDE_VERSION,
    value: NEW_BUILD,
    buildBase: NEW_BUILD,
    ...partial,
  };
}

// ------------------------------------------------------- the reported acceptance failure

describe("the stale override that made a correct APK unusable", () => {
  it("does not stay pinned to the old endpoint when the build endpoint has changed", () => {
    // Exactly the reported state: :18000 saved by the previous build, :18080 in this one.
    const stored = override({ value: OLD_BUILD, buildBase: OLD_BUILD });

    const resolved = resolveApiBase(stored, NEW_BUILD);

    expect(resolved.base).toBe(NEW_BUILD);
    expect(resolved.base).not.toBe(OLD_BUILD);
    expect(resolved.rejected).toBe("stale");
  });

  it("discards a legacy record that cannot prove which build it belongs to", () => {
    // v1 was a bare string. It has no provenance, so it can never be shown to be current.
    const legacy: ApiBaseOverride = { version: 1, value: OLD_BUILD, buildBase: "" };

    const resolved = resolveApiBase(legacy, NEW_BUILD);

    expect(resolved.base).toBe(NEW_BUILD);
    expect(resolved.rejected).toBe("legacy");
  });

  it("reports the discard so the endpoint does not appear to change by itself", () => {
    for (const rejection of ["legacy", "stale", "malformed"] as const) {
      const text = describeOverrideRejection(rejection);
      expect(text).not.toBeNull();
      expect(String(text)).toMatch(/discarded/i);
    }
    expect(describeOverrideRejection(null)).toBeNull();
  });
});

// ------------------------------------------------------------ an override that is current

describe("a valid current override", () => {
  it("is applied when it was saved against this build", () => {
    // The case the feature exists for: one build, reached from an emulator and a handset.
    const lan = "http://192.168.1.50:18080";
    const resolved = resolveApiBase(override({ value: lan, buildBase: NEW_BUILD }), NEW_BUILD);

    expect(resolved.base).toBe(lan);
    expect(resolved.source).toBe("operator-override");
    expect(resolved.rejected).toBeNull();
  });

  it("survives when it happens to equal the build default", () => {
    const resolved = resolveApiBase(override({}), NEW_BUILD);

    expect(resolved.base).toBe(NEW_BUILD);
    expect(resolved.source).toBe("operator-override");
  });

  it("falls back to the build default when there is no override at all", () => {
    const resolved = resolveApiBase(null, NEW_BUILD);

    expect(resolved.base).toBe(NEW_BUILD);
    expect(resolved.rejected).toBeNull();
  });
});

// ------------------------------------------------------------- refusing unusable records

describe("malformed and blank overrides", () => {
  it.each([
    ["blank", ""],
    ["whitespace", "   "],
    ["no scheme", "10.0.2.2:18080"],
    ["wrong scheme", "ftp://10.0.2.2:18080"],
    ["not a url", "not a url at all"],
  ])("rejects a %s value and uses the build default", (_label, value) => {
    const resolved = resolveApiBase(override({ value }), NEW_BUILD);

    expect(resolved.base).toBe(NEW_BUILD);
    expect(resolved.rejected).toBe("malformed");
  });

  it("rejects a record whose provenance field is not a string", () => {
    const broken = { version: API_BASE_OVERRIDE_VERSION, value: NEW_BUILD } as ApiBaseOverride;

    expect(resolveApiBase(broken, NEW_BUILD).rejected).toBe("malformed");
  });

  it("normalises a trailing slash rather than treating it as a different endpoint", () => {
    expect(normaliseApiBase("http://10.0.2.2:18080/")).toBe(NEW_BUILD);
    expect(normaliseApiBase("http://10.0.2.2:18080///")).toBe(NEW_BUILD);
  });
});

// ------------------------------------------- production must not inherit a local endpoint

describe("the build default", () => {
  it("offers an emulator loopback ONLY in development", () => {
    // A release build that fell through to 10.0.2.2 would ship a hidden local endpoint and
    // fail like a network fault. Real builds set EXPO_PUBLIC_API_BASE through eas.json.
    expect(buildDefaultApiBase(true)).toMatch(/^https?:\/\//);
    expect(buildDefaultApiBase(false)).toBe("");
  });

  it("reports an unconfigured build as unconfigured rather than substituting one", () => {
    const resolved = resolveApiBase(null, "");

    expect(resolved.base).toBe("");
    expect(resolved.source).toBe("unconfigured");
  });

  it("will not let an override resurrect an endpoint on an unconfigured build", () => {
    // A stamp of a real address cannot match an empty build default, so it is stale.
    const resolved = resolveApiBase(override({ value: OLD_BUILD, buildBase: OLD_BUILD }), "");

    expect(resolved.base).toBe("");
    expect(resolved.rejected).toBe("stale");
  });
});

describe("describeApiBaseSource", () => {
  it("names each source in words an operator can act on", () => {
    expect(describeApiBaseSource("build-default")).toBe("Build default");
    expect(describeApiBaseSource("operator-override")).toBe("Operator override");
    expect(describeApiBaseSource("development-default")).toBe("Development default");
    expect(describeApiBaseSource("unconfigured")).toBe("Not configured");
  });
});

// -------------------------------------- the emulator address stays inside a dev-only path

describe("the emulator loopback is confined", () => {
  const SRC = join(__dirname, "..");

  /** Strip comments: these files explain the defect, and prose is not a dependency. */
  function code(relative: string): string {
    const raw = readFileSync(join(SRC, relative), "utf8");
    return raw.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  }

  it("appears in config.ts only inside the development-only default", () => {
    const source = code("config.ts");
    const hits = source.split("10.0.2.2").length - 1;

    // Exactly one, and it is the line `developmentDefault` returns. Anywhere else would be
    // a path a release build could reach.
    expect(hits).toBe(1);
    expect(source).toContain("function developmentDefault()");
    const fn = source.slice(source.indexOf("function developmentDefault()"));
    expect(fn.slice(0, fn.indexOf("}"))).toContain("10.0.2.2");
  });

  it("appears on the settings screen only behind a __DEV__ guard", () => {
    const source = code("screens/SettingsScreen.tsx");
    const guard = source.indexOf("__DEV__");

    expect(guard).toBeGreaterThan(-1);
    expect(source.indexOf("10.0.2.2")).toBeGreaterThan(guard);
  });

  it("appears nowhere else in the application source", () => {
    for (const file of [
      "store.ts",
      "storage.ts",
      "brand.ts",
      "api/client.ts",
      "api/commerce.ts",
      "screens/CatalogScreen.tsx",
      "screens/OrdersScreen.tsx",
    ]) {
      expect(code(file)).not.toContain("10.0.2.2");
    }
  });
});
