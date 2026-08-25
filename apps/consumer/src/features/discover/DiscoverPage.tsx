import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge, Chip, ChipRow } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card, OccasionCard } from "../../components/Card";
import { TextField } from "../../components/Field";
import {
  Container,
  Eyebrow,
  Grid,
  Section,
  SectionHead,
  Stack,
  Lede,
  Subtle,
} from "../../components/primitives";
import { EmptyState, ErrorState, SkeletonGrid } from "../../components/States";
import { OCCASIONS, STYLE_CATEGORIES } from "../content";
import { primaryImage, useCatalog } from "../useCatalog";
import type { CatalogProduct } from "../../api/types";

/**
 * Discover.
 *
 * Section 22: a filter that does not affect results is a decorative shell. Everything on
 * this page filters the real catalogue, and the result count is rendered from the filtered
 * array rather than from a constant.
 *
 * The filter state lives in the URL. That is not a detail — it makes a filtered view
 * shareable, survivable across a refresh, and navigable with the back button, which is
 * three behaviours a customer expects and useState alone cannot give.
 */
export default function DiscoverPage() {
  const catalog = useCatalog();
  const [params, setParams] = useSearchParams();

  const query = params.get("q") ?? "";
  const category = params.get("category") ?? "";

  useEffect(() => {
    document.title = "Discover — DEDUNET";
  }, []);

  const categories = useMemo(() => {
    const all = new Set((catalog.data ?? []).map((p) => p.category));
    return [...all].sort();
  }, [catalog.data]);

  const results = useMemo(
    () => filterProducts(catalog.data ?? [], { query, category }),
    [catalog.data, query, category],
  );

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Browse the platform</Eyebrow>
            <h1>Discover</h1>
            <Lede>
              Search the catalogue, or start from an occasion and let the pieces come to you.
            </Lede>
          </Stack>

          <div data-testid="discover-filters">
            <Stack gap="loose">
              <TextField
                label="Search products"
                type="search"
                value={query}
                placeholder="Trouser, shirt, overshirt…"
                hint="Matches name, description, category and material."
                onChange={(e) => update("q", e.currentTarget.value)}
              />

              {categories.length ? (
                <Stack gap="tight">
                  <Eyebrow as="h2">Category</Eyebrow>
                  <ChipRow label="Filter by category">
                    <Chip selected={category === ""} onClick={() => update("category", "")}>
                      All
                    </Chip>
                    {categories.map((c) => (
                      <Chip
                        key={c}
                        selected={category === c}
                        onClick={() => update("category", category === c ? "" : c)}
                      >
                        {c}
                      </Chip>
                    ))}
                  </ChipRow>
                </Stack>
              ) : null}
            </Stack>
          </div>

          {catalog.status === "loading" ? <SkeletonGrid count={6} label="Loading catalogue" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}

          {catalog.status === "success" ? (
            <Stack gap="loose">
              {/* The count comes from the filtered array. A hard-coded total next to a
                  working filter is how a filter appears to work while doing nothing. */}
              <Subtle role="status" aria-live="polite">
                {results.length} {results.length === 1 ? "piece" : "pieces"}
                {query || category ? " matching your filters" : " in the catalogue"}
              </Subtle>

              {results.length === 0 ? (
                <EmptyState
                  title="Nothing matches that"
                  body="There are five pieces in the catalogue at the moment. Try a broader search, or clear the filters."
                  action={
                    <ButtonLink to="/discover" variant="secondary">
                      Clear filters
                    </ButtonLink>
                  }
                />
              ) : (
                <Grid>
                  {results.map((product) => {
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
                        slot={`discover-${product.slug}`}
                        testId="product-card"
                        footer={<Badge tone="neutral" dot>Preview</Badge>}
                      />
                    );
                  })}
                </Grid>
              )}
            </Stack>
          ) : null}
        </Stack>
      </Section>

      <Section tight aria-labelledby="discover-occasions">
        <SectionHead
          eyebrow="By occasion"
          title="Dressing for something specific?"
          level={2}
          id="discover-occasions"
        />
        <Grid>
          {OCCASIONS.slice(0, 6).map((o) => (
            <OccasionCard key={o.slug} to={`/discover/${o.slug}`} name={o.name} hint={o.hint} />
          ))}
        </Grid>
      </Section>

      <Section tight aria-labelledby="discover-styles">
        <SectionHead eyebrow="By style" title="Or by how you dress" level={2} id="discover-styles" />
        <Grid>
          {STYLE_CATEGORIES.map((c) => (
            <OccasionCard
              key={c.slug}
              to={`/discover/${c.slug}`}
              name={c.name}
              hint={c.description}
            />
          ))}
        </Grid>
      </Section>
    </Container>
  );
}

/**
 * The actual filter.
 *
 * Exported so it can be unit tested away from the DOM, and so the category page can reuse
 * exactly this logic rather than reimplementing a near-identical version that drifts.
 */
export function filterProducts(
  products: CatalogProduct[],
  filters: { query?: string; category?: string; categories?: string[] },
): CatalogProduct[] {
  const q = filters.query?.trim().toLowerCase() ?? "";

  return products.filter((p) => {
    if (filters.category && p.category !== filters.category) return false;

    if (filters.categories?.length) {
      const match = filters.categories.some(
        (c) => c.toLowerCase() === p.category.toLowerCase(),
      );
      if (!match) return false;
    }

    if (!q) return true;

    /* Substring across the fields a customer would actually search by. Not semantic
       search, and nothing here pretends it is: KNOWN_LIMITATIONS records that search is a
       literal match, and this is the client-side equivalent of the same honest thing. */
    const haystack = [p.name, p.description, p.category, p.material, p.collection]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}
