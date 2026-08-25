import { useEffect, useId, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge } from "../../components/Badge";
import { Button, ButtonLink } from "../../components/Button";
import { Card } from "../../components/Card";
import { Media } from "../../components/Media";
import {
  Container,
  Eyebrow,
  Grid,
  Section,
  SectionHead,
  Stack,
  Subtle,
} from "../../components/primitives";
import { ErrorState, SkeletonGrid } from "../../components/States";
import { ApiError } from "../../api/types";
import { NotFound } from "../../app/RouteError";
import { purchaseRefusal, refusalText, useCommerceMode } from "../../app/CommerceMode";
import { LOOKS } from "../content";
import { coloursOf, orderedMedia, primaryImage, sizesOf, useCatalog, useProduct } from "../useCatalog";
import styles from "./ProductPage.module.css";

/**
 * Product detail.
 *
 * THE PURCHASE GATE ON THIS PAGE IS ACCEPTED, HUMAN-VERIFIED BEHAVIOUR. Do not relax it.
 *
 * It mirrors the server's `assert_purchasable`, both gates and in its order, because a
 * client that checks only one offers a purchase the server will refuse — which is the exact
 * defect the guard was written to close. The refusal text is bound to the disabled control
 * through aria-describedby, so the reason reaches the control rather than floating
 * elsewhere on the page.
 *
 * PUBLIC_COMMERCIAL_LAUNCH is BLOCKED.
 */
export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();
  const product = useProduct(slug);
  const catalog = useCatalog();
  const { disclosure } = useCommerceMode();

  const [activeIndex, setActiveIndex] = useState(0);
  const refusalId = useId();

  useEffect(() => {
    if (product.data) document.title = `${product.data.name} — DEDUNET`;
  }, [product.data]);

  /* Reset the gallery when the product changes, or a customer arriving from a related
     product sees the previous garment's third detail shot. */
  useEffect(() => setActiveIndex(0), [slug]);

  if (product.status === "loading") {
    return (
      <Container>
        <Section>
          <SkeletonGrid count={2} label="Loading product" />
        </Section>
      </Container>
    );
  }

  if (product.status === "error") {
    /* A product that does not exist is a 404 page, not an error box on a blank frame. */
    if (product.error instanceof ApiError && product.error.status === 404) return <NotFound />;
    return (
      <Container>
        <Section>
          <Stack gap="loose">
            <h1>Product</h1>
            <ErrorState error={product.error} onRetry={product.retry} />
          </Stack>
        </Section>
      </Container>
    );
  }

  const item = product.data!;
  const media = orderedMedia(item);
  const active = media[activeIndex] ?? media[0];
  const sizes = sizesOf(item);
  const colours = coloursOf(item);

  const refusal = purchaseRefusal(item.sellable, disclosure);
  const reason = refusalText(refusal);

  const relatedLooks = LOOKS.filter((look) =>
    look.items.some((i) => i.productSlug === item.slug),
  );
  const related = (catalog.data ?? []).filter((p) => p.slug !== item.slug).slice(0, 4);

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <nav aria-label="Breadcrumb">
            <Link to="/shop" style={{ fontSize: "var(--ds-text-sm)" }}>
              ← Shop
            </Link>
          </nav>

          <div className={styles.layout}>
            {/* ------------------------------------------------------- gallery */}
            <div className={styles.gallery}>
              <Media
                src={active?.url}
                alt={active?.alt_text ?? `Concept artwork for ${item.name}`}
                ratio="portrait"
                slot={`product-primary-${item.slug}`}
                fit="contain"
                priority
                note="Concept artwork, not product photography"
              />

              {media.length > 1 ? (
                <div className={styles.thumbs} role="group" aria-label="Product images">
                  {media.map((shot, index) => (
                    <button
                      key={shot.asset_id}
                      type="button"
                      className={
                        index === activeIndex
                          ? `${styles.thumb} ${styles.thumbActive}`
                          : styles.thumb
                      }
                      onClick={() => setActiveIndex(index)}
                      aria-label={`Show ${shot.role} view`}
                      aria-pressed={index === activeIndex}
                    >
                      <Media
                        src={shot.url}
                        alt=""
                        ratio="portrait"
                        slot={`product-thumb-${shot.asset_id}`}
                        fit="contain"
                      />
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            {/* ---------------------------------------------------------- info */}
            <div className={styles.info}>
              <Stack gap="loose">
                <Stack gap="tight">
                  <Eyebrow>
                    <Link to="/brand/dedunet" className={styles.brandLink}>
                      DEDUNET
                    </Link>
                  </Eyebrow>
                  <h1 className={styles.title}>{item.name}</h1>
                  <p className={styles.collection}>{item.collection}</p>
                </Stack>

                {/* Price. Absent, and the absence is explained rather than hidden. */}
                <div className={styles.price}>
                  {item.price_display ? (
                    <span className={styles.priceValue}>
                      {item.price_display} {item.currency}
                    </span>
                  ) : (
                    <span className={styles.priceAbsent}>Not priced</span>
                  )}
                </div>

                {/* ------------------------------------------- THE PURCHASE GATE */}
                <div className={styles.purchase}>
                  <Button
                    variant="primary"
                    fullWidth
                    disabled={Boolean(refusal)}
                    aria-describedby={refusal ? refusalId : undefined}
                  >
                    {refusal ? "Not available to buy" : "Add to cart"}
                  </Button>

                  {refusal ? (
                    <p className={styles.refusal} id={refusalId}>
                      {reason}
                    </p>
                  ) : null}
                </div>

                <p className={styles.description}>{item.description}</p>

                {colours.length ? (
                  <section aria-labelledby="product-colour">
                    <h2 id="product-colour" className={styles.specHeading}>
                      Colour
                    </h2>
                    <div className={styles.chips}>
                      {colours.map((c) => (
                        <span key={c} className={styles.chip}>
                          {c}
                        </span>
                      ))}
                    </div>
                  </section>
                ) : null}

                {sizes.length ? (
                  <section aria-labelledby="product-size">
                    <h2 id="product-size" className={styles.specHeading}>
                      Size
                    </h2>
                    <div className={styles.chips}>
                      {sizes.map((s) => (
                        <span key={s} className={styles.chip}>
                          {s}
                        </span>
                      ))}
                    </div>
                    <Subtle style={{ marginTop: "var(--ds-space-2)" }}>
                      Sizes are the prototype grid. No stock is held against them.
                    </Subtle>
                  </section>
                ) : null}

                <section aria-labelledby="product-details">
                  <h2 id="product-details" className={styles.specHeading}>
                    Details
                  </h2>
                  <dl className={styles.specs}>
                    <dt>Material</dt>
                    <dd>
                      {item.material}
                      {item.material_claim_status === "UNVERIFIED" ? (
                        <span className={styles.claim}> — stated, not verified</span>
                      ) : null}
                    </dd>

                    <dt>Origin</dt>
                    <dd>
                      {/* "XX" is deliberately an invalid country code so it cannot be read
                          as a substantiated claim. Rendering it raw would show a customer
                          "XX"; rendering it as an intention is the honest reading. */}
                      {item.country_of_origin === "XX"
                        ? `Intended: ${item.intended_origin}`
                        : item.country_of_origin}
                      {item.origin_claim_status === "UNVERIFIED" ? (
                        <span className={styles.claim}> — stated, not verified</span>
                      ) : null}
                    </dd>

                    <dt>Care</dt>
                    <dd>{item.care_instructions}</dd>

                    <dt>Category</dt>
                    <dd>{item.category}</dd>

                    <dt>Availability</dt>
                    <dd>
                      {/* The badge carries the LABEL and the sentence sits beside it.
                          A badge is `white-space: nowrap` by design — that is what keeps a
                          short status from breaking across lines — so a full sentence
                          inside one becomes an unbreakable 355px block. On a 390px phone
                          that forced this specs grid to 471px and took the whole page into
                          horizontal overflow. */}
                      <Badge tone="warning" dot>
                        Prototype
                      </Badge>{" "}
                      <span className={styles.claim}>not produced for sale</span>
                    </dd>
                  </dl>
                </section>

                <div className={styles.actions}>
                  <Button variant="secondary" disabled aria-describedby={`${refusalId}-save`}>
                    Save
                  </Button>
                  <ButtonLink to="/dido" variant="accent">
                    Style this with Dido
                  </ButtonLink>
                </div>
                <Subtle id={`${refusalId}-save`}>
                  Saving is not built. There is nowhere to store it yet.
                </Subtle>
              </Stack>
            </div>
          </div>

          {/* ------------------------------------------------------ related looks */}
          {relatedLooks.length ? (
            <section aria-labelledby="product-looks">
              <SectionHead
                eyebrow="Worn with"
                title="Looks featuring this piece"
                level={2}
                id="product-looks"
              />
              <Grid variant="wide">
                {relatedLooks.map((look) => (
                  <Card
                    key={look.slug}
                    to={`/look/${look.slug}`}
                    title={look.name}
                    brand="DEDUNET"
                    meta={`For ${look.occasion} · ${look.items.length} pieces`}
                    image={primaryImage(item)?.url}
                    imageAlt={`Concept artwork for ${look.name}`}
                    ratio="3 / 2"
                    slot={`product-look-${look.slug}`}
                    testId="look-card"
                  />
                ))}
              </Grid>
            </section>
          ) : null}

          {/* --------------------------------------------------- related products */}
          {related.length ? (
            <section aria-labelledby="product-related">
              <SectionHead
                eyebrow="Also in the capsule"
                title="More from DEDUNET"
                level={2}
                id="product-related"
              />
              <Grid>
                {related.map((p) => {
                  const image = primaryImage(p);
                  return (
                    <Card
                      key={p.slug}
                      to={`/product/${p.slug}`}
                      title={p.name}
                      brand="DEDUNET"
                      meta={p.category}
                      image={image?.url}
                      imageAlt={image?.alt_text ?? `Concept artwork for ${p.name}`}
                      slot={`product-related-${p.slug}`}
                      testId="product-card"
                    />
                  );
                })}
              </Grid>
            </section>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}
