/**
 * Shared presentational primitives.
 *
 * Every colour comes from `BRAND.palette` so the Side A token import later touches one
 * file. Every interactive element carries an accessibility role and label, because the
 * repository already treats accessibility as partially implemented rather than absent.
 */

import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ViewStyle,
} from "react-native";

import { BRAND } from "./brand";

const palette = BRAND.palette;

export function Screen({ children }: { children: React.ReactNode }) {
  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.screenContent}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  );
}

export function Heading({ children }: { children: React.ReactNode }) {
  return (
    <Text accessibilityRole="header" style={styles.heading}>
      {children}
    </Text>
  );
}

export function Body({
  children,
  muted,
  testID,
}: {
  children: React.ReactNode;
  muted?: boolean;
  /* Optional, so a line of body copy can be asserted on without wrapping it in a View. */
  testID?: string;
}) {
  return (
    <Text testID={testID} style={[styles.body, muted === true && styles.bodyMuted]}>
      {children}
    </Text>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Button({
  label,
  onPress,
  variant = "primary",
  disabled = false,
  busy = false,
  testID,
}: {
  label: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  busy?: boolean;
  testID?: string;
}) {
  const inactive = disabled || busy;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: inactive, busy }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === "secondary" && styles.buttonSecondary,
        variant === "danger" && styles.buttonDanger,
        inactive && styles.buttonDisabled,
        pressed && !inactive && styles.buttonPressed,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={variant === "secondary" ? palette.text : palette.accentText} />
      ) : (
        <Text
          style={[styles.buttonLabel, variant === "secondary" && styles.buttonLabelSecondary]}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export type BannerTone = "info" | "error" | "warning" | "success";

export function Banner({
  tone,
  message,
  action,
  testID,
}: {
  tone: BannerTone;
  message: string;
  action?: { label: string; onPress: () => void };
  testID?: string;
}) {
  return (
    <View
      testID={testID}
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      style={[styles.banner, bannerTone(tone)]}
    >
      <Text style={styles.bannerText}>{message}</Text>
      {action ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={action.label}
          onPress={action.onPress}
          style={styles.bannerAction}
        >
          <Text style={styles.bannerActionText}>{action.label}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function bannerTone(tone: BannerTone): ViewStyle {
  switch (tone) {
    case "error":
      return { borderLeftColor: palette.danger };
    case "warning":
      return { borderLeftColor: palette.warning };
    case "success":
      return { borderLeftColor: palette.success };
    case "info":
    default:
      return { borderLeftColor: palette.accent };
  }
}

export function Loading({ label, testID }: { label: string; testID?: string }) {
  return (
    <View testID={testID} accessibilityRole="progressbar" accessibilityLabel={label} style={styles.centred}>
      <ActivityIndicator size="large" color={palette.accent} />
      <Text style={styles.body}>{label}</Text>
    </View>
  );
}

export function EmptyState({
  title,
  detail,
  action,
  testID,
}: {
  title: string;
  detail: string;
  action?: { label: string; onPress: () => void };
  testID?: string;
}) {
  return (
    <View testID={testID} style={styles.centred}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={[styles.body, styles.bodyMuted]}>{detail}</Text>
      {action ? <Button label={action.label} onPress={action.onPress} variant="secondary" /> : null}
    </View>
  );
}

export function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={[styles.body, strong === true && styles.rowStrong]}>{label}</Text>
      <Text style={[styles.body, strong === true && styles.rowStrong]}>{value}</Text>
    </View>
  );
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: palette.background },
  screenContent: { padding: 18, gap: 14, paddingBottom: 48 },
  heading: { fontSize: 26, fontWeight: "800", color: palette.text, letterSpacing: 0.5 },
  body: { fontSize: 15, lineHeight: 22, color: palette.text },
  bodyMuted: { color: palette.textMuted },
  card: {
    backgroundColor: palette.surface,
    borderColor: palette.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: 16,
    gap: 8,
  },
  button: {
    backgroundColor: palette.accent,
    paddingVertical: 13,
    paddingHorizontal: 18,
    borderRadius: 8,
    alignItems: "center",
    minHeight: 46,
    justifyContent: "center",
  },
  buttonSecondary: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: palette.accent,
  },
  buttonDanger: { backgroundColor: palette.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.8 },
  buttonLabel: { color: palette.accentText, fontWeight: "700", fontSize: 15 },
  buttonLabelSecondary: { color: palette.accent },
  banner: {
    backgroundColor: palette.surface,
    borderLeftWidth: 4,
    borderRadius: 6,
    padding: 14,
    gap: 8,
  },
  bannerText: { fontSize: 14, lineHeight: 20, color: palette.text },
  bannerAction: { alignSelf: "flex-start" },
  bannerActionText: { color: palette.accent, fontWeight: "700", fontSize: 14 },
  centred: { alignItems: "center", gap: 12, paddingVertical: 40 },
  emptyTitle: { fontSize: 18, fontWeight: "700", color: palette.text },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  rowStrong: { fontWeight: "800" },
});
