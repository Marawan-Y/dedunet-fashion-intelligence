import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, FixtureBadge } from "../../components/Badge";
import { Button, ButtonLink } from "../../components/Button";
import { Media } from "../../components/Media";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { ErrorState, SkeletonGrid } from "../../components/States";
import { NotFound } from "../../app/RouteError";
import { lookBySlug } from "../content";
import { bySlug, primaryImage, useCatalog } from "../useCatalog";
import styles from "./LookDetailPage.module.css";

/**
 * A single look.
 *
 * Section 15 asks for total pricing and it is deliberately absent. Every DEDUNET piece is a
 * prototype carrying no commercial price, so a total would be a number this platform
 * invented. The page says that where the total would be, rather than showing a plausible
 * figure or silently omitting the row.
 *
 * The modification controls — swap, cheaper, more formal — are architecturally supported by
 * the LookItem shape but not built, and they are not rendered as dead buttons. A control
 * that does nothing is worse than an absent one.
 */
export default function LookDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const look = slug ? lookBySlug(slug) : undefined;
  const catalog = useCatalog();

  useEffect(() => {
    if (look) document.title = `${look.name} — DEDUNET`;
  }, [look]);

  if (!look) return <NotFound />;

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <nav aria-label="Breadcrumb">
            <Link to="/looks" style={{ fontSize: "var(--ds-text-sm)" }}>
              ← Looks
            </Link>
          </nav>

          <div className={styles.layout}>
            <div className={styles.main}>
              <Stack gap="loose">
                <Stack gap="tight">
                  <Eyebrow>For {look.occasion}</Eyebrow>
                  <h1>{look.name}</h1>
                  <div style={{ display: "flex", gap: "var(--ds-space-2)", flexWrap: "wrap" }}>
                    {look.descriptors.map((d) => (
                      <Badge key={d} tone="neutral">
                        {d}
                      </Badge>
                    ))}
                    <FixtureBadge>Editorially arranged</FixtureBadge>
                  </div>
                </Stack>

                <Lede>{look.story}</Lede>

                <section aria-labelledby="look-items">
                  <h2 id="look-items" className={styles.itemsHeading}>
                    The pieces
                  </h2>

                  {catalog.status === "loading" ? (
                    <SkeletonGrid count={look.items.length} label="Loading pieces" />
                  ) : null}
                  {catalog.status === "error" ? (
                    <ErrorState error={catalog.error} onRetry={catalog.retry} />
                  ) : null}

                  {catalog.status === "success" ? (
                    <ul className={styles.items} data-testid="look-items">
                      {look.items.map((item) => {
                        const product = bySlug(catalog.data, item.productSlug);
                        const image = product ? primaryImage(product) : undefined;

                        return (
                          <li key={item.productSlug} className={styles.item}>
                            <div className={styles.itemMedia}>
                              <Media
                                src={image?.url}
                                alt={image?.alt_text ?? item.productSlug}
                                ratio="portrait"
                                slot={`look-item-${item.productSlug}`}
                                fit="contain"
                              />
                            </div>

                            <div className={styles.itemBody}>
                              <span className={styles.itemBrand}>DEDUNET</span>
                              <h3 className={styles.itemName}>
                                {product ? (
                                  <Link to={`/product/${product.slug}`}>{product.name}</Link>
                                ) : (
                                  item.productSlug
                                )}
                              </h3>
                              <p className={styles.itemRole}>{item.role}</p>
                              {product ? (
                                <p className={styles.itemMeta}>{product.category}</p>
                              ) : null}
                            </div>

                            <div className={styles.itemAside}>
                              <Badge tone="neutral" dot>
                                Preview
                              </Badge>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  ) : null}
                </section>
              </Stack>
            </div>

            <aside className={styles.aside} aria-labelledby="look-summary">
              <h2 id="look-summary" className={styles.itemsHeading}>
                This look
              </h2>

              <dl className={styles.summary}>
                <dt>Pieces</dt>
                <dd>{look.items.length}</dd>
                <dt>Occasion</dt>
                <dd style={{ textTransform: "capitalize" }}>{look.occasion}</dd>
                <dt>Brands</dt>
                <dd>DEDUNET</dd>
                <dt>Total</dt>
                {/* Not a price, and not a blank. The reason is the content. */}
                <dd className={styles.noPrice}>Not priced</dd>
              </dl>

              <Subtle>
                Every piece in this capsule is a prototype with no commercial price, so this
                look has no total. A figure here would be invented.
              </Subtle>

              <div className={styles.asideActions}>
                <Button variant="secondary" disabled aria-describedby="save-look-reason">
                  Save this look
                </Button>
                <Subtle id="save-look-reason">
                  Saving is not built. There is nowhere to store it yet, and a save that
                  silently forgets is worse than one that says it cannot.
                </Subtle>

                <ButtonLink to="/dido" variant="accent">
                  Adjust with Dido
                </ButtonLink>
              </div>
            </aside>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
