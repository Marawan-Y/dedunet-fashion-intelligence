import { StatusBar } from "expo-status-bar";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, SafeAreaView, StyleSheet, Text, View } from "react-native";

type Product = {
  id: string;
  name: string;
  collection: string;
  fibre_composition: string;
  made_in: string;
  // Money contract SB-AR-B3-003: authoritative amount is integer minor units.
  price_minor_units: number;
  currency: string;
};

const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "http://10.0.2.2:18000";

const MINOR_UNIT_EXPONENTS: Record<string, number> = { EUR: 2 };
const CURRENCY_SYMBOLS: Record<string, string> = { EUR: "€" };

/** Render integer minor units without any floating-point money arithmetic. */
function formatMinorUnits(minorUnits: number, currency: string): string {
  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined || !Number.isInteger(minorUnits)) {
    return `${minorUnits} ${currency}`;
  }
  const sign = minorUnits < 0 ? "-" : "";
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${major}.${minor}`;
}

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/products`)
      .then((response) => {
        if (!response.ok) throw new Error(`API ${response.status}`);
        return response.json();
      })
      .then(setProducts)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Text style={styles.eyebrow}>EGYPTIAN COTTON / EASTERN DESIGN</Text>
        <Text style={styles.title}>Origin</Text>
        <Text style={styles.subtitle}>Mobile proof of concept connected to the same catalog API.</Text>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {!error && products.length === 0 ? <ActivityIndicator /> : null}
      <FlatList
        data={products}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.eyebrow}>{item.collection}</Text>
            <Text style={styles.productName}>{item.name}</Text>
            <Text>{item.fibre_composition} · Made in {item.made_in}</Text>
            <Text style={styles.price}>{formatMinorUnits(item.price_minor_units, item.currency)}</Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f4f0e8" },
  header: { padding: 24, gap: 6 },
  eyebrow: { fontSize: 11, letterSpacing: 1.5, fontWeight: "700" },
  title: { fontSize: 44, fontWeight: "800", letterSpacing: 4, textTransform: "uppercase" },
  subtitle: { fontSize: 16, lineHeight: 22 },
  list: { padding: 18, gap: 14 },
  card: { padding: 20, backgroundColor: "white", gap: 8 },
  productName: { fontSize: 22, fontWeight: "700" },
  price: { fontSize: 18, fontWeight: "800" },
  error: { margin: 20, color: "#8b1e1e" }
});
