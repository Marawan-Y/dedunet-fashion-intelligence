/**
 * What the two screens actually put on the device.
 *
 * The rules are unit-tested elsewhere; this is about whether they reach a screen. Native
 * acceptance was spent on one unanswerable question -- "is this build talking to what I
 * think it is?" -- with the settings screen showing a single address and no indication of
 * where it came from, and a "Reset to default" button that only refilled the text box while
 * the saved override went on winning.
 *
 * The orders empty state is a separate issue and lives in `orders-copy.test.tsx`.
 */

import React from "react";
import TestRenderer, { act } from "react-test-renderer";

import { SettingsScreen } from "../screens/SettingsScreen";
import type { AppState } from "../store";

const NEW_BUILD = "http://10.0.2.2:18080";
const LAN = "http://192.168.1.50:18080";

function textOf(tree: TestRenderer.ReactTestRenderer, testID: string): string {
  const [node] = tree.root.findAll((n) => n.props?.testID === testID);
  return node === undefined ? "" : JSON.stringify(node.props.children);
}

function has(tree: TestRenderer.ReactTestRenderer, testID: string): boolean {
  return tree.root.findAll((n) => n.props?.testID === testID).length > 0;
}

// ------------------------------------------------------------------------- settings

function settingsApp(overrides: Partial<AppState>): AppState {
  return {
    apiBase: NEW_BUILD,
    apiBaseSource: "build-default",
    apiBaseRejection: null,
    buildDefaultApiBase: NEW_BUILD,
    setApiBase: jest.fn(),
    resetApiBaseToBuildDefault: jest.fn().mockResolvedValue(undefined),
    navigate: jest.fn(),
    loadCatalog: jest.fn(),
    ...overrides,
  } as unknown as AppState;
}

function renderSettings(overrides: Partial<AppState> = {}): TestRenderer.ReactTestRenderer {
  let tree!: TestRenderer.ReactTestRenderer;
  act(() => {
    tree = TestRenderer.create(<SettingsScreen app={settingsApp(overrides)} />);
  });
  return tree;
}

describe("settings shows where the endpoint came from", () => {
  it("names the build default as the source when no override is in force", () => {
    const tree = renderSettings();

    expect(textOf(tree, "settings-api-base-source")).toContain("Build default");
    expect(textOf(tree, "settings-api-base-current")).toContain(NEW_BUILD);
  });

  it("names an operator override as such, and still shows the build default", () => {
    // Both, deliberately: knowing an override is in force is only useful next to what it
    // is overriding.
    const tree = renderSettings({ apiBase: LAN, apiBaseSource: "operator-override" });

    expect(textOf(tree, "settings-api-base-source")).toContain("Operator override");
    expect(textOf(tree, "settings-api-base-current")).toContain(LAN);
    expect(textOf(tree, "settings-api-base-build-default")).toContain(NEW_BUILD);
  });

  it("says so when the build carries no endpoint at all", () => {
    const tree = renderSettings({
      apiBase: "",
      apiBaseSource: "unconfigured",
      buildDefaultApiBase: "",
    });

    expect(textOf(tree, "settings-api-base-source")).toContain("Not configured");
    expect(textOf(tree, "settings-api-base-current")).toContain("none configured");
  });
});

describe("settings explains a discarded override", () => {
  it.each([["stale"], ["legacy"], ["malformed"]] as const)(
    "shows a banner when a %s override was dropped",
    (rejection) => {
      // Without this the address changes between launches with no explanation, which reads
      // as the app being unreliable rather than as it recovering.
      const tree = renderSettings({ apiBaseRejection: rejection });

      expect(has(tree, "settings-override-discarded")).toBe(true);
    }
  );

  it("shows no banner when nothing was discarded", () => {
    expect(has(renderSettings(), "settings-override-discarded")).toBe(false);
  });
});

describe("the reset action", () => {
  it("is present and clears the SAVED override, not just the text field", async () => {
    const resetApiBaseToBuildDefault = jest.fn().mockResolvedValue(undefined);
    const tree = renderSettings({
      apiBase: LAN,
      apiBaseSource: "operator-override",
      resetApiBaseToBuildDefault,
    });

    const [button] = tree.root.findAll((n) => n.props?.testID === "settings-reset-endpoint");
    expect(button).toBeDefined();
    if (button === undefined) throw new Error("reset button is missing");

    await act(async () => {
      button.props.onPress();
    });

    // The old button called setDraft() and nothing else, so the override survived and the
    // only real cure was clearing app storage.
    expect(resetApiBaseToBuildDefault).toHaveBeenCalledTimes(1);
  });
});
