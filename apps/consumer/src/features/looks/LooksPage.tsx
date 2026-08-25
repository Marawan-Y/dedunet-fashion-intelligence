import { useEffect } from "react";
import { FixtureBadge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card } from "../../components/Card";
import {
  Container,
  Eyebrow,
  Grid,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { ErrorState, SkeletonGrid } from "../../components/States";
import { LOOKS } from "../content";
import { bySlug, primaryImage, useCatalog } from "../useCatalog";

/**
 * Looks.
 *
 * Section 15: a Look is a first-class product concept, not a tag on a product. Each one is
 * an arrangement of pieces that exist in the catalogue, with a stated occasion, descriptors
 * and an editorial argument for why those pieces are together.
 */
export default function LooksPage() {
  const catalog = useCatalog();

  useEffect(() => {
    document.title = "Looks — DEDUNET";
  }, []);

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Complete outfits</Eyebrow>
            <h1>Looks</h1>
            <Lede>
              A look is a whole outfit with the reasoning attached: what it is for, what each
              piece is doing, and which brand it comes from.
            </Lede>
          </Stack>

          <Stack gap="tight">
            <div>
              <FixtureBadge>Editorially arranged</FixtureBadge>
            </div>
            <Subtle>
              These four are assembled by hand from the DEDUNET capsule. No outfit engine
              produced them and none of them is personalised — the engine that would score
              compatibility, budget and fit is not built. Every garment shown is real; the
              curation is the part that is not automated.
            </Subtle>
          </Stack>

          {catalog.status === "loading" ? <SkeletonGrid count={4} label="Loading looks" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}

          {catalog.status === "success" ? (
            <Grid variant="wide">
              {LOOKS.map((look) => {
                const lead = look.items[0];
                const product = lead ? bySlug(catalog.data, lead.productSlug) : undefined;
                const image = product ? primaryImage(product) : undefined;

                return (
                  <Card
                    key={look.slug}
                    to={`/look/${look.slug}`}
                    title={look.name}
                    brand="DEDUNET"
                    meta={`For ${look.occasion} · ${look.items.length} pieces`}
                    image={image?.url}
                    imageAlt={image?.alt_text ?? `Concept artwork for ${look.name}`}
                    ratio="3 / 2"
                    slot={`look-${look.slug}`}
                    testId="look-card"
                    headingLevel={2}
                    footer={
                      <span style={{ fontSize: "var(--ds-text-sm)", color: "var(--ds-text-muted)" }}>
                        {look.descriptors.join(" · ")}
                      </span>
                    }
                  />
                );
              })}
            </Grid>
          ) : null}

          <div>
            <ButtonLink to="/dido" variant="accent">
              Have Dido build one for you
            </ButtonLink>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
