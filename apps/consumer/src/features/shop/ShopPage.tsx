import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card } from "../../components/Card";
import { SaveButton } from "../../components/SaveButton";
import { SelectField, TextField } from "../../components/Field";
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
import { primaryImage, useCatalog } from "../useCatalog";
import { filterProducts } from "../discover/DiscoverPage";
import styles from "./ShopPage.module.css";

type SortKey = "name" | "category" | "collection";

/**
 * Shop.
 *
 * A real destination, but not the platform's identity — section 17. Search, category and
 * sort all operate on the real catalogue and all live in the URL, so a filtered shop is
 * shareable and survives a refresh.
 */
export default function ShopPage() {
  const catalog = useCatalog();
  const [params, setParams] = useSearchParams();

  const query = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const brandSlug = params.get("brand") ?? "";
  const sort = (params.get("sort") as SortKey) || "name";

  useEffect(() => {
    document.title = "Shop — DEDUNET";
  }, []);

  const categories = useMemo(
    () => [...new Set((catalog.data ?? []).map((p) => p.category))].sort(),
    [catalog.data],
  );

  /* Brands derived from the CATALOGUE rather than fetched separately, so the filter can
     never offer a brand with nothing behind it -- picking one and getting "nothing matches"
     is a worse experience than not offering it. */
  const brands = useMemo(() => {
    const seen = new Map<string, string>();
    for (const product of catalog.data ?? []) {
      if (product.brand?.slug) seen.set(product.brand.slug, product.brand.name);
    }
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [catalog.data]);

  const results = useMemo(() => {
    let filtered = filterProducts(catalog.data ?? [], { query, category });
    if (brandSlug) filtered = filtered.filter((p) => p.brand?.slug === brandSlug);
    return [...filtered].sort((a, b) => {
      if (sort === "category") return a.category.localeCompare(b.category);
      if (sort === "collection") return a.collection.localeCompare(b.collection);
      return a.name.localeCompare(b.name);
    });
  }, [catalog.data, query, category, brandSlug, sort]);

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
          <div data-testid="shop-head">
            <Stack gap="tight">
              <Eyebrow>The catalogue</Eyebrow>
              <h1>Shop</h1>
              <Lede>
                Every piece DEDUNET can show you, with the brand it comes from. If you would
                rather be styled than browse, start with Dido.
              </Lede>
            </Stack>
          </div>

          <div className={styles.controls}>
            <TextField
              label="Search products"
              type="search"
              value={query}
              placeholder="Trouser, shirt, scarf…"
              onChange={(e) => update("q", e.currentTarget.value)}
            />

            <SelectField
              label="Category"
              value={category}
              onChange={(e) => update("category", e.currentTarget.value)}
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </SelectField>

            {/* Shown only when there is a choice to make. A single-brand catalogue with a
                brand filter is a control that can only ever do nothing. */}
            {brands.length > 1 ? (
              <SelectField
                label="Brand"
                value={brandSlug}
                onChange={(e) => update("brand", e.currentTarget.value)}
                data-testid="shop-brand-filter"
              >
                <option value="">All brands</option>
                {brands.map(([slug, name]) => (
                  <option key={slug} value={slug}>
                    {name}
                  </option>
                ))}
              </SelectField>
            ) : null}

            <SelectField
              label="Sort"
              value={sort}
              onChange={(e) => update("sort", e.currentTarget.value)}
            >
              <option value="name">Name</option>
              <option value="category">Category</option>
              <option value="collection">Collection</option>
            </SelectField>
          </div>

          {catalog.status === "loading" ? <SkeletonGrid count={5} label="Loading catalogue" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}

          {catalog.status === "success" ? (
            <Stack gap="loose">
              <Subtle role="status" aria-live="polite">
                {results.length} {results.length === 1 ? "piece" : "pieces"}
              </Subtle>

              {results.length === 0 ? (
                <EmptyState
                  title="Nothing matches that"
                  body="Try a broader search, or clear the filters to see the whole capsule."
                  action={
                    <ButtonLink to="/shop" variant="secondary">
                      Clear filters
                    </ButtonLink>
                  }
                />
              ) : (
                <div data-testid="shop-grid">
                  <Grid>
                    {results.map((product) => {
                      const image = primaryImage(product);
                      return (
                        <Card
                          key={product.slug}
                          to={`/product/${product.slug}`}
                          title={product.name}
                          /* REAL attribution. Hardcoding "DEDUNET" was true only while one
                             brand existed, and a multi-brand shop that labels every piece
                             with the platform's own name is misattribution. */
                          brand={product.brand?.name ?? "DEDUNET"}
                          meta={product.category}
                          image={image?.url}
                          imageAlt={image?.alt_text ?? `Concept artwork for ${product.name}`}
                          slot={`shop-${product.slug}`}
                          testId="product-card"
                          headingLevel={2}
                          saveControl={
                            <SaveButton
                              kind="products"
                              slug={product.slug}
                              name={product.name}
                              testId={`save-product-${product.slug}`}
                            />
                          }
                          footer={
                            /* The server's label, not this component's guess. Falls back to
                               the accepted copy if an older payload carries no action. */
                            <Badge
                              tone={product.commerce_action?.enabled ? "info" : "warning"}
                              dot
                            >
                              {product.commerce_action?.label ?? "Not available to buy"}
                            </Badge>
                          }
                        />
                      );
                    })}
                  </Grid>
                </div>
              )}
            </Stack>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}
