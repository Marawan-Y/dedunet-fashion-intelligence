import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, FixtureBadge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card } from "../../components/Card";
import { Media } from "../../components/Media";
import {
  Container,
  Eyebrow,
  Grid,
  Lede,
  Section,
  SectionHead,
  Stack,
  Subtle,
} from "../../components/primitives";
import { EmptyState, ErrorState, SkeletonGrid } from "../../components/States";
import { NotFound } from "../../app/RouteError";
import { ApiError } from "../../api/types";
import { brand as brandAssets } from "../../lib/brand";
import { formatMinorUnits } from "../../lib/money";
import { useBrand } from "../useBrands";
import styles from "./BrandDetailPage.module.css";

/**
 * Brand detail, wired to the real domain.
 *
 * Every state the page can be in is handled explicitly, because each of them happened during
 * this phase's development: loading, a 404 for a brand that does not exist or is not visible,
 * a transport error with a retry, and a real brand whose catalogue is legitimately empty.
 *
 * The layout is the accepted one. What changed is that `brandBySlug` -- a lookup in a
 * hardcoded array that only ever knew about two brands -- became a request, so a brand added
 * to the database appears here without a frontend release.
 */
export default function BrandDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const brand = useBrand(slug);
  const profile = brand.data;

  useEffect(() => {
    if (profile) document.title = `${profile.name} — DEDUNET`;
  }, [profile]);

  /* A 404 from the API is a missing page, not an error banner. An unpublished brand also
     answers 404 rather than 403, deliberately: a 403 would confirm the row exists. */
  if (brand.status === "error" && brand.error instanceof ApiError && brand.error.status === 404) {
    return <NotFound />;
  }

  if (brand.status === "loading") {
    return (
      <Container>
        <Section>
          <SkeletonGrid count={5} label="Loading brand" />
        </Section>
      </Container>
    );
  }

  if (brand.status === "error" || !profile) {
    return (
      <Container>
        <Section>
          <ErrorState error={brand.error} onRetry={brand.retry} />
        </Section>
      </Container>
    );
  }

  const products = profile.products ?? [];
  const isDedunet = profile.slug === "dedunet";

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <nav aria-label="Breadcrumb">
            <Link to="/brands" style={{ fontSize: "var(--ds-text-sm)" }}>
              ← Brands
            </Link>
          </nav>

          <div className={styles.header}>
            <div className={styles.headerCopy}>
              <Eyebrow>{profile.relationship_label}</Eyebrow>
              <h1>{profile.name}</h1>

              <div className={styles.badges} data-testid="brand-commerce">
                <Badge tone="neutral">{profile.relationship_label}</Badge>
                <Badge tone="info">
                  {products.length === 1 ? "1 piece" : `${products.length} pieces`}
                </Badge>
                {profile.is_development_fixture ? (
                  <FixtureBadge>Development fixture</FixtureBadge>
                ) : null}
              </div>

              {/* The fixture notice is prose, not only a badge. A badge can be cropped out
                  of a screenshot; a sentence under the heading cannot be missed. */}
              {profile.fixture_notice ? (
                <Subtle data-testid="brand-fixture-notice">{profile.fixture_notice}</Subtle>
              ) : null}

              <Lede>{profile.story}</Lede>

              <dl className={styles.facts}>
                <dt>Relationship</dt>
                <dd>{profile.relationship_label}</dd>
                <dt>Information</dt>
                {/* Where the brand's information came from. "Written by DEDUNET" is a
                    different claim from "Maintained by the brand", and the difference
                    matters to a reader deciding how much to trust it. */}
                <dd>{profile.provenance.label}</dd>
                {profile.country_code ? (
                  <>
                    <dt>Country</dt>
                    <dd>{profile.country_code}</dd>
                  </>
                ) : null}
                {profile.website_url ? (
                  <>
                    <dt>Website</dt>
                    <dd>
                      {/* rel is not optional on an outbound link: without noopener the
                          opened page can navigate this tab (reverse tabnabbing). */}
                      <a
                        href={profile.website_url}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                      >
                        {profile.website_url}
                      </a>
                    </dd>
                  </>
                ) : null}
              </dl>
            </div>

            <Media
              src={
                profile.cover_image_url ||
                profile.logo_url ||
                (isDedunet ? brandAssets.assets.about : "")
              }
              alt={
                profile.cover_image_url || profile.logo_url || isDedunet
                  ? `${profile.name} brand artwork`
                  : `No imagery for ${profile.name}`
              }
              ratio="editorial"
              slot={`brand-detail-${profile.slug}`}
              fit="contain"
            />
          </div>

          <section aria-labelledby="brand-products">
            <SectionHead
              eyebrow={isDedunet ? "First Passage / 01" : "Catalogue"}
              title={isDedunet ? "The capsule" : "Products"}
              level={2}
              id="brand-products"
            />

            {products.length === 0 ? (
              <EmptyState
                title="No catalogue"
                body={
                  profile.is_development_fixture
                    ? "This record exists to exercise the multi-brand architecture. It has no products because it is not a real brand, and inventing some would misrepresent the platform."
                    : "This brand has no published pieces yet."
                }
                action={
                  <ButtonLink to="/brands" variant="secondary">
                    Back to Brands
                  </ButtonLink>
                }
              />
            ) : (
              <Grid>
                {products.map((product) => {
                  const price =
                    typeof product.price_minor_units_min === "number"
                      ? formatMinorUnits(product.price_minor_units_min, product.currency)
                      : "";
                  return (
                    <Card
                      key={product.slug}
                      to={`/product/${product.slug}`}
                      title={product.name}
                      brand={product.brand.name}
                      meta={price ? `${product.category} · ${price}` : product.category}
                      image={product.image_url}
                      imageAlt={`Concept artwork for ${product.name}`}
                      slot={`brand-product-${product.slug}`}
                      testId="product-card"
                      footer={
                        /* The server decided this label. The client renders it and does not
                           re-derive a purchase gate of its own. */
                        <Badge
                          tone={product.commerce_action.enabled ? "info" : "warning"}
                          dot
                        >
                          {product.commerce_action.label}
                        </Badge>
                      }
                    />
                  );
                })}
              </Grid>
            )}
          </section>

          {isDedunet ? (
            <Subtle>
              Material, composition and origin are stated intentions pending supplier
              documents, samples and testing. They are not substantiated claims, and the
              country of origin is deliberately unset rather than guessed.
            </Subtle>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}
