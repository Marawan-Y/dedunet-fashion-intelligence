/**
 * Mobile guard-mutation harness.
 *
 * Same discipline as `scripts/validation/mutation_guard_check.py`: remove one protected
 * behaviour at a time and require the guarding test to fail. A guard whose removal nobody
 * notices is not a guard.
 *
 * Two properties matter and are both enforced:
 *   1. A mutation whose anchor no longer matches is an ERROR, not a skip. A rotted anchor
 *      silently retires a guard, which is exactly how the backend harness caught five
 *      dead entries during Workstream B.
 *   2. Each mutation declares the test file that must fail AND a fragment that must appear
 *      in the failure output, so "it failed" is not mistaken for "it failed for the right
 *      reason". A syntax error would otherwise count as a detection.
 *
 * Exit 0 = every mutation detected. Exit 1 = at least one survived or misfired.
 */

import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/** @typedef {{id:string,file:string,find:string,replace:string,test:string,expect:string,why:string}} Mutation */

/** @type {Mutation[]} */
const MUTATIONS = [
  {
    id: "M1",
    why: "zero-variant products fall back to Math.min(...[]) === Infinity",
    file: "src/money.ts",
    find: `  let lowest: number | null = null;
  for (const variant of variants) {
    const price = variant.price_minor_units;
    if (!isMinorUnits(price)) continue;
    if (lowest === null || price < lowest) lowest = price;
  }
  return lowest;`,
    replace: `  return Math.min(...variants.map((v) => v.price_minor_units as number));`,
    test: "src/__tests__/money.test.ts",
    expect: "lowestPriceMinorUnits",
  },
  {
    id: "M2",
    why: "a binary float is accepted as an authoritative price",
    file: "src/money.ts",
    find: `  return typeof value === "number" && Number.isSafeInteger(value);`,
    replace: `  return typeof value === "number";`,
    test: "src/__tests__/money.test.ts",
    expect: "formatMinorUnits",
  },
  {
    id: "M3",
    why: "an unreviewed currency silently gets a 2-digit exponent",
    file: "src/money.ts",
    find: `  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined) return null;`,
    replace: `  const exponent = MINOR_UNIT_EXPONENTS[currency] ?? 2;`,
    test: "src/__tests__/money.test.ts",
    expect: "reviewed",
  },
  {
    id: "M4",
    why: "an unverified origin is rendered as a 'Made in' claim",
    file: "src/origin.ts",
    find: `  return \`Declared origin \${code.toUpperCase()} — not independently verified\`;`,
    replace: `  return \`Made in \${code.toUpperCase()}\`;`,
    test: "src/__tests__/origin.test.ts",
    expect: "made in",
  },
  {
    id: "M5",
    why: "the invalid XX placeholder is treated as a real country",
    file: "src/origin.ts",
    find: `const UNSUBSTANTIATED = new Set(["", "XX", "xx"]);`,
    replace: `const UNSUBSTANTIATED = new Set([""]);`,
    test: "src/__tests__/origin.test.ts",
    expect: "originLabel",
  },
  {
    id: "M6",
    why: "HTTP 429 is collapsed into a generic client error, losing Retry-After",
    file: "src/api/client.ts",
    find: `  if (status === 429) return "rate_limited";`,
    replace: ``,
    test: "src/__tests__/client.test.ts",
    expect: "rate_limited",
  },
  {
    id: "M7",
    why: "a dropped connection is reported as an expired session, signing the customer out",
    file: "src/api/client.ts",
    find: `    const aborted = cause instanceof Error && cause.name === "AbortError";`,
    replace: `    const aborted = false;`,
    test: "src/__tests__/client.test.ts",
    expect: "timeout",
  },
  {
    id: "M8",
    why: "a non-JSON 200 body is passed to the screens instead of being rejected",
    file: "src/api/client.ts",
    find: `  if (parsed === null && raw.length > 0) {
    throw new ApiError("malformed", "the response was not valid JSON", {
      status: response.status,
      correlationId,
    });
  }`,
    replace: ``,
    test: "src/__tests__/client.test.ts",
    expect: "malformed",
  },
  {
    id: "M9",
    why: "a renamed price field reaches the UI as undefined instead of failing loudly",
    file: "src/api/commerce.ts",
    find: `    if (typeof variant.price_minor_units !== "number") malformed("variant");`,
    replace: ``,
    test: "src/__tests__/commerce.test.ts",
    expect: "malformed",
  },
  {
    id: "M10",
    why: "decreasing a cart line POSTs the absolute quantity, silently increasing it",
    file: "src/api/commerce.ts",
    find: `  await removeCartItem(baseUrl, cartToken, variantId);
  return addCartItem(baseUrl, cartToken, variantId, desiredQuantity);`,
    replace: `  return addCartItem(baseUrl, cartToken, variantId, desiredQuantity);`,
    test: "src/__tests__/commerce.test.ts",
    expect: "setCartItemQuantity",
  },
  {
    id: "M11",
    why: "an empty cart reports a 400 as a hard error instead of an empty basket",
    file: "src/api/commerce.ts",
    find: `    if (error instanceof ApiError && error.status === 400) return null;`,
    replace: ``,
    test: "src/__tests__/commerce.test.ts",
    expect: "quoteCart",
  },
  {
    id: "M12",
    why: "signing out discards the shopper's bag",
    file: "src/storage.ts",
    find: `export async function clearSession(): Promise<void> {
  await remove(KEY_SESSION);
}`,
    replace: `export async function clearSession(): Promise<void> {
  await remove(KEY_SESSION);
  await remove(KEY_CART);
}`,
    test: "src/__tests__/storage.test.ts",
    expect: "cart",
  },
  {
    id: "M13",
    why: "a corrupt stored session crashes the boot path instead of degrading to signed out",
    file: "src/storage.ts",
    find: `  } catch {
    // A corrupt record is discarded rather than crashing the boot path.
    return null;
  }`,
    replace: `  } finally {
    // mutated
  }`,
    test: "src/__tests__/storage.test.ts",
    expect: "corrupt",
  },
  {
    id: "M14",
    why: "an empty catalogue is rendered as a fetch error",
    file: "src/screens/CatalogScreen.tsx",
    find: `      {catalog.status === "ready" && catalog.products.length === 0 ? (`,
    replace: `      {false ? (`,
    test: "src/__tests__/screens.test.tsx",
    expect: "catalog-empty",
  },
  {
    id: "M15",
    why: "the sandbox notice is dropped, so a prototype looks like a real shop",
    file: "src/screens/CatalogScreen.tsx",
    find: `      <Banner tone="warning" message={SANDBOX_NOTICE} testID="sandbox-notice" />`,
    replace: ``,
    test: "src/__tests__/screens.test.tsx",
    expect: "sandbox-notice",
  },
  {
    id: "M16",
    why: "a screen hard-codes the brand name, breaking the single-seam rule",
    file: "src/screens/CatalogScreen.tsx",
    find: `      <Heading>{BRAND.name}</Heading>`,
    replace: `      <Heading>{"DEDUNET"}</Heading>`,
    test: "src/__tests__/brand.test.ts",
    expect: "literal",
  },
  {
    id: "M17",
    why: "the app points at a NEW EAS project instead of the existing one",
    file: "app.json",
    find: `"projectId": "72b0a18d-36dd-406f-a54b-ab481a95db88"`,
    replace: `"projectId": "00000000-0000-0000-0000-000000000000"`,
    test: "src/__tests__/brand.test.ts",
    expect: "EAS",
  },
  {
    id: "M18",
    why: "the app regresses to the legacy fixture catalogue endpoint",
    file: "src/api/commerce.ts",
    find: `  const body = await request<unknown>(baseUrl, "/api/v1/catalog/products", { signal });`,
    replace: `  const body = await request<unknown>(baseUrl, "/api/v1/products", { signal });`,
    test: "src/__tests__/contract.test.ts",
    expect: "legacy",
  },
];

/**
 * Run one jest file and return its exit status plus BOTH streams.
 *
 * `spawnSync` with `shell: true`, not execFileSync: on Windows execFileSync could not
 * resolve `npx.cmd` and threw with `stdout`/`stderr` undefined. Every mutation then looked
 * like "failed for the wrong reason" — 18 identical misfires caused by the runner, not by
 * the guards. Jest writes its report to stderr, so both streams must be joined.
 */
function runTest(testFile) {
  const result = spawnSync("npx", ["jest", "--ci", testFile], {
    cwd: ROOT,
    encoding: "utf8",
    shell: true,
  });
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  if (result.error) throw result.error;
  if (output.trim() === "") throw new Error(`no output captured while running ${testFile}`);
  return { failed: result.status !== 0, output };
}

let detected = 0;
const survivors = [];
const errors = [];

console.log(`mobile guard mutations: ${MUTATIONS.length}\n`);

for (const mutation of MUTATIONS) {
  const path = join(ROOT, mutation.file);
  const original = readFileSync(path, "utf8");

  if (!original.includes(mutation.find)) {
    // A rotted anchor is an error, never a skip: skipping retires the guard in silence.
    errors.push(`${mutation.id}: anchor not found in ${mutation.file}`);
    console.log(`${mutation.id}  ANCHOR ROTTED  ${mutation.file}`);
    continue;
  }

  writeFileSync(path, original.replace(mutation.find, mutation.replace), "utf8");
  try {
    const { failed, output } = runTest(mutation.test);
    const matchedReason = output.toLowerCase().includes(mutation.expect.toLowerCase());

    if (failed && matchedReason) {
      detected += 1;
      console.log(`${mutation.id}  detected      ${mutation.why}`);
    } else if (failed) {
      errors.push(`${mutation.id}: failed, but not for the stated reason ("${mutation.expect}")`);
      console.log(`${mutation.id}  WRONG REASON  ${mutation.why}`);
    } else {
      survivors.push(`${mutation.id}: ${mutation.why}`);
      console.log(`${mutation.id}  SURVIVED      ${mutation.why}`);
    }
  } finally {
    writeFileSync(path, original, "utf8");
  }
}

console.log(`\nMUTATIONS RUN: ${MUTATIONS.length}`);
console.log(`DETECTED:      ${detected}`);
console.log(`SURVIVED:      ${survivors.length}`);
console.log(`ERRORS:        ${errors.length}`);

for (const line of [...survivors, ...errors]) console.log(`  - ${line}`);

if (survivors.length > 0 || errors.length > 0) {
  console.log("\nRESULT: at least one guard does not guard.");
  process.exit(1);
}
console.log("\nRESULT: every guard removal was detected by its guarding test.");
