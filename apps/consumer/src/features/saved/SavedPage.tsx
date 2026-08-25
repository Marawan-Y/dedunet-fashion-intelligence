import { useEffect, useState } from "react";
import { ButtonLink } from "../../components/Button";
import { Chip, ChipRow } from "../../components/Badge";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { NotBuiltState } from "../../components/States";
import styles from "./SavedPage.module.css";

type Tab = "looks" | "products" | "brands";

const TABS: {
  id: Tab;
  label: string;
  holds: string;
  /** What saving this thing would actually do for the customer. */
  purpose: string;
  destination: { to: string; label: string };
}[] = [
  {
    id: "looks",
    label: "Looks",
    holds: "Complete outfits",
    purpose:
      "A saved look keeps the whole arrangement — every piece, the occasion it was built for, and the reasoning — so you can come back to a decision rather than rebuild it.",
    destination: { to: "/looks", label: "Browse looks" },
  },
  {
    id: "products",
    label: "Products",
    holds: "Individual pieces",
    purpose:
      "A saved piece is the one you are not sure about yet. It stays with its brand, its size grid and its availability, so what you come back to is the piece and not a screenshot of it.",
    destination: { to: "/shop", label: "Browse the capsule" },
  },
  {
    id: "brands",
    label: "Brands",
    holds: "Labels you follow",
    purpose:
      "A saved brand is a standing preference. It tells DEDUNET whose work to put in front of you before you have asked, and it is the first real signal a styling model would have.",
    destination: { to: "/brands", label: "Browse brands" },
  },
];

/**
 * Saved.
 *
 * Section 19 asks for real saving where the backend supports it, and section 22 forbids
 * faking persistence. The backend has no saved-items model — no table, no endpoint — so
 * this page does not write to localStorage to look functional. A list that survives a
 * refresh on one device and is empty on the next is a worse promise than an honest
 * "not built", because the customer only discovers it when they have lost something.
 *
 * The three sections are real structure and real counts. When the backend gains a
 * saved-items model, the only thing that changes here is where the count comes from.
 */
export default function SavedPage() {
  const [tab, setTab] = useState<Tab>("looks");

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
              The looks, pieces and brands you want to come back to, kept in one place.
            </Lede>
          </Stack>

          {/* Counts, from the same source the list would come from. Zero everywhere,
              because there is no store — shown rather than hidden, so the number is a fact
              rather than an absence. */}
          <ul className={styles.summary}>
            {TABS.map((t) => (
              <li key={t.id} className={styles.summaryItem}>
                <span className={styles.summaryCount}>0</span>
                <span className={styles.summaryLabel}>{t.label}</span>
                <span className={styles.summaryHolds}>{t.holds}</span>
              </li>
            ))}
          </ul>

          <ChipRow label="Saved sections">
            {TABS.map((t) => (
              <Chip key={t.id} selected={tab === t.id} onClick={() => setTab(t.id)}>
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

            <NotBuiltState
              title="Saving is not built yet"
              body={`DEDUNET has nowhere to store your saved ${active.label.toLowerCase()}. There is no saved-items model behind this page, and writing to this browser alone would give you a list that disappears the moment you open DEDUNET anywhere else.`}
              action={
                <ButtonLink to={active.destination.to} variant="secondary">
                  {active.destination.label}
                </ButtonLink>
              }
            />
          </section>

          <Subtle>
            When saving does arrive it will be attached to your account rather than to this
            browser, so the list is the same on every device you sign in from. That is the
            reason it is not shipped as a local-only feature first.
          </Subtle>
        </Stack>
      </Section>
    </Container>
  );
}
