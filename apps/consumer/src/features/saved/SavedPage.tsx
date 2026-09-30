import { useEffect, useState } from "react";
import { Badge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Chip, ChipRow } from "../../components/Badge";
import { Card } from "../../components/Card";
import { SaveButton } from "../../components/SaveButton";
import {
  Container,
  Eyebrow,
  Grid,
  Lede,
  Section,
  Stack,
} from "../../components/primitives";
import { EmptyState, ErrorState, SkeletonGrid } from "../../components/States";
import { fetchSavedBrands, fetchSavedLooks, fetchSavedProducts } from "../../api/endpoints";
import type {
  SavedBrandEntry,
  SavedListing,
  SavedLookEntry,
  SavedProductEntry,
} from "../../api/types";
import { useAsync } from "../../lib/useAsync";
import { formatMinorUnits } from "../../lib/money";
import { useSaved } from "./SavedContext";
import styles from "./SavedPage.module.css";

type Tab = "looks" | "products" | "brands";

/* The three entry shapes share `slug`, `name`, `saved_at` and `available`; everything else
   differs per kind. A union rather than a widened interface, so a card cannot read a price
   off a brand. */
type AnySavedEntry = SavedProductEntry | SavedBrandEntry | SavedLookEntry;

interface TabSpec {
  id: Tab;
  label: string;
  holds: string;
  purpose: string;
  empty: string;
  destination: { to: string; label: string };
}

const TABS: TabSpec[] = [
  {
    id: "looks",
    label: "Looks",
    holds: "Complete outfits",
    purpose:
      "A saved look keeps the whole arrangement, not just the pieces. The reason each garment is there is part of what you kept.",
    empty: "You haven't saved any looks yet.",
    destination: { to: "/looks", label: "Browse looks" },
  },
  {
    id: "products",
    label: "Products",
    holds: "Individual pieces",
    purpose:
      "A saved piece is a decision you have not made yet. Keeping it costs nothing and does not put it in a basket.",
    empty: "You haven't saved any products yet.",
    destination: { to: "/shop", label: "Browse the shop" },
  },
  {
    id: "brands",
    label: "Brands",
    holds: "Labels you follow",
    purpose:
      "A saved brand is a standing preference: whose work to put in front of you before you have asked.",
    empty: "You haven't saved any brands yet.",
    destination: { to: "/brands", label: "Browse brands" },
  },
];

/**
 * Saved.
 *
 * REAL PERSISTENCE, attached to the account rather than the browser. This page previously
 * said "Saving is not built yet" and meant it: there was no table, no endpoint, and it
 * deliberately refused to write to `localStorage` to look functional, because a list that
 * survives a refresh on one device and is empty on the next is a worse promise than an
 * honest absence.
 *
 * That disclosure is now REMOVED, because the thing it disclosed is built. The production
 * disclosure rule cuts both ways: an unbuilt feature must say so, and a built one must stop
 * saying so. Leaving the notice up would be the same defect in the other direction.
 *
 * Counts come from the shared saved context, so they agree with every save control on every
 * other surface without this page refetching.
 */
export default function SavedPage() {
  const [tab, setTab] = useState<Tab>("products");
  const { counts, signedIn, ready } = useSaved();

  useEffect(() => {
    document.title = "Saved — DEDUNET";
  }, []);

  const active = TABS.find((t) => t.id === tab)!;

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Your space</Eyebrow>
            <h1>Saved</h1>
            <Lede>
              The looks, pieces and brands you want to come back to, kept to your account so
              the list is the same on every device you sign in from.
            </Lede>
          </Stack>

          <ul className={styles.summary} data-testid="saved-summary">
            {TABS.map((t) => (
              <li key={t.id} className={styles.summaryItem}>
                <span className={styles.summaryCount} data-testid={`saved-count-${t.id}`}>
                  {signedIn ? counts[t.id] : 0}
                </span>
                <span className={styles.summaryLabel}>{t.label}</span>
                <span className={styles.summaryHolds}>{t.holds}</span>
              </li>
            ))}
          </ul>

          <ChipRow label="Saved sections">
            {TABS.map((t) => (
              <Chip
                key={t.id}
                selected={tab === t.id}
                onClick={() => setTab(t.id)}
                testId={`saved-tab-${t.id}`}
              >
                {t.label}
              </Chip>
            ))}
          </ChipRow>

          <section
            aria-labelledby="saved-section-heading"
            aria-live="polite"
            className={styles.panel}
          >
            <h2 id="saved-section-heading" className={styles.panelTitle}>
              {active.label}
            </h2>
            <p className={styles.purpose}>{active.purpose}</p>

            {!signedIn && ready ? (
              /* Honest, not fake. There is no anonymous saved list to show, because there
                 is no anonymous saved list -- see SavedContext. */
              <EmptyState
                title="Sign in to see your saved items"
                body="Saved looks, pieces and brands are kept to your account rather than to this browser, so they are the same wherever you sign in."
                action={
                  <ButtonLink to="/account" variant="primary">
                    Sign in
                  </ButtonLink>
                }
              />
            ) : (
              <SavedSection tab={tab} spec={active} />
            )}
          </section>
        </Stack>
      </Section>
    </Container>
  );
}

/** One tab's list. Mounted per tab so switching tabs does not refetch the others. */
function SavedSection({ tab, spec }: { tab: Tab; spec: TabSpec }) {
  const { version } = useSaved();

  const listing = useAsync<SavedListing<AnySavedEntry>>(
    (signal) => {
      if (tab === "products") return fetchSavedProducts(signal);
      if (tab === "brands") return fetchSavedBrands(signal);
      return fetchSavedLooks(signal);
    },
    /* `version`, NOT the saved set.
     *
     * The set changes optimistically the moment the control is tapped -- before the DELETE
     * has committed -- so refetching on it can be served the row the server is still
     * removing, leaving a list that never corrects itself. `version` only advances once the
     * request has settled. WebKit failed on this consistently; Chromium hid it. */
    [tab, version],
  );

  if (listing.status === "loading") {
    return <SkeletonGrid count={3} label={`Loading saved ${spec.label.toLowerCase()}`} />;
  }
  if (listing.status === "error") {
    return <ErrorState error={listing.error} onRetry={listing.retry} />;
  }

  const items = listing.data?.items ?? [];
  if (items.length === 0) {
    return (
      <EmptyState
        title={spec.empty}
        body="Anything you save will appear here."
        action={
          <ButtonLink to={spec.destination.to} variant="secondary">
            {spec.destination.label}
          </ButtonLink>
        }
      />
    );
  }

  return (
    <Grid>
      {items.map((entry) => {
        const kind = tab;
        /* An unavailable target is rendered but NOT linked. It was theirs, so it does not
           silently vanish; it is also no longer active production content, so it is not a
           destination. */
        const href =
          !entry.available
            ? ""
            : kind === "products"
              ? `/product/${entry.slug}`
              : kind === "brands"
                ? `/brand/${entry.slug}`
                : `/look/${entry.slug}`;

        const meta = describe(entry, kind);
        const image =
          "image_url" in entry ? entry.image_url : "logo_url" in entry ? entry.logo_url : "";

        return (
          <div key={`${kind}-${entry.slug}`} data-testid="saved-item">
            {href ? (
              <Card
                to={href}
                title={entry.name}
                meta={meta}
                image={image}
                imageAlt={`${entry.name}`}
                ratio={kind === "brands" ? "3 / 2" : "3 / 4"}
                slot={`saved-${kind}-${entry.slug}`}
                testId={kind === "brands" ? "brand-card" : "product-card"}
                headingLevel={3}
                saveControl={
                  <SaveButton
                    kind={kind}
                    slug={entry.slug}
                    name={entry.name}
                    testId={`unsave-${kind}-${entry.slug}`}
                  />
                }
                footer={
                  "is_development_fixture" in entry && entry.is_development_fixture ? (
                    <Badge tone="warning" dot>
                      Development fixture
                    </Badge>
                  ) : undefined
                }
              />
            ) : (
              <article className={styles.unavailable}>
                <h3 className={styles.unavailableTitle}>{entry.name}</h3>
                <p className={styles.unavailableBody}>
                  No longer available. It stays in your saved items until you remove it.
                </p>
                <SaveButton
                  kind={kind}
                  slug={entry.slug}
                  name={entry.name}
                  variant="inline"
                  testId={`unsave-${kind}-${entry.slug}`}
                />
              </article>
            )}
          </div>
        );
      })}
    </Grid>
  );
}

/** The card's secondary line, per kind. */
function describe(entry: AnySavedEntry, kind: Tab): string {
  if (kind === "products" && entry.kind === "product") {
    const price =
      typeof entry.price_minor_units_min === "number"
        ? formatMinorUnits(entry.price_minor_units_min, entry.currency)
        : "";
    return price ? `${entry.category} · ${price}` : entry.category;
  }
  if (kind === "brands" && entry.kind === "brand") return entry.relationship_label;
  if (entry.kind === "look") {
    return entry.item_count === 1 ? "1 piece" : `${entry.item_count} pieces`;
  }
  return "";
}
