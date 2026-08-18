/**
 * Order history and order detail.
 *
 * Both live here because they share the same load-and-fail shape and the same money
 * rendering, and splitting them would duplicate that without separating any concern.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Pressable, Text } from "react-native";

import { ApiError, describeFailure } from "../api/client";
import { getOrder, listOrders } from "../api/commerce";
import type { Order } from "../api/types";
import { ordersEmptyDetail } from "../brand";
import { formatMinorUnits } from "../money";
import type { AppState } from "../store";
import { Banner, Body, Button, Card, EmptyState, Heading, Loading, Row, Screen, styles } from "../ui";

type ListState =
  | { status: "loading" }
  | { status: "ready"; orders: Order[] }
  | { status: "error"; error: ApiError };

export function OrdersScreen({ app }: { app: AppState }) {
  const { apiBase, session, navigate, handleFailure, commerceMode } = app;
  const [state, setState] = useState<ListState>({ status: "loading" });

  const load = useCallback(async () => {
    if (session === null) return;
    setState({ status: "loading" });
    try {
      setState({ status: "ready", orders: await listOrders(apiBase, session.accessToken) });
    } catch (failure) {
      setState({ status: "error", error: handleFailure(failure) });
    }
  }, [apiBase, session, handleFailure]);

  useEffect(() => {
    void load();
  }, [load]);

  if (session === null) {
    return (
      <Screen>
        <Heading>Your orders</Heading>
        <Banner tone="warning" message="Please sign in to see your orders." />
        <Button label="Go to account" onPress={() => navigate({ name: "account" })} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Heading>Your orders</Heading>

      {state.status === "loading" ? <Loading label="Loading orders…" testID="orders-loading" /> : null}

      {state.status === "error" ? (
        <Banner
          testID="orders-error"
          tone="error"
          message={describeFailure(state.error)}
          action={{ label: "Try again", onPress: () => void load() }}
        />
      ) : null}

      {state.status === "ready" && state.orders.length === 0 ? (
        <EmptyState
          testID="orders-empty"
          title="No orders yet"
          /* Mode-derived. Preview mode must not invite a purchase the server will refuse. */
          detail={ordersEmptyDetail(commerceMode)}
          action={{ label: "Browse the collection", onPress: () => navigate({ name: "catalog" }) }}
        />
      ) : null}

      {state.status === "ready"
        ? state.orders.map((order) => (
            <Pressable
              key={order.order_number}
              testID={`order-${order.order_number}`}
              accessibilityRole="button"
              accessibilityLabel={`Order ${order.order_number}, ${order.status}`}
              onPress={() => navigate({ name: "orderDetail", orderNumber: order.order_number })}
            >
              <Card>
                <Text style={styles.rowStrong}>{order.order_number}</Text>
                <Row
                  label={order.status}
                  value={formatMinorUnits(order.total_minor_units, order.currency) ?? "—"}
                />
                {order.placed_at !== null ? <Body muted>{order.placed_at}</Body> : null}
              </Card>
            </Pressable>
          ))
        : null}

      <Button label="Back to catalogue" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}

type DetailState =
  | { status: "loading" }
  | { status: "ready"; order: Order }
  | { status: "error"; error: ApiError };

/**
 * Settled states that are NOT a successful purchase.
 *
 * Rendering these in the success tone would tell a customer their order went through when
 * the payment was declined.
 */
const SETTLED_BAD = new Set(["cancelled", "canceled", "refunded", "payment_failed"]);

export function OrderDetailScreen({ app, orderNumber }: { app: AppState; orderNumber: string }) {
  const { apiBase, session, navigate, handleFailure, lastOrder, lastOrderReplayed } = app;

  // A checkout that just completed already holds the order, so the confirmation renders
  // without a second round trip -- and still renders if that round trip would fail.
  const [state, setState] = useState<DetailState>(
    lastOrder !== null && lastOrder.order_number === orderNumber
      ? { status: "ready", order: lastOrder }
      : { status: "loading" }
  );

  const load = useCallback(async () => {
    if (session === null) return;
    setState({ status: "loading" });
    try {
      setState({ status: "ready", order: await getOrder(apiBase, session.accessToken, orderNumber) });
    } catch (failure) {
      setState({ status: "error", error: handleFailure(failure) });
    }
  }, [apiBase, session, orderNumber, handleFailure]);

  useEffect(() => {
    if (state.status === "ready") return;
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  if (session === null) {
    return (
      <Screen>
        <Banner tone="warning" message="Please sign in to see this order." />
        <Button label="Go to account" onPress={() => navigate({ name: "account" })} />
      </Screen>
    );
  }

  if (state.status === "loading") {
    return (
      <Screen>
        <Loading label="Loading order…" testID="order-loading" />
      </Screen>
    );
  }

  if (state.status === "error") {
    return (
      <Screen>
        <Banner
          testID="order-error"
          tone="error"
          message={describeFailure(state.error)}
          action={{ label: "Try again", onPress: () => void load() }}
        />
        <Button label="Your orders" variant="secondary" onPress={() => navigate({ name: "orders" })} />
      </Screen>
    );
  }

  const { order } = state;
  // Only claim a replay for the order the last checkout actually returned.
  const isReplay = lastOrderReplayed && lastOrder?.order_number === order.order_number;

  return (
    <Screen>
      <Heading>Order {order.order_number}</Heading>

      {/*
        Three things are deliberately distinguished here, because conflating them is how a
        customer concludes an order was placed when it was not:
          - a REPLAY returned an order that already existed;
          - the order's real status, which may be `cancelled` after a declined payment;
          - the fact that this is sandbox commerce either way.
      */}
      {isReplay ? (
        <Banner
          testID="order-replayed"
          tone="warning"
          message="This order already existed — the request was replayed and no new order was placed."
        />
      ) : null}
      <Banner
        testID="order-confirmed"
        tone={SETTLED_BAD.has(order.status) ? "warning" : "success"}
        message={`Sandbox order status: ${order.status}. No card was charged and nothing will ship.`}
      />

      {order.lines.map((line, index) => (
        <Card key={`${line.sku}-${index}`}>
          <Text style={styles.rowStrong}>{line.product_name}</Text>
          <Body muted>
            {line.size} · {line.color} · {line.sku}
          </Body>
          <Row
            label={`${formatMinorUnits(line.unit_price_minor_units, order.currency) ?? "—"} × ${line.quantity}`}
            value={formatMinorUnits(line.line_total_minor_units, order.currency) ?? "—"}
          />
        </Card>
      ))}

      <Card>
        <Row label="Subtotal" value={formatMinorUnits(order.subtotal_minor_units, order.currency) ?? "—"} />
        {order.discount_minor_units > 0 ? (
          <Row
            label="Discount"
            value={`-${formatMinorUnits(order.discount_minor_units, order.currency) ?? "—"}`}
          />
        ) : null}
        <Row label="Shipping" value={formatMinorUnits(order.shipping_minor_units, order.currency) ?? "—"} />
        <Row label="Total" value={formatMinorUnits(order.total_minor_units, order.currency) ?? "—"} strong />
        <Body muted>Includes {formatMinorUnits(order.tax_minor_units, order.currency) ?? "—"} VAT</Body>
      </Card>

      {order.shipments.length > 0 ? (
        <Card>
          <Text style={styles.rowStrong}>Shipments</Text>
          {order.shipments.map((shipment, index) => (
            <Row
              key={`${shipment.tracking_number}-${index}`}
              label={`${shipment.carrier} · ${shipment.status}`}
              value={shipment.tracking_number}
            />
          ))}
          {/* Tracking numbers are generated locally by a mock carrier. */}
          <Body muted>Mock carrier — this tracking number is not real.</Body>
        </Card>
      ) : null}

      <Button label="Your orders" onPress={() => navigate({ name: "orders" })} />
      <Button label="Back to catalogue" variant="secondary" onPress={() => navigate({ name: "catalog" })} />
    </Screen>
  );
}
