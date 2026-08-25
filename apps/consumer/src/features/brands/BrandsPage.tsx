import { useEffect } from "react";
import { Badge, FixtureBadge } from "../../components/Badge";
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
import { brand as brandAssets } from "../../lib/brand";
import { BRANDS, commerceRouteLabel, ownershipLabel } from "../content";
import { primaryImage, useCatalog } from "../useCatalog";

/**
 * Brands.
 *
 * Section 16: never invent partnerships. DEDUNET is the only real brand here. The second
 * entry is a structure demonstration, it is labelled as one on the card and again on its
 * page, and its own copy says it is not a partner.
 *
 * The consumer-facing language is "Made by DEDUNET" and "Curated by DEDUNET", never
 * PLATFORM_CURATED or EXTERNAL_CURATED. Internal enums are for the data model.
 */
export default function BrandsPage() {
  const catalog = useCatalog();

  useEffect(() => {
    document.title = "Brands — DEDUNET";
  }, []);

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>The network</Eyebrow>
            <h1>Brands</h1>
            <Lede>
              DEDUNET holds brands it makes and brands it curates. Where a piece is sold is a
              separate question from who makes it, and both are stated on every brand.
            </Lede>
          </Stack>

          <Subtle>
            DEDUNET is not accepting brands and has no commercial agreement with any brand.
            One entry below exists to show the shape of a multi-brand catalogue.
          </Subtle>

          {catalog.status === "loading" ? <SkeletonGrid count={2} label="Loading brands" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}

          {catalog.status === "success" ? (
            <Grid variant="wide">
              {BRANDS.map((profile) => {
                /* The DEDUNET card leads with a real product image from the catalogue. The
                   demonstration entry has no products and therefore no image, so its media
                   slot renders the labelled placeholder rather than borrowing artwork that
                   would imply it has a collection. */
                const lead = profile.slug === "dedunet" ? (catalog.data ?? [])[0] : undefined;
                const image = lead ? primaryImage(lead) : undefined;
                const cover = profile.slug === "dedunet" ? brandAssets.assets.collection_cover : "";

                return (
                  <Card
                    key={profile.slug}
                    to={`/brand/${profile.slug}`}
                    title={profile.name}
                    meta={profile.positioning}
                    image={image?.url || cover}
                    imageAlt={
                      profile.slug === "dedunet"
                        ? "DEDUNET first capsule concept artwork"
                        : `No imagery for ${profile.name}`
                    }
                    ratio="editorial"
                    fit="contain"
                    slot={`brand-${profile.slug}`}
                    testId="brand-card"
                    headingLevel={2}
                    footer={
                      <div style={{ display: "flex", gap: "var(--ds-space-2)", flexWrap: "wrap" }}>
                        <Badge tone="neutral">{ownershipLabel(profile.ownership)}</Badge>
                        <Badge tone={profile.commerceRoute === "NON_PURCHASABLE" ? "warning" : "info"}>
                          {commerceRouteLabel(profile.commerceRoute)}
                        </Badge>
                        {profile.demonstration ? <FixtureBadge>Demonstration</FixtureBadge> : null}
                      </div>
                    }
                  />
                );
              })}
            </Grid>
          ) : null}

          <section aria-labelledby="brands-later" data-testid="brands-later">
            <h2 style={{ fontSize: "var(--ds-heading)" }} id="brands-later">
              How brands join
            </h2>
            <Lede style={{ marginTop: "var(--ds-space-3)" }}>
              A brand on DEDUNET keeps its own identity, its own story and its own commerce.
              DEDUNET supplies the styling layer that puts it in front of someone who has
              already said what they need it for.
            </Lede>
            <Subtle style={{ marginTop: "var(--ds-space-3)" }}>
              Merchant accounts, catalogues and order routing are not built. Nothing on this
              page can be signed up for.
            </Subtle>
          </section>
        </Stack>
      </Section>
    </Container>
  );
}
