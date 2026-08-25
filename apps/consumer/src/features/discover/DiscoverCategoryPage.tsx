import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
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
import { EmptyState, ErrorState, SkeletonGrid } from "../../components/States";
import { occasionBySlug, styleCategoryBySlug } from "../content";
import { primaryImage, useCatalog } from "../useCatalog";
import { filterProducts } from "./DiscoverPage";
import { NotFound } from "../../app/RouteError";

/**
 * A single occasion or style cut of the catalogue.
 *
 * One route serves both because from the customer's side they are the same thing — a named
 * way into a filtered catalogue — and splitting them would duplicate every piece of this
 * page for a distinction only the data model cares about.
 */
export default function DiscoverCategoryPage() {
  const { category: slug } = useParams<{ category: string }>();
  const catalog = useCatalog();

  const occasion = slug ? occasionBySlug(slug) : undefined;
  const style = slug ? styleCategoryBySlug(slug) : undefined;
  const title = occasion?.name ?? style?.name;

  useEffect(() => {
    if (title) document.title = `${title} — DEDUNET`;
  }, [title]);

  /* An unknown slug is a 404, not an empty grid. An empty grid says "we have nothing for
     Interview", which is a different and wrong statement. */
  if (!occasion && !style) return <NotFound />;

  const results = filterProducts(catalog.data ?? [], {
    categories: occasion?.categories ?? [],
  });

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <nav aria-label="Breadcrumb">
            <Link to="/discover" style={{ fontSize: "var(--ds-text-sm)" }}>
              ← Discover
            </Link>
          </nav>

          <Stack gap="tight">
            <Eyebrow>{occasion ? "Occasion" : "Style"}</Eyebrow>
            <h1>{occasion ? `${occasion.name} Fits` : style!.name}</h1>
            <Lede>{occasion?.hint ?? style!.description}</Lede>
          </Stack>

          {occasion ? (
            <Subtle>
              Drawn from {occasion.categories.join(" and ").toLowerCase()} in the catalogue.
              Occasion matching is a category rule, not a styling model — the model that
              would weigh dress code, weather and fit is not built.
            </Subtle>
          ) : (
            <Subtle>
              Style cuts are defined but not yet applied to the catalogue: the pieces have no
              style classification behind them, so this shows the whole capsule rather than
              filtering it to a claim DEDUNET cannot make.
            </Subtle>
          )}

          {catalog.status === "loading" ? <SkeletonGrid count={4} label="Loading" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}

          {catalog.status === "success" ? (
            (style ? catalog.data ?? [] : results).length === 0 ? (
              <EmptyState
                title="Nothing here yet"
                body="The catalogue has five pieces and none of them are classified for this cut yet."
                action={
                  <ButtonLink to="/discover" variant="secondary">
                    Back to Discover
                  </ButtonLink>
                }
              />
            ) : (
              <Grid>
                {(style ? catalog.data ?? [] : results).map((product) => {
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
                      slot={`category-${product.slug}`}
                      testId="product-card"
                      headingLevel={2}
                      footer={<Badge tone="neutral" dot>Preview</Badge>}
                    />
                  );
                })}
              </Grid>
            )
          ) : null}

          <div>
            <ButtonLink to="/dido" variant="accent">
              Style this with Dido
            </ButtonLink>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
