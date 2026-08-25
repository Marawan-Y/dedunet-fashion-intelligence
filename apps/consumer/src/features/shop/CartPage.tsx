import { useEffect } from "react";
import { ButtonLink } from "../../components/Button";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { EmptyState } from "../../components/States";
import { useCommerceMode } from "../../app/CommerceMode";

/**
 * The bag.
 *
 * Empty by construction in BRAND_PREVIEW_MODE: nothing in the catalogue is purchasable, so
 * nothing can be added. The copy is derived from the resolved mode rather than hard-coded,
 * because "nothing here is available to purchase" is FALSE in COMMERCE_TEST_MODE where
 * synthetic stock is purchasable and sandbox checkout completes. Shipping one sentence for
 * both modes is the class of untruth this programme keeps closing.
 */
export default function CartPage() {
  const { disclosure } = useCommerceMode();

  useEffect(() => {
    document.title = "Bag — DEDUNET";
  }, []);

  const purchasable = disclosure?.purchasable ?? null;

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Your bag</Eyebrow>
            <h1>Bag</h1>
            <Lede>Nothing has been added yet.</Lede>
          </Stack>

          <EmptyState
            title="Your bag is empty"
            body={
              purchasable === false
                ? "This catalogue is in preview, so nothing can be added to a bag. Everything is here to be looked at rather than bought."
                : purchasable === true
                  ? "Add something from the catalogue and it will appear here."
                  : "Add something from the catalogue and it will appear here."
            }
            action={
              <div style={{ display: "flex", gap: "var(--ds-space-3)", flexWrap: "wrap" }}>
                <ButtonLink to="/shop" variant="primary">
                  Browse the capsule
                </ButtonLink>
                <ButtonLink to="/dido" variant="secondary">
                  Style with Dido
                </ButtonLink>
              </div>
            }
          />

          {purchasable === null ? (
            <Subtle>
              DEDUNET could not confirm which mode this deployment is in, so this page is
              showing what is true either way rather than guessing.
            </Subtle>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}
