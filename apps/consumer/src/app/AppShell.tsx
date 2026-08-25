import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { mediaUrl } from "../api/client";
import { brand } from "../lib/brand";
import { useCommerceMode } from "./CommerceMode";
import styles from "./AppShell.module.css";

/* The application shell: disclosure, header, live region, main, footer, tab bar. */

/* Every NavLink below passes a FUNCTION for className.
 *
 * With a string, react-router appends its own "active" and "pending" classes — names this
 * design system never defines, so they render with no rule behind them. That is precisely
 * the defect class that failed Phase 2 acceptance, and the CSS contract test caught it here
 * before it shipped. Styling keys off aria-current, which the router sets anyway and which
 * a screen reader announces, so the visual state and the announced state are one fact.
 */
const DESKTOP_NAV = [
  { to: "/dido", label: "Style with Dido", primary: true },
  { to: "/discover", label: "Discover" },
  { to: "/looks", label: "Looks" },
  { to: "/brands", label: "Brands" },
  { to: "/shop", label: "Shop" },
  { to: "/saved", label: "Saved" },
  { to: "/account", label: "Account" },
];

export function AppShell() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <CommerceNotice />
      <SiteHeader />

      {/* One polite live region for the whole platform. Several competing regions is how a
          status message ends up announced by none of them. */}
      <div id="ds-live" className="sr-only" role="status" aria-live="polite" />

      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>

      <SiteFooter />
      <MobileTabBar />
    </>
  );
}

function CommerceNotice() {
  const { disclosure } = useCommerceMode();

  /* The shipped sentence is what is true in every permitted mode. The deployment's own
     disclosure replaces it only once the API has actually said which mode this is. */
  const text = disclosure
    ? [disclosure.headline, ...disclosure.detail].join(" ")
    : "DEDUNET prototype. No real card is charged and no real order is fulfilled.";

  return (
    <p className={styles.notice} role="note" data-testid="commerce-mode-notice">
      {text}
    </p>
  );
}

function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <NavLink to="/" className={() => styles.brand!} aria-label="DEDUNET home">
          <img
            className={styles.brandMark}
            src={mediaUrl(brand.assets.logo_primary)}
            alt="DEDUNET"
            width={132}
            height={22}
          />
        </NavLink>

        <nav className={styles.nav} aria-label="Main">
          {DESKTOP_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={() =>
                [styles.navLink, item.primary ? styles.navDido : ""].filter(Boolean).join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.headerActions}>
          <NavLink to="/cart" className={() => styles.iconButton!} aria-label="Bag" data-testid="header-bag">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
              <path d="M6 7h12l1 14H5z" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M9 7a3 3 0 0 1 6 0" fill="none" stroke="currentColor" strokeWidth="1.6" />
            </svg>
          </NavLink>
        </div>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div style={{ maxWidth: "var(--ds-content-max)", margin: "0 auto", padding: "0 var(--ds-gutter)" }}>
        <div className={styles.footerGrid}>
          <FooterColumn
            heading="Platform"
            links={[
              { to: "/dido", label: "Style with Dido" },
              { to: "/discover", label: "Discover" },
              { to: "/looks", label: "Looks" },
              { to: "/brands", label: "Brands" },
              { to: "/shop", label: "Shop" },
            ]}
          />
          <FooterColumn
            heading="You"
            links={[
              { to: "/account", label: "Account" },
              { to: "/my-style", label: "My Style" },
              { to: "/saved", label: "Saved" },
              { to: "/orders", label: "Orders" },
            ]}
          />
          <FooterColumn
            heading="Brands"
            links={[{ to: "/for-brands", label: "DEDUNET for Brands" }]}
          />
        </div>

        <p className={styles.legal}>
          DEDUNET — worth, worn. This is a prototype build. Imagery is concept artwork, not
          product photography. Material, composition and origin are stated intentions pending
          supplier documents, samples and testing, and are not substantiated claims. DEDUNET
          is not accepting brands and has no commercial agreements with any brand.
        </p>
      </div>
    </footer>
  );
}

function FooterColumn({
  heading,
  links,
}: {
  heading: string;
  links: { to: string; label: string }[];
}) {
  return (
    <div>
      {/* h2 inside the footer, which sits after the page's own h1 in document order. */}
      <h2 className={styles.footerHeading}>{heading}</h2>
      <ul className={styles.footerList}>
        {links.map((link) => (
          <li key={link.to}>
            <NavLink to={link.to} className={() => styles.footerLink!}>
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* Five destinations with Dido raised at the centre. */
const TABS = [
  { to: "/", label: "Home", end: true, icon: <path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" fill="currentColor" /> },
  { to: "/discover", label: "Discover", icon: <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm3.5 6.5-2 5-5 2 2-5z" fill="currentColor" /> },
  { to: "/dido", label: "Dido", dido: true, icon: <path d="M12 3c-2.2 0-4 1.8-4 4v2H6v12h12V9h-2V7c0-2.2-1.8-4-4-4zm0 2a2 2 0 0 1 2 2v2h-4V7a2 2 0 0 1 2-2z" fill="currentColor" /> },
  { to: "/saved", label: "Saved", icon: <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" fill="currentColor" /> },
  { to: "/account", label: "Account", icon: <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-4 0-7 2.2-7 5v1h14v-1c0-2.8-3-5-7-5z" fill="currentColor" /> },
];

function MobileTabBar() {
  return (
    <nav className={styles.tabBar} aria-label="Primary">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={() => [styles.tab, tab.dido ? styles.tabDido : ""].filter(Boolean).join(" ")}
        >
          {tab.dido ? (
            <span className={styles.tabDidoMark}>
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                {tab.icon}
              </svg>
            </span>
          ) : (
            <svg className={styles.tabIcon} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              {tab.icon}
            </svg>
          )}
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}

/**
 * Focus and scroll management across a route change.
 *
 * A single-page application changes the document without the browser doing any of the
 * things a real navigation does. Left alone, a screen reader announces nothing and the
 * keyboard stays wherever the last link was — several screens into a page that no longer
 * exists. Moving focus to `main` is what makes an SPA route change a navigation.
 */
export function RouteAnnouncer() {
  const location = useLocation();

  /* Compare against the last path rather than counting mounts.
   *
   * A boolean "is this the first run" guard is defeated by StrictMode, which invokes every
   * effect twice on mount: the first pass flips the flag and the second pass then treats a
   * cold load as a navigation. That is not cosmetic — it moved focus into <main> on page
   * load, which put the skip link BEHIND the current focus position and made the first Tab
   * land in the footer. A skip link the keyboard cannot reach is worse than none, because
   * it is still announced.
   *
   * Comparing paths is idempotent, so running twice changes nothing. */
  const lastPath = useRef(location.pathname);

  useEffect(() => {
    if (lastPath.current === location.pathname) return;
    lastPath.current = location.pathname;

    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });

    const main = document.getElementById("main");
    main?.focus({ preventScroll: true });

    /* Announce the destination by its own h1, so what is read out is the page's name
       rather than a route path. */
    const heading = document.querySelector("main h1")?.textContent?.trim();
    const live = document.getElementById("ds-live");
    if (live && heading) live.textContent = `${heading}. Page loaded.`;
  }, [location.pathname]);

  return null;
}
