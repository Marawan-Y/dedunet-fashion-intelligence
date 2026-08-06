/**
 * Sandbox checkout.
 *
 * The outcome selector is deliberately visible. `SandboxGateway` chooses its result from
 * the payment-method token exactly as a real provider sandbox does, and hiding that behind
 * a "Pay" button would make a prototype look like a payment form. Nothing here collects a
 * card number, because nothing here can charge one.
 *
 * The idempotency key is stable per attempt-and-outcome, so retrying the same attempt
 * replays the original order instead of placing a second one, while changing the outcome
 * counts as a new intent. See the key derivation below.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { describeFailure } from "../api/client";
import { checkout, newIdempotencyKey, quoteCart } from "../api/commerce";
import { SANDBOX_PAYMENT_TOKENS, type PriceBreakdown, type SandboxOutcome } from "../api/types";
import { BRAND, SANDBOX_NOTICE } from "../brand";
import { formatMinorUnits } from "../money";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, Heading, Loading, Row, Screen, styles } from "../ui";

const OUTCOMES: { key: SandboxOutcome; label: string; detail: string }[] = [
  { key: "succeed", label: "Succeeds", detail: "Authorises and places the order" },
  { key: "decline", label: "Declined", detail: "Provider declines — HTTP 402, no charge" },
  { key: "error", label: "Provider error", detail: "Provider unavailable — HTTP 503, retryable" },
];

export function CheckoutScreen({ app }: { app: AppState }) {
  const {
    apiBase,
    cartToken,
    session,
    navigate,
    setLastOrder,
    setLastOrderReplayed,
    handleFailure,
    resetCart,
  } = app;

  const [quote, setQuote] = useState<PriceBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [outcome, setOutcome] = useState<SandboxOutcome>("succeed");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Idempotency key = one nonce per mount, PLUS the chosen outcome.
   *
   * Found by driving the real API: `services.checkout` returns any existing order whose
   * `idempotency_key` matches, with `replayed=true`, regardless of that order's status. A
   * key fixed for the whole screen therefore meant that after a declined attempt, choosing
   * "Succeeds" and pressing pay REPLAYED the cancelled order and presented it as a fresh
   * confirmation. No order was placed and the customer was not told.
   *
   * Including the outcome makes the key represent the INTENT: retrying the same outcome
   * still replays (which is the point of idempotency), while changing the outcome is a new
   * intent and gets a new key.
   */
  const attemptNonce = useMemo(() => newIdempotencyKey(), []);
  const idempotencyKey = `${attemptNonce}-${outcome}`;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const breakdown = await quoteCart(apiBase, cartToken);
        if (!cancelled) setQuote(breakdown);
      } catch (failure) {
        if (!cancelled) setError(describeFailure(handleFailure(failure)));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, cartToken, handleFailure]);

  const pay = useCallback(async () => {
    if (session === null || cartToken === null) return;
    setBusy(true);
    setError(null);
    try {
      const result = await checkout(
        apiBase,
        cartToken,
        session.accessToken,
        SANDBOX_PAYMENT_TOKENS[outcome],
        idempotencyKey
      );
      setLastOrder(result.order);
      setLastOrderReplayed(result.replayed);
      // Checkout consumed this cart. Drop the token so the bag is genuinely empty rather
      // than continuing to show the items that were just bought.
      try {
        await resetCart();
      } catch {
        /* the order is placed; a stale badge must not mask that */
      }
      navigate({ name: "orderDetail", orderNumber: result.order.order_number });
    } catch (failure) {
      setError(describeFailure(handleFailure(failure)));
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    cartToken,
    session,
    outcome,
    idempotencyKey,
    setLastOrder,
    setLastOrderReplayed,
    navigate,
    handleFailure,
    resetCart,
  ]);

  if (session === null) {
    return (
      <Screen>
        <Heading>Checkout</Heading>
        <Banner tone="warning" message="Please sign in before checking out." />
        <Button label="Go to account" onPress={() => navigate({ name: "account" })} />
      </Screen>
    );
  }

  if (loading) {
    return (
      <Screen>
        <Loading label="Pricing your bag…" testID="checkout-loading" />
      </Screen>
    );
  }

  if (quote === null) {
    return (
      <Screen>
        <Heading>Checkout</Heading>
        <Banner tone="warning" message="Your bag is empty." testID="checkout-empty" />
        <Button label="Browse the collection" onPress={() => navigate({ name: "catalog" })} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Heading>Checkout</Heading>
      <Banner tone="warning" message={SANDBOX_NOTICE} />

      <Card>
        <Row label="Subtotal" value={formatMinorUnits(quote.subtotal_minor_units, quote.currency) ?? "—"} />
        {quote.discount_minor_units > 0 ? (
          <Row
            label="Discount"
            value={`-${formatMinorUnits(quote.discount_minor_units, quote.currency) ?? "—"}`}
          />
        ) : null}
        <Row label="Shipping" value={formatMinorUnits(quote.shipping_minor_units, quote.currency) ?? "—"} />
        <Row label="Total" value={formatMinorUnits(quote.total_minor_units, quote.currency) ?? "—"} strong />
        <Body muted>Includes {formatMinorUnits(quote.tax_minor_units, quote.currency) ?? "—"} VAT</Body>
      </Card>

      <Card>
        <Text style={styles.rowStrong}>Sandbox outcome</Text>
        <Body muted>
          Choose what the sandbox payment adapter should do. This replaces a card form because
          no real payment can occur.
        </Body>
        {OUTCOMES.map((option) => (
          <Pressable
            key={option.key}
            testID={`outcome-${option.key}`}
            accessibilityRole="radio"
            accessibilityState={{ selected: outcome === option.key }}
            accessibilityLabel={`${option.label}. ${option.detail}`}
            onPress={() => setOutcome(option.key)}
            style={{
              borderWidth: outcome === option.key ? 2 : 1,
              borderColor: outcome === option.key ? BRAND.palette.accent : BRAND.palette.border,
              borderRadius: 8,
              padding: 12,
            }}
          >
            <Text style={styles.rowStrong}>{option.label}</Text>
            <Text style={[styles.body, styles.bodyMuted]}>{option.detail}</Text>
          </Pressable>
        ))}
      </Card>

      {error !== null ? <Banner testID="checkout-error" tone="error" message={error} /> : null}

      <Button
        testID="checkout-pay"
        label="Place sandbox order"
        busy={busy}
        onPress={() => void pay()}
      />
      <Button label="Back to bag" variant="secondary" onPress={() => navigate({ name: "cart" })} />
    </Screen>
  );
}
