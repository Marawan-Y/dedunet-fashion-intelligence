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
import { defaultApiBase, normaliseApiBase } from "../config";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, Heading, Screen, styles } from "../ui";

export function SettingsScreen({ app }: { app: AppState }) {
  const { apiBase, setApiBase, navigate, loadCatalog } = app;

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
        <Body muted>Currently in use: {apiBase}</Body>
      </Card>

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
      <Button
        label="Reset to default"
        variant="secondary"
        onPress={() => setDraft(defaultApiBase())}
      />

      <Card>
        <Text style={styles.rowStrong}>Reaching the API from a device</Text>
        <View style={{ gap: 4 }}>
          <Body muted>Android emulator — http://10.0.2.2:18000</Body>
          <Body muted>iOS simulator / web — http://127.0.0.1:18000</Body>
          <Body muted>Physical device — http://&lt;your LAN IP&gt;:18000</Body>
          <Body muted>Local staging stack — port 18080 instead of 18000</Body>
        </View>
      </Card>

      <Button label="Back" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}
