/**
 * Sign in, register, sign out.
 *
 * Registration is offered because `POST /api/v1/auth/register` exists in the contract and
 * returns a session directly. Its password minimum (8) and e-mail pattern mirror the
 * server's `RegisterRequest`, so the common mistakes are caught before a request is spent
 * against a 5-per-hour rate-limit bucket.
 */

import React, { useCallback, useState } from "react";
import { Pressable, Switch, Text, TextInput, View } from "react-native";

import { describeFailure } from "../api/client";
import { BRAND } from "../brand";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, Heading, Screen, styles } from "../ui";

// Mirrors app/commerce/api.py:63. Deliberately permissive: strict RFC 5322 rejects
// addresses real mail systems accept, and deliverability is proven by sending, not regex.
const EMAIL_PATTERN = /^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/;

type Mode = "signIn" | "register";

export function AccountScreen({ app }: { app: AppState }) {
  const { session, signIn, signUp, signOut, navigate, notice } = app;

  const [mode, setMode] = useState<Mode>("signIn");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setError(null);

    if (!EMAIL_PATTERN.test(email.trim())) {
      setError("Please enter a valid e-mail address.");
      return;
    }
    if (mode === "register") {
      if (fullName.trim().length === 0) {
        setError("Please enter your name.");
        return;
      }
      if (password.length < 8) {
        setError("Please choose a password of at least 8 characters.");
        return;
      }
    } else if (password.length === 0) {
      setError("Please enter your password.");
      return;
    }

    setBusy(true);
    try {
      if (mode === "register") {
        await signUp(email.trim(), password, fullName.trim(), consent);
      } else {
        await signIn(email.trim(), password);
      }
      // Never keep the password in state after a successful exchange.
      setPassword("");
      navigate({ name: "catalog" });
    } catch (failure) {
      setError(describeFailure(failure));
    } finally {
      setBusy(false);
    }
  }, [mode, email, password, fullName, consent, signIn, signUp, navigate]);

  if (session !== null) {
    return (
      <Screen>
        <Heading>Account</Heading>
        <Card>
          <Text style={styles.rowStrong}>{session.email}</Text>
          <Body muted>Signed in{session.role !== "customer" ? ` · ${session.role}` : ""}</Body>
        </Card>
        <Button label="Your orders" onPress={() => navigate({ name: "orders" })} />
        <Button
          testID="sign-out"
          label="Sign out"
          variant="secondary"
          onPress={() => {
            void signOut();
          }}
        />
        <Button label="API settings" variant="secondary" onPress={() => navigate({ name: "settings" })} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Heading>{mode === "signIn" ? "Sign in" : "Create an account"}</Heading>

      {notice !== null ? <Banner testID="session-notice" tone="warning" message={notice} /> : null}
      {error !== null ? <Banner testID="account-error" tone="error" message={error} /> : null}

      <Card>
        {mode === "register" ? (
          <Field
            label="Full name"
            value={fullName}
            onChange={setFullName}
            testID="field-name"
            autoComplete="name"
          />
        ) : null}
        <Field
          label="E-mail"
          value={email}
          onChange={setEmail}
          testID="field-email"
          keyboardType="email-address"
          autoComplete="email"
        />
        <Field
          label="Password"
          value={password}
          onChange={setPassword}
          testID="field-password"
          secure
          autoComplete={mode === "register" ? "new-password" : "current-password"}
        />
        {mode === "register" ? (
          <View style={[styles.row, { alignItems: "center" }]}>
            <Text style={styles.body}>Send me marketing e-mail</Text>
            <Switch
              testID="field-consent"
              value={consent}
              onValueChange={setConsent}
              accessibilityLabel="Send me marketing e-mail"
            />
          </View>
        ) : null}
      </Card>

      <Button
        testID="account-submit"
        label={mode === "signIn" ? "Sign in" : "Create account"}
        busy={busy}
        onPress={() => void submit()}
      />

      <Pressable
        testID="account-toggle-mode"
        accessibilityRole="button"
        onPress={() => {
          setMode(mode === "signIn" ? "register" : "signIn");
          setError(null);
        }}
      >
        <Text style={{ color: BRAND.palette.accent, fontWeight: "700" }}>
          {mode === "signIn" ? "Create an account instead" : "I already have an account"}
        </Text>
      </Pressable>

      <Button label="API settings" variant="secondary" onPress={() => navigate({ name: "settings" })} />
    </Screen>
  );
}

function Field({
  label,
  value,
  onChange,
  testID,
  secure = false,
  keyboardType,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  testID: string;
  secure?: boolean;
  keyboardType?: "email-address";
  autoComplete?: "name" | "email" | "new-password" | "current-password";
}) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={styles.body}>{label}</Text>
      <TextInput
        testID={testID}
        accessibilityLabel={label}
        value={value}
        onChangeText={onChange}
        secureTextEntry={secure}
        autoCapitalize="none"
        autoCorrect={false}
        {...(keyboardType ? { keyboardType } : {})}
        {...(autoComplete ? { autoComplete } : {})}
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
    </View>
  );
}
