import { useEffect } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { Card, OccasionCard } from "../../components/Card";
import { ProductFigure } from "../../components/ProductFigure";
import { mediaUrl } from "../../api/client";
import { ErrorState, SkeletonGrid } from "../../components/States";
import { brand } from "../../lib/brand";
import { useReveal } from "../../lib/useReveal";
import { DidoMoment } from "../dido/DidoMoment";
import { BRANDS, LOOKS, OCCASIONS, STYLE_CATEGORIES } from "../content";
import { bySlug, mediaByRotation, primaryImage, useCatalog } from "../useCatalog";
import styles from "./HomePage.module.css";

/**
 * Home.
 *
 * The information architecture is the accepted one and is unchanged: personal fashion
 * intelligence, style with Dido, occasion discovery, looks, Dido, product discovery,
 * styles, brands, for brands. What changed is the presentation.
 *
 * The rhythm alternates on purpose — full-bleed hero, occasion rail, split feature look,
 * full-bleed Dido, looks rail, editorial statement, capsule rail, style list, brands rail,
 * split for-brands. No two adjacent sections share a shape, which is what stops a long
 * page reading as a feed.
 *
 * Looks come before products (section 7): the feature look and the looks rail both sit
 * above the capsule, and the capsule is framed as the pieces that looks are built from.
 */
export default function HomePage() {
  const catalog = useCatalog();

  useEffect(() => {
    document.title = "DEDUNET — Personal fashion intelligence";
  }, []);

  const products = catalog.data ?? [];
  /* The four-piece look, because the feature slot wants the most composed arrangement. */
  const featured = LOOKS[2] ?? LOOKS[0]!;
  const featuredLead = bySlug(products, featured.items[0]?.productSlug ?? "");

  /* The plates Dido assembles, taken from the featured look so the moment shows real
     pieces from a real arrangement rather than three decorative rectangles. */
  const didoPieces = featured.items.slice(0, 3).map((item) => {
    const product = bySlug(products, item.productSlug);
    return {
      image: product ? primaryImage(product)?.url : null,
      label: product ? product.category : item.productSlug,
      alt: product ? product.name : item.productSlug,
    };
  });

  return (
    <>
      {/* ==================================================================== hero */}
      <section className={styles.hero} aria-labelledby="hero-title">
        <img
          className={styles.heroMedia}
          src={mediaUrl(brand.assets.hero)}
          alt=""
          aria-hidden="true"
        />

        <div className={styles.inner}>
          <div className={styles.heroCopy} data-testid="hero">
            <p className={styles.heroEyebrow}>
              <span className={styles.heroEyebrowRule} aria-hidden="true" />
              Personal fashion intelligence
            </p>

            {/* One h1. The wordmark is inside it but subordinate: the campaign line
                carries the size, because a homepage whose largest element is the company
                name is a software landing page. */}
            <h1 id="hero-title" className={styles.heroTitle}>
              <span className={styles.heroBrand}>DEDUNET</span>
              <span className={styles.heroStatement}>
                Decide what to wear.
                <em>Then find it.</em>
              </span>
            </h1>

            <p className={styles.heroLede}>
              Tell Dido where you are going. It builds complete looks, explains every piece,
              and traces each one back to the brand that makes it.
            </p>

            <div className={styles.heroActions}>
              <ButtonLink to="/dido" variant="accent">
                Style with Dido
              </ButtonLink>
              <Link to="/discover" className={styles.heroSecondary}>
                Discover looks
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* =============================================================== occasions */}
      <Reveal>
        <section className={styles.section} aria-labelledby="occasions-title">
          <div className={styles.inner}>
            <SectionHead
              eyebrow="Start here"
              title="What are you dressing for?"
              id="occasions-title"
              action={
                <ButtonLink to="/discover" variant="quiet">
                  All occasions
                </ButtonLink>
              }
            />

            <div
              className={`${styles.rail} ${styles.occasionRail}`}
              role="group"
              aria-label="Occasions"
              tabIndex={0}
              data-testid="occasions"
            >
              {OCCASIONS.map((occasion) => (
                <OccasionCard
                  key={occasion.slug}
                  to={`/discover/${occasion.slug}`}
                  name={occasion.name}
                  hint={occasion.hint}
                  image={occasion.image}
                />
              ))}
            </div>
          </div>
        </section>
      </Reveal>

      {/* ============================================================ feature look */}
      <Reveal>
        <section className={styles.section} aria-labelledby="feature-title">
          <div className={styles.inner}>
            <SectionHead eyebrow="The look" title={featured.name} id="feature-title" />

            <div className={styles.feature}>
              <div className={styles.featureMedia}>
                <ProductFigure
                  src={featuredLead ? primaryImage(featuredLead)?.url : null}
                  alt={`Concept artwork for ${featured.name}`}
                  slot={`home-feature-${featured.slug}`}
                  ratio="4 / 5"
                  mark="Editorially arranged"
                />
              </div>

              <div className={styles.featureCopy}>
                <div className={styles.featureTags}>
                  {featured.descriptors.map((d) => (
                    <span key={d} className={styles.featureTag}>
                      {d}
                    </span>
                  ))}
                </div>

                <p className={styles.featureStory}>{featured.story}</p>

                {catalog.status === "success" ? (
                  <ul className={styles.featurePieces}>
                    {featured.items.map((item) => {
                      const product = bySlug(products, item.productSlug);
                      return (
                        <li key={item.productSlug} className={styles.featurePiece}>
                          <span className={styles.featurePieceName}>
                            {product ? product.name : item.productSlug}
                          </span>
                          <span className={styles.featurePieceRole}>{item.role}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}

                <div>
                  <ButtonLink to={`/look/${featured.slug}`} variant="primary">
                    See the look
                  </ButtonLink>
                </div>
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ==================================================================== dido */}
      <DidoMoment pieces={didoPieces} />

      {/* =================================================================== looks */}
      <Reveal>
        <section className={styles.section} aria-labelledby="looks-title">
          <div className={styles.inner}>
            <SectionHead
              eyebrow="Complete outfits"
              title="Looks"
              id="looks-title"
              note="Assembled by hand from pieces that exist in the catalogue. Personalised selection is not built — see My Style for what DEDUNET does and does not know about you."
              action={
                <ButtonLink to="/looks" variant="quiet">
                  All looks
                </ButtonLink>
              }
            />

            {catalog.status === "loading" ? <SkeletonGrid count={3} label="Loading looks" /> : null}
            {catalog.status === "error" ? (
              <ErrorState error={catalog.error} onRetry={catalog.retry} />
            ) : null}

            {catalog.status === "success" ? (
              <div className={styles.rail} role="group" aria-label="Looks" tabIndex={0}>
                {LOOKS.map((look, index) => {
                  const lead = look.items[0];
                  const product = lead ? bySlug(products, lead.productSlug) : undefined;
                  /* Each look shows its lead piece from a different delivered view, so the
                     rail is varied without any plate misrepresenting its look. */
                  const image = product ? mediaByRotation(product, index) : undefined;
                  return (
                    <Card
                      key={look.slug}
                      to={`/look/${look.slug}`}
                      title={look.name}
                      brand={`For ${look.occasion}`}
                      meta={`${look.items.length} pieces · ${look.descriptors.join(", ")}`}
                      image={image?.url}
                      imageAlt={image?.alt_text ?? `Concept artwork for ${look.name}`}
                      slot={`home-look-${look.slug}`}
                      testId="look-card"
                    />
                  );
                })}
              </div>
            ) : null}
          </div>
        </section>
      </Reveal>

      {/* ============================================================== statement */}
      <Reveal>
        <section className={styles.statement} aria-labelledby="statement-title">
          <div className={`${styles.inner} ${styles.statementInner}`}>
            <h2 id="statement-title" className={styles.statementText}>
              A wardrobe is a set of decisions. <em>Most are made badly.</em>
            </h2>
            <p className={styles.statementNote}>
              DEDUNET exists to make the decision first and the purchase second. That is why
              the catalogue is not the front door, and why every look explains itself.
            </p>
          </div>
        </section>
      </Reveal>

      {/* ================================================================= capsule */}
      <Reveal>
        <section className={styles.section} aria-labelledby="capsule-title">
          <div className={styles.inner}>
            <SectionHead
              eyebrow="First Passage / 01"
              title="The pieces"
              id="capsule-title"
              note="The garments looks are built from. Every one is a prototype and none is available to buy."
              action={
                <ButtonLink to="/shop" variant="quiet">
                  See everything
                </ButtonLink>
              }
            />

            {catalog.status === "loading" ? (
              <SkeletonGrid count={4} label="Loading the capsule" />
            ) : null}
            {catalog.status === "error" ? (
              <ErrorState error={catalog.error} onRetry={catalog.retry} />
            ) : null}

            {catalog.status === "success" ? (
              <div className={styles.rail} role="group" aria-label="The capsule" tabIndex={0}>
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
                      slot={`home-product-${product.slug}`}
                      testId="product-card"
                      mark="Preview"
                    />
                  );
                })}
              </div>
            ) : null}
          </div>
        </section>
      </Reveal>

      {/* ================================================================== styles */}
      <Reveal>
        <section className={styles.section} aria-labelledby="styles-title">
          <div className={styles.inner}>
            <SectionHead eyebrow="Another way in" title="By style" id="styles-title" />

            <div className={styles.styleList}>
              {STYLE_CATEGORIES.map((category) => (
                <Link
                  key={category.slug}
                  to={`/discover/${category.slug}`}
                  className={styles.styleItem}
                >
                  <span className={styles.styleName}>{category.name}</span>
                  <span className={styles.styleDesc}>{category.description}</span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </Reveal>

      {/* ================================================================== brands */}
      <Reveal>
        <section className={styles.section} aria-labelledby="brands-title">
          <div className={styles.inner}>
            <SectionHead
              eyebrow="The network"
              title="Brands"
              id="brands-title"
              note="DEDUNET is not accepting brands and has no commercial agreement with any brand."
              action={
                <ButtonLink to="/brands" variant="quiet">
                  All brands
                </ButtonLink>
              }
            />

            <div className={styles.rail} role="group" aria-label="Brands" tabIndex={0}>
              {BRANDS.map((profile) => {
                const lead = profile.slug === "dedunet" ? products[0] : undefined;
                const image = lead ? primaryImage(lead)?.url : null;
                return (
                  <Card
                    key={profile.slug}
                    to={`/brand/${profile.slug}`}
                    title={profile.name}
                    brand={profile.positioning}
                    image={image}
                    imageAlt={
                      profile.slug === "dedunet"
                        ? "DEDUNET first capsule concept artwork"
                        : `No imagery for ${profile.name}`
                    }
                    slot={`home-brand-${profile.slug}`}
                    testId="brand-card"
                    mark={profile.demonstration ? "Demonstration" : undefined}
                  />
                );
              })}
            </div>
          </div>
        </section>
      </Reveal>

      {/* ============================================================== for brands */}
      <Reveal>
        <section className={styles.forBrands} aria-labelledby="for-brands-title">
          <div className={styles.forBrandsMedia}>
            <img
              src={mediaUrl(brand.assets.app_splash)}
              alt="DEDUNET brand concept artwork"
              loading="lazy"
              decoding="async"
            />
          </div>

          <div className={styles.forBrandsCopy}>
            <p className={styles.heroEyebrow}>
              <span className={styles.heroEyebrowRule} aria-hidden="true" />
              For brands
            </p>
            <h2 id="for-brands-title" className={styles.forBrandsTitle}>
              Reach customers through styling, not search.
            </h2>
            <p className={styles.forBrandsBody}>
              DEDUNET puts a brand in front of someone who has already described the occasion,
              the fit and the budget. That is a different kind of placement, and a different
              kind of customer, from a search result.
            </p>
            <ButtonLink to="/for-brands" variant="inverse">
              DEDUNET for Brands
            </ButtonLink>
            <p className={styles.forBrandsNote}>
              The merchant platform is not built. Nothing on this page can be signed up for.
            </p>
          </div>
        </section>
      </Reveal>
    </>
  );
}

/* ---------------------------------------------------------------------- helpers */

/**
 * A section head.
 *
 * Always an h2: every caller sits directly under the page h1, so there is no level to
 * decide and nothing that can skip. The eyebrow is a `p`, not a heading, because it labels
 * the title rather than introducing a level of its own.
 */
function SectionHead({
  eyebrow,
  title,
  id,
  note,
  action,
}: {
  eyebrow: string;
  title: string;
  id: string;
  note?: string;
  action?: ReactNode;
}) {
  return (
    <>
      <div className={styles.head}>
        <div className={styles.headText}>
          <p className={styles.eyebrow}>{eyebrow}</p>
          <h2 id={id} className={styles.title}>
            {title}
          </h2>
        </div>
        {action}
      </div>
      {note ? <p className={styles.note}>{note}</p> : null}
    </>
  );
}

/** Reveals its children the first time they scroll into view. */
function Reveal({ children }: { children: ReactNode }) {
  const { ref, revealed } = useReveal<HTMLDivElement>();
  return (
    <div ref={ref} className={`${styles.reveal} ${revealed ? styles.revealed : ""}`}>
      {children}
    </div>
  );
}
