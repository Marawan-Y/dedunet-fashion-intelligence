import { useCallback, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
} from "../../components/primitives";
import { EmptyState, ErrorState, SkeletonGrid } from "../../components/States";
import { fetchOrders } from "../../api/endpoints";
import { session } from "../../api/client";
import { useAsync } from "../../lib/useAsync";
import { useCommerceMode } from "../../app/CommerceMode";
import type { CustomerOrder } from "../../api/types";

/**
 * Order history.
 *
 * THE EMPTY COPY IS MODE-DERIVED AND THAT IS ACCEPTED BEHAVIOUR. Three variants, no shared
 * sentence between them.
 *
 * "No orders yet — why not browse the collection?" is an invitation, and in
 * BRAND_PREVIEW_MODE it invites a customer to do something the platform will refuse. The
 * empty state has to say why it is empty, and the reason differs per mode. An unresolved
 * mode gets its own sentence rather than borrowing whichever of the other two is more
 * flattering.
 */
export default function OrdersPage() {
  const { disclosure, resolved } = useCommerceMode();

  const run = useCallback((signal: AbortSignal) => fetchOrders(signal), []);
  const orders = useAsync<CustomerOrder[]>(run, []);

  useEffect(() => {
    document.title = "Orders — DEDUNET";
  }, []);

  /* Signed out, there is no order history to show and no useful error to raise. Sending
     the visitor to sign in is the answer, and `replace` keeps the back button working. */
  if (!session.signedIn) return <Navigate to="/account" replace />;

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Your account</Eyebrow>
            <h1>Orders</h1>
            <Lede>Everything you have ordered from DEDUNET.</Lede>
          </Stack>

          {orders.status === "loading" ? <SkeletonGrid count={2} label="Loading orders" /> : null}

          {orders.status === "error" ? (
            <ErrorState error={orders.error} onRetry={orders.retry} />
          ) : null}

          {orders.status === "success" && (orders.data ?? []).length === 0 ? (
            <EmptyState
              title="No orders yet."
              body={emptyReason(disclosure?.purchasable ?? null, resolved)}
              action={
                <ButtonLink to="/discover" variant="secondary">
                  Discover the capsule
                </ButtonLink>
              }
            />
          ) : null}

          {orders.status === "success" && (orders.data ?? []).length > 0 ? (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {(orders.data ?? []).map((order) => (
                <li key={order.order_number}>
                  <strong>{order.order_number}</strong> — {order.status}
                </li>
              ))}
            </ul>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}

/**
 * Why the order history is empty.
 *
 * Three distinct sentences, deliberately sharing no phrasing:
 *
 *   preview     purchasing is refused, so an empty history is the expected state
 *   test        purchasing works but orders are test orders, and saying "sandbox" here
 *               would be false in preview
 *   unresolved  the mode is not known, so neither of the above can be claimed
 */
function emptyReason(purchasable: boolean | null, resolved: boolean): string {
  if (!resolved || purchasable === null) {
    return "DEDUNET could not confirm whether this deployment accepts orders, so there is nothing here to explain yet.";
  }
  if (purchasable === false) {
    return "Purchasing is unavailable while this catalogue is in preview. Nothing here can be ordered, so an empty history is expected rather than a problem.";
  }
  return "Nothing has been ordered from this account. Orders placed in this deployment are test orders and are marked as such.";
}
