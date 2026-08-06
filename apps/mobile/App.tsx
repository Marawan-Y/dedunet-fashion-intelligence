/**
 * Application root: boot, chrome and routing.
 *
 * Routing is a typed union switched here rather than a navigation library. The flows are
 * linear and few, and every added dependency in an Expo project is another entry in the
 * SDK compatibility matrix that has to keep resolving. This is a deliberate trade-off
 * recorded in the Workstream F evidence: it costs deep links and gesture-based back
 * navigation, which nothing here needs yet.
 */

import { StatusBar } from "expo-status-bar";
import React from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";

import { BRAND } from "./src/brand";
import { AccountScreen } from "./src/screens/AccountScreen";
import { CartScreen } from "./src/screens/CartScreen";
import { CatalogScreen } from "./src/screens/CatalogScreen";
import { CheckoutScreen } from "./src/screens/CheckoutScreen";
import { OrderDetailScreen, OrdersScreen } from "./src/screens/OrdersScreen";
import { ProductScreen } from "./src/screens/ProductScreen";
import { SettingsScreen } from "./src/screens/SettingsScreen";
import { useAppStore, type Route } from "./src/store";
import { Loading } from "./src/ui";

const palette = BRAND.palette;

export default function App() {
  const app = useAppStore();

  // Boot restores the saved session, cart token and API base. Rendering the catalogue
  // first would fire a request against the default base and then a second against the
  // restored one, which looks like a flicker and doubles the rate-limit cost.
  if (!app.booted) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="dark" />
        <Loading label="Starting…" testID="app-booting" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <View style={styles.content}>{renderRoute(app.route, app)}</View>
      <TabBar app={app} />
    </SafeAreaView>
  );
}

function renderRoute(route: Route, app: ReturnType<typeof useAppStore>) {
  switch (route.name) {
    case "catalog":
      return <CatalogScreen app={app} />;
    case "product":
      return <ProductScreen app={app} slug={route.slug} />;
    case "cart":
      return <CartScreen app={app} />;
    case "checkout":
      return <CheckoutScreen app={app} />;
    case "orders":
      return <OrdersScreen app={app} />;
    case "orderDetail":
      return <OrderDetailScreen app={app} orderNumber={route.orderNumber} />;
    case "account":
      return <AccountScreen app={app} />;
    case "settings":
      return <SettingsScreen app={app} />;
    default:
      return <CatalogScreen app={app} />;
  }
}

function TabBar({ app }: { app: ReturnType<typeof useAppStore> }) {
  const { route, navigate, cartCount, session } = app;

  const tabs: { key: Route["name"]; route: Route; label: string; badge?: number }[] = [
    { key: "catalog", route: { name: "catalog" }, label: "Shop" },
    { key: "cart", route: { name: "cart" }, label: "Bag", badge: cartCount },
    { key: "orders", route: { name: "orders" }, label: "Orders" },
    { key: "account", route: { name: "account" }, label: session === null ? "Sign in" : "Account" },
  ];

  return (
    <View style={styles.tabBar} accessibilityRole="tablist">
      {tabs.map((tab) => {
        const active = route.name === tab.key;
        const badge = tab.badge !== undefined && tab.badge > 0 ? ` (${tab.badge})` : "";
        return (
          <Pressable
            key={tab.key}
            testID={`tab-${tab.key}`}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={`${tab.label}${badge}`}
            onPress={() => navigate(tab.route)}
            style={styles.tab}
          >
            <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>
              {tab.label}
              {badge}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: palette.background },
  content: { flex: 1 },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: palette.border,
    backgroundColor: palette.surface,
  },
  tab: { flex: 1, paddingVertical: 14, alignItems: "center", justifyContent: "center", minHeight: 52 },
  tabLabel: { fontSize: 13, fontWeight: "600", color: palette.textMuted },
  tabLabelActive: { color: palette.accent, fontWeight: "800" },
});
