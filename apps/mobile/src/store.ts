/**
 * Application state: API base, session, cart and the current screen.
 *
 * A single hook rather than a state library. The state is small and the flows are linear,
 * so a reducer plus context would add indirection without removing any real problem.
 *
 * The one rule worth stating: a 401 from ANY call clears the session exactly once, through
 * `handleFailure`. Scattering that logic per screen is how an app ends up with a signed-out
 * session that still shows an account page.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "./api/client";
import * as api from "./api/commerce";
import type { Cart, CommerceMode, Order, Product } from "./api/types";
import { defaultApiBase } from "./config";
import * as storage from "./storage";

export type ScreenName =
  | "catalog"
  | "product"
  | "cart"
  | "checkout"
  | "orders"
  | "orderDetail"
  | "account"
  | "settings";

export type Route =
  | { name: "catalog" }
  | { name: "product"; slug: string }
  | { name: "cart" }
  | { name: "checkout" }
  | { name: "orders" }
  | { name: "orderDetail"; orderNumber: string }
  | { name: "account" }
  | { name: "settings" };

export type Session = storage.StoredSession;

/**
 * Catalog is a discriminated union rather than
 * `{ items, loading, error }`. Three booleans admit states that cannot happen
 * ("loading and errored"), and "empty" then becomes indistinguishable from "not loaded",
 * which is the exact bug the brief asks to avoid.
 */
export type CatalogState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; products: Product[] }
  | { status: "error"; error: ApiError };

export type AppState = ReturnType<typeof useAppStore>;

export function useAppStore() {
  const [booted, setBooted] = useState(false);
  const [apiBase, setApiBaseState] = useState<string>(defaultApiBase());
  const [session, setSession] = useState<Session | null>(null);
  const [cartToken, setCartToken] = useState<string | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [route, setRoute] = useState<Route>({ name: "catalog" });
  const [catalog, setCatalog] = useState<CatalogState>({ status: "idle" });
  /** null until the deployment has told us what it is. Never defaulted to a mode. */
  const [commerceMode, setCommerceMode] = useState<CommerceMode | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastOrder, setLastOrder] = useState<Order | null>(null);
  /** True when the last checkout returned an EXISTING order rather than placing a new one. */
  const [lastOrderReplayed, setLastOrderReplayed] = useState(false);

  // Guards against a slow response from a previous API base overwriting a newer one.
  const catalogRequestId = useRef(0);

  // --------------------------------------------------------------------------- boot

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [storedBase, storedSession, storedCart] = await Promise.all([
        storage.loadApiBase(),
        storage.loadSession(),
        storage.loadCartToken(),
      ]);
      if (cancelled) return;
      if (storedBase) setApiBaseState(storedBase);
      if (storedSession) setSession(storedSession);
      if (storedCart) setCartToken(storedCart);
      setBooted(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // ------------------------------------------------------------------ failure policy

  /**
   * Central reaction to a failed call.
   *
   * Returns the error so callers can still render something specific. Only a 401 mutates
   * global state, and it does so once.
   */
  const handleFailure = useCallback(
    (error: unknown): ApiError => {
      const apiError =
        error instanceof ApiError ? error : new ApiError("network", "unexpected failure");
      if (apiError.kind === "unauthorized") {
        setSession(null);
        void storage.clearSession();
        setNotice("Your session expired. Please sign in again.");
      }
      return apiError;
    },
    []
  );

  // -------------------------------------------------------------------------- catalog

  const loadCatalog = useCallback(async () => {
    const requestId = ++catalogRequestId.current;
    setCatalog({ status: "loading" });
    try {
      const products = await api.listProducts(apiBase);
      if (requestId !== catalogRequestId.current) return;
      setCatalog({ status: "ready", products });
    } catch (error) {
      if (requestId !== catalogRequestId.current) return;
      setCatalog({ status: "error", error: handleFailure(error) });
    }
  }, [apiBase, handleFailure]);

  // Reload whenever the API base changes, but only after boot has restored a saved one.
  useEffect(() => {
    if (!booted) return;
    void loadCatalog();
  }, [booted, loadCatalog]);

  // -------------------------------------------------------------------- commerce mode

  /**
   * Ask the deployment what it is.
   *
   * A failure leaves `commerceMode` null, and the catalogue screen then shows its
   * mode-independent notice. It deliberately does NOT go through `handleFailure`: this is
   * an unauthenticated disclosure call, so a 401 from it says nothing about the customer's
   * session and must not end one.
   */
  const loadCommerceMode = useCallback(async () => {
    try {
      setCommerceMode(await api.getCommerceMode(apiBase));
    } catch {
      setCommerceMode(null);
    }
  }, [apiBase]);

  // Per API base, like the catalogue: pointing the app at another deployment must not keep
  // showing the previous one's disclosure.
  useEffect(() => {
    if (!booted) return;
    void loadCommerceMode();
  }, [booted, loadCommerceMode]);

  // ----------------------------------------------------------------------------- cart

  const refreshCart = useCallback(async () => {
    try {
      const next = await api.viewCart(apiBase, cartToken);
      setCart(next);
      if (next.cart_token !== cartToken) {
        setCartToken(next.cart_token);
        await storage.saveCartToken(next.cart_token);
      }
      return next;
    } catch (error) {
      throw handleFailure(error);
    }
  }, [apiBase, cartToken, handleFailure]);

  const addToCart = useCallback(
    async (variantId: number, quantity: number) => {
      try {
        const next = await api.addCartItem(apiBase, cartToken, variantId, quantity);
        setCart(next);
        if (next.cart_token !== cartToken) {
          setCartToken(next.cart_token);
          await storage.saveCartToken(next.cart_token);
        }
        return next;
      } catch (error) {
        throw handleFailure(error);
      }
    },
    [apiBase, cartToken, handleFailure]
  );

  const setLineQuantity = useCallback(
    async (variantId: number, currentQuantity: number, desiredQuantity: number) => {
      try {
        const next = await api.setCartItemQuantity(
          apiBase,
          cartToken,
          variantId,
          currentQuantity,
          desiredQuantity
        );
        setCart(next);
        return next;
      } catch (error) {
        // The decrease path is two calls; refresh so the UI shows the real server state
        // rather than an optimistic guess about which half succeeded.
        try {
          setCart(await api.viewCart(apiBase, cartToken));
        } catch {
          /* leave the previous cart on screen */
        }
        throw handleFailure(error);
      }
    },
    [apiBase, cartToken, handleFailure]
  );

  const removeLine = useCallback(
    async (variantId: number) => {
      try {
        const next = await api.removeCartItem(apiBase, cartToken, variantId);
        setCart(next);
        return next;
      } catch (error) {
        throw handleFailure(error);
      }
    },
    [apiBase, cartToken, handleFailure]
  );

  // ----------------------------------------------------------------------------- auth

  const signIn = useCallback(
    async (email: string, password: string) => {
      try {
        const token = await api.login(apiBase, email, password);
        const next: Session = { accessToken: token.access_token, role: token.role, email };
        setSession(next);
        await storage.saveSession(next);
        setNotice(null);
        return next;
      } catch (error) {
        throw handleFailure(error);
      }
    },
    [apiBase, handleFailure]
  );

  const signUp = useCallback(
    async (email: string, password: string, fullName: string, marketingConsent: boolean) => {
      try {
        const token = await api.register(apiBase, email, password, fullName, marketingConsent);
        const next: Session = { accessToken: token.access_token, role: token.role, email };
        setSession(next);
        await storage.saveSession(next);
        setNotice(null);
        return next;
      } catch (error) {
        throw handleFailure(error);
      }
    },
    [apiBase, handleFailure]
  );

  /**
   * Forget the cart after checkout has consumed it.
   *
   * `services.checkout` sets `cart.status = "converted"` but LEAVES the lines in place, so
   * `GET /cart` with the same token keeps returning the purchased items and the bag badge
   * keeps counting them. Found by driving the real API. Dropping the token is the correct
   * client response: the next cart call mints a fresh, empty cart.
   */
  const resetCart = useCallback(async () => {
    setCart(null);
    setCartToken(null);
    await storage.clearCartToken();
  }, []);

  /** Clears the session but deliberately keeps the cart -- the basket is the device's. */
  const signOut = useCallback(async () => {
    setSession(null);
    await storage.clearSession();
    setNotice(null);
  }, []);

  // ------------------------------------------------------------------------- api base

  const setApiBase = useCallback(async (value: string) => {
    setApiBaseState(value);
    await storage.saveApiBase(value);
    setCart(null);
    setNotice(null);
  }, []);

  // ----------------------------------------------------------------------- navigation

  const navigate = useCallback((next: Route) => setRoute(next), []);

  const cartCount = useMemo(
    () => (cart ? cart.lines.reduce((total, line) => total + line.quantity, 0) : 0),
    [cart]
  );

  return {
    booted,
    apiBase,
    setApiBase,
    session,
    signIn,
    signUp,
    signOut,
    cart,
    cartToken,
    cartCount,
    refreshCart,
    resetCart,
    addToCart,
    setLineQuantity,
    removeLine,
    catalog,
    loadCatalog,
    commerceMode,
    loadCommerceMode,
    route,
    navigate,
    notice,
    setNotice,
    lastOrder,
    setLastOrder,
    lastOrderReplayed,
    setLastOrderReplayed,
    handleFailure,
  };
}
