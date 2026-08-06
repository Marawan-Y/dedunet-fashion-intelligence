/**
 * Brand-boundary and configuration guards.
 *
 * Two separate obligations from the manager brief:
 *   §7 remove hard architectural dependence on the legacy brand and route everything
 *      through one seam;
 *   §8 the app configuration must carry the EXISTING EAS project, not a new one.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { BRAND } from "../brand";

const MOBILE_ROOT = join(__dirname, "..", "..");
const SRC_ROOT = join(__dirname, "..");

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === "dist" || entry === ".expo") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full));
    else if (/\.(ts|tsx)$/.test(entry)) out.push(full);
  }
  return out;
}

describe("legacy brand boundary", () => {
  /**
   * Application source only.
   *
   * `__tests__` is excluded because these guards must contain the very strings they
   * forbid in order to search for them — this file names MERET and MERYT below. An
   * earlier version scanned itself and failed on its own assertion.
   */
  const files = [
    ...sourceFiles(SRC_ROOT).filter((file) => !file.includes("__tests__")),
    join(MOBILE_ROOT, "App.tsx"),
    join(MOBILE_ROOT, "index.ts"),
  ];

  it("covers the whole application, so an exclusion cannot empty the check", () => {
    // Without this, deleting every source file would make the guards below pass.
    expect(files.length).toBeGreaterThanOrEqual(12);
    expect(files.some((f) => f.endsWith("client.ts"))).toBe(true);
    expect(files.some((f) => f.endsWith("CatalogScreen.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("App.tsx"))).toBe(true);
  });

  it("no source file references the legacy brand names", () => {
    const offenders: string[] = [];
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      // Word-boundary match so "meret" inside an unrelated identifier is not a false hit.
      if (/\bMERET\b|\bMERYT\b/i.test(text)) offenders.push(file);
    }
    expect(offenders).toEqual([]);
  });

  it("the brand name appears as a literal in exactly one module", () => {
    // Everything else must read BRAND.name. This is what makes the Side A identity import
    // a one-file change instead of a repository-wide replacement.
    const offenders = files.filter((file) => {
      if (file.endsWith(join("src", "brand.ts"))) return false;
      return /["'`]DEDUNET["'`]/.test(readFileSync(file, "utf8"));
    });
    expect(offenders).toEqual([]);
  });

  it("no screen hard-codes a palette colour", () => {
    // Hex literals belong in brand.ts. A stray #f4f0e8 in a screen is a token that the
    // Side A import would silently miss.
    const offenders = sourceFiles(join(SRC_ROOT, "screens")).filter((file) =>
      /#[0-9a-fA-F]{6}\b/.test(readFileSync(file, "utf8"))
    );
    expect(offenders).toEqual([]);
  });

  it("exposes a complete palette through the seam", () => {
    for (const key of [
      "background",
      "surface",
      "border",
      "text",
      "textMuted",
      "accent",
      "accentText",
      "danger",
      "warning",
      "success",
    ] as const) {
      expect(BRAND.palette[key]).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it("does not yet import the Side A brand package — that is the next milestone", () => {
    // Matches real import/require statements only. An earlier version grepped for the
    // bare string and flagged brand.ts's own comment explaining what is deliberately NOT
    // imported yet -- a test that failed on its own documentation.
    const importPattern = /(?:import[^;]*from\s*["'`][^"'`]*brand-prototype|require\(\s*["'`][^"'`]*brand-prototype)/;
    const offenders = files.filter((file) => importPattern.test(readFileSync(file, "utf8")));
    expect(offenders).toEqual([]);
  });
});

describe("app configuration", () => {
  const appJson = JSON.parse(readFileSync(join(MOBILE_ROOT, "app.json"), "utf8")) as {
    expo: {
      name: string;
      slug: string;
      owner?: string;
      ios: { bundleIdentifier: string };
      android: { package: string };
      extra?: { eas?: { projectId?: string } };
    };
  };

  it("targets the EXISTING EAS project", () => {
    expect(appJson.expo.extra?.eas?.projectId).toBe("72b0a18d-36dd-406f-a54b-ab481a95db88");
  });

  it("uses the mandated slug, owner and identifiers", () => {
    expect(appJson.expo.slug).toBe("dedunet");
    expect(appJson.expo.owner).toBe("Dedunet");
    expect(appJson.expo.ios.bundleIdentifier).toBe("com.dedunet.store");
    expect(appJson.expo.android.package).toBe("com.dedunet.store");
  });

  it("no longer carries the reserved com.example namespace", () => {
    // com.example.* can never be published to either store.
    const serialised = JSON.stringify(appJson);
    expect(serialised).not.toContain("com.example");
    expect(serialised).not.toContain("origin-fashion-poc");
  });
});
