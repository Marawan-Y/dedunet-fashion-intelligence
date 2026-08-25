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
import { brand as brandAssets } from "../../lib/brand";
import { brandBySlug, commerceRouteLabel, ownershipLabel } from "../content";
import { primaryImage, useCatalog } from "../useCatalog";
import styles from "./BrandDetailPage.module.css";

export default function BrandDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const profile = slug ? brandBySlug(slug) : undefined;
  const catalog = useCatalog();

  useEffect(() => {
    if (profile) document.title = `${profile.name} — DEDUNET`;
  }, [profile]);

  if (!profile) return <NotFound />;

  const isDedunet = profile.slug === "dedunet";
  const products = isDedunet ? catalog.data ?? [] : [];

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
              <Eyebrow>{profile.positioning}</Eyebrow>
              <h1>{profile.name}</h1>

              <div className={styles.badges} data-testid="brand-commerce">
                <Badge tone="neutral">{ownershipLabel(profile.ownership)}</Badge>
                <Badge tone={profile.commerceRoute === "NON_PURCHASABLE" ? "warning" : "info"}>
                  {commerceRouteLabel(profile.commerceRoute)}
                </Badge>
                {profile.demonstration ? <FixtureBadge>Demonstration</FixtureBadge> : null}
              </div>

              <Lede>{profile.story}</Lede>

              <dl className={styles.facts}>
                <dt>Origin</dt>
                <dd>{profile.origin}</dd>
                <dt>Where it sells</dt>
                <dd>{commerceRouteLabel(profile.commerceRoute)}</dd>
              </dl>
            </div>

            <Media
              src={isDedunet ? brandAssets.assets.about : ""}
              alt={
                isDedunet
                  ? "DEDUNET brand concept artwork"
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

            {isDedunet && catalog.status === "loading" ? (
              <SkeletonGrid count={5} label="Loading products" />
            ) : null}
            {isDedunet && catalog.status === "error" ? (
              <ErrorState error={catalog.error} onRetry={catalog.retry} />
            ) : null}

            {!isDedunet ? (
              <EmptyState
                title="No catalogue"
                body="This entry demonstrates the shape of a brand that DEDUNET curates rather than makes. It has no products because it is not a real brand, and inventing some would misrepresent the platform."
                action={
                  <ButtonLink to="/brands" variant="secondary">
                    Back to Brands
                  </ButtonLink>
                }
              />
            ) : null}

            {isDedunet && catalog.status === "success" ? (
              <Grid>
                {products.map((product) => {
                  const image = primaryImage(product);
                  return (
                    <Card
                      key={product.slug}
                      to={`/product/${product.slug}`}
                      title={product.name}
                      brand="DEDUNET"
                      meta={product.category}
                      image={image?.url}
                      imageAlt={image?.alt_text ?? `Concept artwork for ${product.name}`}
                      slot={`brand-product-${product.slug}`}
                      testId="product-card"
                      footer={<Badge tone="neutral" dot>Preview</Badge>}
                    />
                  );
                })}
              </Grid>
            ) : null}
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
