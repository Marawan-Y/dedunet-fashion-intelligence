import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell, RouteAnnouncer } from "./AppShell";
import { CommerceModeProvider } from "./CommerceMode";
import { RouteError, NotFound } from "./RouteError";
import { RouteFallback } from "./RouteFallback";

/* Real path routing, not hash routing.
 *
 * A hash router never asks the server for a route, which is why it appears to work
 * everywhere and is also why it cannot support a shareable URL that a server, a crawler or
 * a native app can resolve. Real paths require one thing of the host — a history fallback,
 * so /discover serves index.html rather than 404 — and that is configured in nginx.conf
 * and provided natively by the dev server. The refresh test in the E2E suite is what
 * proves it is actually there, because a missing fallback fails ONLY on reload.
 */

/* Route-level code splitting. Home and the shell are eager because they are the first
   paint; everything else is fetched when it is first visited. */
const Home = lazy(() => import("../features/home/HomePage"));
const Dido = lazy(() => import("../features/dido/DidoPage"));
const Discover = lazy(() => import("../features/discover/DiscoverPage"));
const DiscoverCategory = lazy(() => import("../features/discover/DiscoverCategoryPage"));
const Looks = lazy(() => import("../features/looks/LooksPage"));
const LookDetail = lazy(() => import("../features/looks/LookDetailPage"));
const Brands = lazy(() => import("../features/brands/BrandsPage"));
const BrandDetail = lazy(() => import("../features/brands/BrandDetailPage"));
const Shop = lazy(() => import("../features/shop/ShopPage"));
const Product = lazy(() => import("../features/shop/ProductPage"));
const Saved = lazy(() => import("../features/saved/SavedPage"));
const MyStyle = lazy(() => import("../features/my-style/MyStylePage"));
const ForBrands = lazy(() => import("../features/for-brands/ForBrandsPage"));
const Account = lazy(() => import("../features/account/AccountPage"));
const Orders = lazy(() => import("../features/account/OrdersPage"));
const Cart = lazy(() => import("../features/shop/CartPage"));

function page(element: React.ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <>
        <RouteAnnouncer />
        <AppShell />
      </>
    ),
    /* Catches a render failure in ANY route and shows a recoverable error instead of the
       white screen React otherwise leaves behind. Section 23: no blank page, ever. */
    errorElement: <RouteError />,
    children: [
      { index: true, element: page(<Home />) },
      { path: "dido", element: page(<Dido />) },
      { path: "discover", element: page(<Discover />) },
      { path: "discover/:category", element: page(<DiscoverCategory />) },
      { path: "looks", element: page(<Looks />) },
      { path: "look/:slug", element: page(<LookDetail />) },
      { path: "brands", element: page(<Brands />) },
      { path: "brand/:slug", element: page(<BrandDetail />) },
      { path: "shop", element: page(<Shop />) },
      { path: "product/:slug", element: page(<Product />) },
      { path: "cart", element: page(<Cart />) },
      { path: "saved", element: page(<Saved />) },
      { path: "my-style", element: page(<MyStyle />) },
      { path: "for-brands", element: page(<ForBrands />) },
      { path: "account", element: page(<Account />) },
      { path: "orders", element: page(<Orders />) },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export function App() {
  return (
    <CommerceModeProvider>
      <RouterProvider router={router} />
    </CommerceModeProvider>
  );
}
