import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchCommerceMode } from "../api/endpoints";
import type { CommerceModeDisclosure } from "../api/types";

/* The deployment's commerce mode.
 *
 * Asked ONCE at boot and shared, because it is a property of the deployment rather than of
 * the page being viewed. Two surfaces genuinely need the answer — the purchase gate on a
 * product and the empty order history — and they read it from here rather than each
 * issuing their own request.
 *
 * `null` is a real third state meaning "not known yet", never a silent fallback to a
 * permissive one. An unresolved mode does not refuse on its own and does not permit on its
 * own; the product gate below decides what to do with the uncertainty, and it decides in
 * the safe direction.
 */

interface CommerceModeValue {
  disclosure: CommerceModeDisclosure | null;
  /** True only once the API has actually answered. */
  resolved: boolean;
}

const CommerceModeContext = createContext<CommerceModeValue>({
  disclosure: null,
  resolved: false,
});

export function CommerceModeProvider({ children }: { children: ReactNode }) {
  const [disclosure, setDisclosure] = useState<CommerceModeDisclosure | null>(null);
  const [resolved, setResolved] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    fetchCommerceMode(controller.signal)
      .then((mode) => {
        setDisclosure(mode);
        setResolved(true);
      })
      .catch(() => {
        /* Deliberately swallowed, and deliberately NOT resolved.
         *
         * If the mode cannot be read, the page keeps the disclosure it shipped with —
         * copy that is true in every permitted mode — rather than adopting a guess. An
         * unreachable API must never be the reason a purchase becomes available. */
        if (!controller.signal.aborted) setResolved(false);
      });

    return () => controller.abort();
  }, []);

  const value = useMemo(() => ({ disclosure, resolved }), [disclosure, resolved]);

  return <CommerceModeContext.Provider value={value}>{children}</CommerceModeContext.Provider>;
}

export function useCommerceMode(): CommerceModeValue {
  return useContext(CommerceModeContext);
}

/** Why a purchase is refused. The REASON, not a boolean: the two refusals are different
 *  facts about different things, and collapsing them loses the one the customer needs. */
export type PurchaseRefusal = "mode" | "product" | null;

/**
 * Mirror of the server's `assert_purchasable`, both gates and in its order.
 *
 * The server refuses on two independent gates and this mirrors both, because a client that
 * checks only one offers a purchase the server will refuse — which is the exact defect this
 * guard was written to close:
 *
 *   MODE     brand preview refuses every purchase, whatever the product says
 *   PRODUCT  a non-sellable product is refused in any mode
 *
 * An unresolved mode does not refuse on its own. The mode gate cannot be evaluated yet, so
 * it abstains and the product gate still applies — which for every DEDUNET prototype is
 * itself a refusal.
 */
export function purchaseRefusal(
  sellable: boolean | undefined,
  mode: CommerceModeDisclosure | null,
): PurchaseRefusal {
  if (mode && !mode.purchasable) return "mode";
  /* `false` is a deliberate refusal. `undefined` is the legacy payload shape, which
     carries no opinion and must not be read as one. */
  if (sellable === false) return "product";
  return null;
}

export function refusalText(refusal: PurchaseRefusal): string {
  if (refusal === "mode") {
    return "This catalogue is in preview. Nothing here is available to buy.";
  }
  if (refusal === "product") {
    return "This piece is a prototype. It has never been produced for sale.";
  }
  return "";
}
