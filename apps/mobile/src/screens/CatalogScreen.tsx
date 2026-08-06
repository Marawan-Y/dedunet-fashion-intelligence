/**
 * Catalog list.
 *
 * Renders four distinct states — loading, failed, empty, ready — from the `CatalogState`
 * union. "Empty" and "failed" are separate screens on purpose: an empty catalog is a
 * normal condition of a staging environment running `SEED_DEMO_DATA=0`, and showing an
 * error there would send an operator hunting a fault that does not exist.
 */

import React from "react";
import { Pressable, Text, View } from "react-native";

import { describeFailure } from "../api/client";
import type { Product } from "../api/types";
import { BRAND, SANDBOX_NOTICE } from "../brand";
import { formatMinorUnits, lowestPriceMinorUnits } from "../money";
import type { AppState } from "../store";
import { Banner, Body, Card, EmptyState, Heading, Loading, Screen, styles } from "../ui";

export function CatalogScreen({ app }: { app: AppState }) {
  const { catalog, loadCatalog, navigate } = app;

  return (
    <Screen>
      <Heading>{BRAND.name}</Heading>
      <Body muted>{BRAND.tagline}</Body>
      <Banner tone="warning" message={SANDBOX_NOTICE} testID="sandbox-notice" />

      {catalog.status === "loading" || catalog.status === "idle" ? (
        <Loading label="Loading the collection…" testID="catalog-loading" />
      ) : null}

      {catalog.status === "error" ? (
        <Banner
          testID="catalog-error"
          tone="error"
          message={describeFailure(catalog.error)}
          action={{ label: "Try again", onPress: () => void loadCatalog() }}
        />
      ) : null}

      {catalog.status === "ready" && catalog.products.length === 0 ? (
        <EmptyState
          testID="catalog-empty"
          title="No products yet"
          detail="This environment has no catalogue loaded. That is expected on a staging build seeded with no demo data."
          action={{ label: "Refresh", onPress: () => void loadCatalog() }}
        />
      ) : null}

      {catalog.status === "ready" && catalog.products.length > 0
        ? catalog.products.map((product) => (
            <ProductCard
              key={product.slug}
              product={product}
              onPress={() => navigate({ name: "product", slug: product.slug })}
            />
          ))
        : null}
    </Screen>
  );
}

function ProductCard({ product, onPress }: { product: Product; onPress: () => void }) {
  // A product with no variants has no price. `lowestPriceMinorUnits` returns null rather
  // than Math.min()'s Infinity, so nothing numeric can reach the formatter.
  const lowest = lowestPriceMinorUnits(product.variants);
  const price = lowest === null ? null : formatMinorUnits(lowest, product.currency);
  const purchasable = product.variants.length > 0;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${product.name}. ${price ?? "Price unavailable"}`}
      onPress={onPress}
      testID={`product-card-${product.slug}`}
    >
      <Card>
        {product.collection !== "" ? (
          <Text style={[styles.body, styles.bodyMuted]}>{product.collection}</Text>
        ) : null}
        <Text style={styles.emptyTitle}>{product.name}</Text>
        <View style={styles.row}>
          <Text style={styles.rowStrong}>
            {price === null ? "Price unavailable" : `From ${price}`}
          </Text>
          {!purchasable ? (
            <Text style={[styles.body, { color: BRAND.palette.warning }]}>Not available</Text>
          ) : null}
        </View>
      </Card>
    </Pressable>
  );
}
