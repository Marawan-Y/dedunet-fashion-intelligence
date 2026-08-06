/**
 * Product detail and variant selection.
 *
 * Fetches by slug rather than reusing the list payload, so a deep link works and a stale
 * list cannot show a stock figure that has since changed.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { ApiError, describeFailure } from "../api/client";
import { getProduct } from "../api/commerce";
import type { Product, Variant } from "../api/types";
import { BRAND } from "../brand";
import { formatMinorUnits } from "../money";
import { materialLabel, originStatement } from "../origin";
import type { AppState } from "../store";
import { Gallery } from "../components/Gallery";
import { Banner, Body, Button, Card, Heading, Loading, Screen, styles } from "../ui";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; product: Product }
  | { status: "error"; error: ApiError };

export function ProductScreen({ app, slug }: { app: AppState; slug: string }) {
  const { apiBase, navigate, addToCart, handleFailure } = app;
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const product = await getProduct(apiBase, slug);
      setState({ status: "ready", product });
      // Preselect the first variant that can actually be bought.
      const firstAvailable = product.variants.find((v) => v.available > 0);
      setSelectedVariantId(firstAvailable?.id ?? product.variants[0]?.id ?? null);
    } catch (error) {
      setState({ status: "error", error: handleFailure(error) });
    }
  }, [apiBase, slug, handleFailure]);

  useEffect(() => {
    void load();
  }, [load]);

  const onAdd = useCallback(async () => {
    if (selectedVariantId === null) return;
    setBusy(true);
    setMessage(null);
    try {
      await addToCart(selectedVariantId, 1);
      setMessage({ tone: "success", text: "Added to your bag." });
    } catch (error) {
      setMessage({ tone: "error", text: describeFailure(error) });
    } finally {
      setBusy(false);
    }
  }, [selectedVariantId, addToCart]);

  if (state.status === "loading") {
    return (
      <Screen>
        <Loading label="Loading product…" testID="product-loading" />
      </Screen>
    );
  }

  if (state.status === "error") {
    return (
      <Screen>
        <Banner
          testID="product-error"
          tone="error"
          message={describeFailure(state.error)}
          action={{ label: "Try again", onPress: () => void load() }}
        />
        <Button label="Back to catalogue" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
      </Screen>
    );
  }

  const { product } = state;
  const origin = originStatement(product);
  const material = materialLabel(product.material);
  // `sellable === false` is a deliberate refusal. `undefined` means the legacy API, which
  // predates the flag, so it must not be treated as "not sellable".
  const previewOnly = product.sellable === false;
  const selected = product.variants.find((v) => v.id === selectedVariantId) ?? null;
  const price = selected ? formatMinorUnits(selected.price_minor_units, product.currency) : null;

  return (
    <Screen>
      <Heading>{product.name}</Heading>
      {product.collection !== "" ? <Body muted>{product.collection}</Body> : null}
      {product.description !== "" ? <Body>{product.description}</Body> : null}

      {/*
        Origin and material are rendered only through the gated helpers. The removed PoC
        printed `Made in {made_in}` straight from the payload, which is the claim the
        programme is explicitly not permitted to make.
      */}
      {material !== null ? <Body muted>{material}</Body> : null}
      {origin !== null ? <Body muted>{origin}</Body> : null}

      <Gallery product={product} apiBase={apiBase} />

      {previewOnly ? (
        <Banner
          testID="product-preview-only"
          tone="warning"
          message={
            "Preview only — this piece is not available to buy. Imagery is concept artwork, " +
            "not product photography."
          }
        />
      ) : null}

      {product.variants.length === 0 ? (
        <Banner
          testID="product-no-variants"
          tone="warning"
          message="This product has no purchasable options at the moment."
        />
      ) : (
        <Card>
          <Text style={styles.rowStrong}>Choose a size</Text>
          <View style={{ gap: 8 }}>
            {product.variants.map((variant) => (
              <VariantRow
                key={variant.id}
                variant={variant}
                currency={product.currency}
                selected={variant.id === selectedVariantId}
                onSelect={() => setSelectedVariantId(variant.id)}
              />
            ))}
          </View>
        </Card>
      )}

      {message !== null ? (
        <Banner
          testID="product-message"
          tone={message.tone === "error" ? "error" : "success"}
          message={message.text}
          {...(message.tone === "success"
            ? { action: { label: "View bag", onPress: () => navigate({ name: "cart" }) } }
            : {})}
        />
      ) : null}

      {selected !== null ? (
        <Button
          testID="product-add"
          label={
            previewOnly
              ? "Not available to buy"
              : selected.available <= 0
                ? "Out of stock"
                : price === null
                  ? "Add to bag"
                  : `Add to bag — ${price}`
          }
          // The server refuses this anyway. Disabling here means the customer is not
          // invited to press a button whose only outcome is a rejection.
          disabled={previewOnly || selected.available <= 0}
          busy={busy}
          onPress={() => void onAdd()}
        />
      ) : null}

      <Button label="Back to catalogue" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}

function VariantRow({
  variant,
  currency,
  selected,
  onSelect,
}: {
  variant: Variant;
  currency: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const price = formatMinorUnits(variant.price_minor_units, currency);
  const soldOut = variant.available <= 0;

  return (
    <Pressable
      testID={`variant-${variant.id}`}
      accessibilityRole="radio"
      accessibilityState={{ selected, disabled: soldOut }}
      accessibilityLabel={`${variant.size} ${variant.color}. ${price ?? "price unavailable"}. ${
        soldOut ? "Out of stock" : `${variant.available} available`
      }`}
      onPress={onSelect}
      style={{
        borderWidth: selected ? 2 : 1,
        borderColor: selected ? BRAND.palette.accent : BRAND.palette.border,
        borderRadius: 8,
        padding: 12,
        opacity: soldOut ? 0.55 : 1,
      }}
    >
      <View style={styles.row}>
        <Text style={styles.body}>
          {variant.size} · {variant.color}
        </Text>
        <Text style={styles.rowStrong}>{price ?? "—"}</Text>
      </View>
      <Text style={[styles.body, styles.bodyMuted]}>
        {soldOut ? "Out of stock" : `${variant.available} available`}
      </Text>
    </Pressable>
  );
}
