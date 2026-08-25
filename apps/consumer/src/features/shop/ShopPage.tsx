import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card } from "../../components/Card";
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
  const sort = (params.get("sort") as SortKey) || "name";

  useEffect(() => {
    document.title = "Shop — DEDUNET";
  }, []);

  const categories = useMemo(
    () => [...new Set((catalog.data ?? []).map((p) => p.category))].sort(),
    [catalog.data],
  );

  const results = useMemo(() => {
    const filtered = filterProducts(catalog.data ?? [], { query, category });
    return [...filtered].sort((a, b) => {
      if (sort === "category") return a.category.localeCompare(b.category);
      if (sort === "collection") return a.collection.localeCompare(b.collection);
      return a.name.localeCompare(b.name);
    });
  }, [catalog.data, query, category, sort]);

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
                          brand="DEDUNET"
                          meta={product.category}
                          image={image?.url}
                          imageAlt={image?.alt_text ?? `Concept artwork for ${product.name}`}
                          slot={`shop-${product.slug}`}
                          testId="product-card"
                          headingLevel={2}
                          footer={
                            <Badge tone="warning" dot>
                              Not available to buy
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
