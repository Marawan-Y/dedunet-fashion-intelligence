import { useEffect } from "react";
import { Badge, FixtureBadge } from "../../components/Badge";
import { Card } from "../../components/Card";
import { SaveButton } from "../../components/SaveButton";
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
import { realBrandsFirst, useBrands } from "../useBrands";

/**
 * Brands.
 *
 * WIRED TO THE REAL DOMAIN. This page used to render a hardcoded array; it now renders
 * whatever brands the API returns, with their real product counts. The layout is the
 * accepted one and is deliberately unchanged -- the foundation is locked, and this phase
 * changes where the data comes from, not what the page looks like.
 *
 * Never invent partnerships. The relationship wording comes from the server as
 * `relationship_label`, so an internal enum cannot leak into copy and no surface can coin
 * its own word for a relationship that does not exist. A development fixture carries
 * `fixture_notice` and is rendered with it, always.
 */
export default function BrandsPage() {
  const brands = useBrands();

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

          {brands.status === "loading" ? <SkeletonGrid count={2} label="Loading brands" /> : null}
          {brands.status === "error" ? (
            <ErrorState error={brands.error} onRetry={brands.retry} />
          ) : null}

          {brands.status === "success" && (brands.data?.items ?? []).length === 0 ? (
            <Subtle data-testid="brands-empty">No brands are published yet.</Subtle>
          ) : null}

          {brands.status === "success" ? (
            <Grid variant="wide">
              {realBrandsFirst(brands.data?.items ?? []).map((profile) => {
                /* Imagery, and why a fixture gets none.
                   A brand with no products has no artwork of its own, and borrowing another
                   brand's would imply it has a collection. The first-party brand uses its
                   own logo asset; anything else uses its logo if the domain gave it one and
                   the labelled placeholder otherwise. */
                const cover =
                  profile.cover_image_url ||
                  profile.logo_url ||
                  (profile.slug === "dedunet" ? brandAssets.assets.collection_cover : "");

                return (
                  <Card
                    key={profile.slug}
                    to={`/brand/${profile.slug}`}
                    title={profile.name}
                    /* The story's opening clause, not the relationship label -- that is
                       already on a badge below, and repeating it made the DEDUNET card read
                       "DEDUNET / DEDUNET / DEDUNET". A card should say something new in
                       each slot. */
                    meta={firstClause(profile.story)}
                    image={cover}
                    imageAlt={
                      cover
                        ? `${profile.name} brand artwork`
                        : `No imagery for ${profile.name}`
                    }
                    ratio="3 / 2"
                    slot={`brand-${profile.slug}`}
                    testId="brand-card"
                    headingLevel={2}
                    saveControl={
                      <SaveButton
                        kind="brands"
                        slug={profile.slug}
                        name={profile.name}
                        testId={`save-brand-${profile.slug}`}
                      />
                    }
                    footer={
                      <div style={{ display: "flex", gap: "var(--ds-space-2)", flexWrap: "wrap" }}>
                        <Badge tone="neutral">{profile.relationship_label}</Badge>

                        <Badge tone="info">
                          {profile.product_count === 1
                            ? "1 piece"
                            : `${profile.product_count} pieces`}
                        </Badge>
                        {/* Always rendered when present. A fixture must be impossible to
                            mistake for a real brand, including in a screenshot. */}
                        {profile.is_development_fixture ? (
                          <FixtureBadge>Development fixture</FixtureBadge>
                        ) : null}
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

/** The first sentence of a brand story, for a card. Never mid-word, never empty-looking. */
function firstClause(story: string): string {
  if (!story) return "";
  const sentence = story.split(/(?<=\.)\s/)[0] ?? story;
  if (sentence.length <= 120) return sentence;
  return `${sentence.slice(0, 117).trimEnd()}…`;
}
