/**
 * Runtime API configuration.
 *
 * A device cannot be rebuilt to point at a different host, and the correct base URL is not
 * knowable at build time: an Android emulator needs 10.0.2.2, a simulator needs 127.0.0.1
 * and a physical handset needs the development machine's LAN address. Making this editable
 * at runtime is what lets one build be tested from all three.
 */

import React, { useCallback, useState } from "react";
import { Text, TextInput, View } from "react-native";

import { describeFailure } from "../api/client";
import { listProducts } from "../api/commerce";
import { BRAND } from "../brand";
import { describeApiBaseSource, normaliseApiBase } from "../config";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, Heading, Screen, styles } from "../ui";

export function SettingsScreen({ app }: { app: AppState }) {
  const {
    apiBase,
    apiBaseSource,
    apiBaseRejection,
    buildDefaultApiBase,
    setApiBase,
    resetApiBaseToBuildDefault,
    navigate,
    loadCatalog,
  } = app;

  const [draft, setDraft] = useState(apiBase);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  /**
   * Save only after the address actually answers.
   *
   * Saving an unreachable base would leave every subsequent screen failing with a network
   * error and no obvious cause, which is far harder to diagnose than a refusal here.
   */
  const saveAndTest = useCallback(async () => {
    const normalised = normaliseApiBase(draft);
    if (normalised === null) {
      setResult({ tone: "error", text: "Enter a full URL including http:// or https://" });
      return;
    }

    setBusy(true);
    setResult(null);
    try {
      const products = await listProducts(normalised);
      await setApiBase(normalised);
      setDraft(normalised);
      setResult({
        tone: "success",
        text: `Connected. ${products.length} product${products.length === 1 ? "" : "s"} visible.`,
      });
      void loadCatalog();
    } catch (failure) {
      setResult({ tone: "error", text: `Not saved — ${describeFailure(failure)}` });
    } finally {
      setBusy(false);
    }
  }, [draft, setApiBase, loadCatalog]);

  return (
    <Screen>
      <Heading>API settings</Heading>
      <Body muted>
        The address of the commerce API this build talks to. It is verified before it is saved.
      </Body>

      <Card>
        <Text style={styles.body}>API base URL</Text>
        <TextInput
          testID="settings-api-base"
          accessibilityLabel="API base URL"
          value={draft}
          onChangeText={setDraft}
          autoCapitalize="none"
          autoCorrect={false}
          inputMode="url"
          style={{
            borderWidth: 1,
            borderColor: BRAND.palette.border,
            borderRadius: 8,
            padding: 12,
            fontSize: 15,
            color: BRAND.palette.text,
            backgroundColor: BRAND.palette.surface,
            minHeight: 46,
          }}
        />
        <Body muted testID="settings-api-base-current">
          Currently in use: {apiBase === "" ? "none configured" : apiBase}
        </Body>
        {/* Which of the two it came from. Native acceptance spent its time on exactly this
            question -- "is this build talking to what I think it is?" -- with nothing on
            screen able to answer it. */}
        <Body muted testID="settings-api-base-source">
          Source: {describeApiBaseSource(apiBaseSource)}
        </Body>
        <Body muted testID="settings-api-base-build-default">
          Build default: {buildDefaultApiBase === "" ? "none configured" : buildDefaultApiBase}
        </Body>
      </Card>

      {apiBaseRejection !== null ? (
        <Banner
          testID="settings-override-discarded"
          tone="warning"
          message={
            apiBaseRejection === "stale"
              ? "A saved endpoint from a different build was discarded. This build's endpoint is in use."
              : apiBaseRejection === "legacy"
                ? "A saved endpoint from an older build was discarded. This build's endpoint is in use."
                : "A saved endpoint could not be read and was discarded. This build's endpoint is in use."
          }
        />
      ) : null}

      {result !== null ? (
        <Banner
          testID="settings-result"
          tone={result.tone === "success" ? "success" : "error"}
          message={result.text}
        />
      ) : null}

      <Button
        testID="settings-save"
        label="Test and save"
        busy={busy}
        onPress={() => void saveAndTest()}
      />
      {/* Previously this only refilled the text box, so the SAVED override survived and the
          app kept using it. The one cure for that was clearing app storage, which also
          destroyed the session and the cart. This forgets the override and nothing else. */}
      <Button
        testID="settings-reset-endpoint"
        label="Reset API endpoint to build default"
        variant="secondary"
        onPress={() => {
          void resetApiBaseToBuildDefault().then(() => {
            setDraft(buildDefaultApiBase);
            setResult({
              tone: "success",
              text:
                buildDefaultApiBase === ""
                  ? "Saved endpoint cleared. This build has no endpoint configured."
                  : `Saved endpoint cleared. Using the build default ${buildDefaultApiBase}.`,
            });
            void loadCatalog();
          });
        }}
      />

      {/* Development aid only. These are loopback addresses for a developer machine and
          have no meaning on a shipped build, so they are not rendered into one. */}
      {__DEV__ ? (
        <Card>
          <Text style={styles.rowStrong}>Reaching the API from a device</Text>
          <View style={{ gap: 4 }}>
            <Body muted>Android emulator — 10.0.2.2 on the API port</Body>
            <Body muted>iOS simulator / web — 127.0.0.1 on the API port</Body>
            <Body muted>Physical device — your machine&apos;s LAN IP</Body>
            <Body muted>docker-compose 18000 · local staging 18080</Body>
          </View>
        </Card>
      ) : null}

      <Button label="Back" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}
