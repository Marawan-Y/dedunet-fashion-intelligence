/**
 * Bag: lines, quantity changes, removal and the server-priced total.
 *
 * The displayed total always comes from `GET /cart/quote`. The client computes line totals
 * for display only and never sums them into a payable amount — VAT is a component extracted
 * from the gross, not an addend, so a client-side total would disagree with the server's.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Text, View } from "react-native";

import { describeFailure } from "../api/client";
import { quoteCart } from "../api/commerce";
import type { CartLine, PriceBreakdown } from "../api/types";
import { formatMinorUnits, lineTotalMinorUnits } from "../money";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, EmptyState, Heading, Loading, Row, Screen, styles } from "../ui";

export function CartScreen({ app }: { app: AppState }) {
  const { apiBase, cartToken, cart, refreshCart, setLineQuantity, removeLine, navigate, session } = app;

  const [loading, setLoading] = useState(true);
  const [quote, setQuote] = useState<PriceBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyVariant, setBusyVariant] = useState<number | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await refreshCart();
      setQuote(await quoteCart(apiBase, cartToken));
    } catch (failure) {
      setError(describeFailure(failure));
    } finally {
      setLoading(false);
    }
  }, [apiBase, cartToken, refreshCart]);

  useEffect(() => {
    void reload();
    // Intentionally once per mount: reload() changes identity with the cart token, which
    // would otherwise re-run this on every token refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const changeQuantity = useCallback(
    async (line: CartLine, desired: number) => {
      setBusyVariant(line.variant_id);
      setError(null);
      try {
        await setLineQuantity(line.variant_id, line.quantity, desired);
        setQuote(await quoteCart(apiBase, cartToken));
      } catch (failure) {
        setError(describeFailure(failure));
      } finally {
        setBusyVariant(null);
      }
    },
    [apiBase, cartToken, setLineQuantity]
  );

  const drop = useCallback(
    async (line: CartLine) => {
      setBusyVariant(line.variant_id);
      setError(null);
      try {
        await removeLine(line.variant_id);
        setQuote(await quoteCart(apiBase, cartToken));
      } catch (failure) {
        setError(describeFailure(failure));
      } finally {
        setBusyVariant(null);
      }
    },
    [apiBase, cartToken, removeLine]
  );

  if (loading) {
    return (
      <Screen>
        <Loading label="Loading your bag…" testID="cart-loading" />
      </Screen>
    );
  }

  const lines = cart?.lines ?? [];

  return (
    <Screen>
      <Heading>Your bag</Heading>

      {error !== null ? (
        <Banner
          testID="cart-error"
          tone="error"
          message={error}
          action={{ label: "Try again", onPress: () => void reload() }}
        />
      ) : null}

      {lines.length === 0 ? (
        <EmptyState
          testID="cart-empty"
          title="Your bag is empty"
          detail="Add something from the collection to see it here."
          action={{ label: "Browse the collection", onPress: () => navigate({ name: "catalog" }) }}
        />
      ) : null}

      {lines.map((line) => (
        <LineCard
          key={line.variant_id}
          line={line}
          currency={quote?.currency ?? "EUR"}
          busy={busyVariant === line.variant_id}
          onIncrease={() => void changeQuantity(line, line.quantity + 1)}
          onDecrease={() => void changeQuantity(line, line.quantity - 1)}
          onRemove={() => void drop(line)}
        />
      ))}

      {quote !== null ? (
        <Card>
          <Row label="Subtotal" value={formatMinorUnits(quote.subtotal_minor_units, quote.currency) ?? "—"} />
          {quote.discount_minor_units > 0 ? (
            <Row
              label={quote.promotion_code !== "" ? `Discount (${quote.promotion_code})` : "Discount"}
              value={`-${formatMinorUnits(quote.discount_minor_units, quote.currency) ?? "—"}`}
            />
          ) : null}
          <Row label="Shipping" value={formatMinorUnits(quote.shipping_minor_units, quote.currency) ?? "—"} />
          <Row label="Total" value={formatMinorUnits(quote.total_minor_units, quote.currency) ?? "—"} strong />
          {/* VAT is contained within the total, never added to it. */}
          <Body muted>
            Includes {formatMinorUnits(quote.tax_minor_units, quote.currency) ?? "—"} VAT
          </Body>
        </Card>
      ) : null}

      {lines.length > 0 ? (
        <Button
          testID="cart-checkout"
          label={session === null ? "Sign in to check out" : "Continue to checkout"}
          onPress={() => navigate({ name: session === null ? "account" : "checkout" })}
        />
      ) : null}

      <Button label="Back to catalogue" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}

function LineCard({
  line,
  currency,
  busy,
  onIncrease,
  onDecrease,
  onRemove,
}: {
  line: CartLine;
  currency: string;
  busy: boolean;
  onIncrease: () => void;
  onDecrease: () => void;
  onRemove: () => void;
}) {
  // Display only. The payable amount is always the server's quote.
  let lineTotal: string | null = null;
  try {
    lineTotal = formatMinorUnits(
      lineTotalMinorUnits(line.unit_price_minor_units, line.quantity),
      currency
    );
  } catch {
    lineTotal = null;
  }

  return (
    <Card>
      <Text style={styles.rowStrong}>{line.product_name}</Text>
      <Text style={[styles.body, styles.bodyMuted]}>
        {line.size} · {line.color} · {line.sku}
      </Text>
      <View style={styles.row}>
        <Text style={styles.body}>
          {formatMinorUnits(line.unit_price_minor_units, currency) ?? "—"} × {line.quantity}
        </Text>
        <Text style={styles.rowStrong}>{lineTotal ?? "—"}</Text>
      </View>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <View style={{ flex: 1 }}>
          <Button
            testID={`line-decrease-${line.variant_id}`}
            label="−"
            variant="secondary"
            busy={busy}
            onPress={onDecrease}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Button
            testID={`line-increase-${line.variant_id}`}
            label="+"
            variant="secondary"
            busy={busy}
            onPress={onIncrease}
          />
        </View>
        <View style={{ flex: 2 }}>
          <Button
            testID={`line-remove-${line.variant_id}`}
            label="Remove"
            variant="danger"
            busy={busy}
            onPress={onRemove}
          />
        </View>
      </View>
    </Card>
  );
}
