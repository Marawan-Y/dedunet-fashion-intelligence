import { useEffect } from "react";
import { Badge, FixtureBadge } from "../../components/Badge";
import { ButtonLink } from "../../components/Button";
import { Card, OccasionCard } from "../../components/Card";
import { Media } from "../../components/Media";
import {
  Container,
  Eyebrow,
  Grid,
  Rail,
  Section,
  SectionHead,
  Stack,
  Subtle,
} from "../../components/primitives";
import { ErrorState, SkeletonGrid } from "../../components/States";
import { brand } from "../../lib/brand";
import { LOOKS, OCCASIONS, STYLE_CATEGORIES } from "../content";
import { primaryImage, useCatalog, bySlug } from "../useCatalog";
import styles from "./HomePage.module.css";

/**
 * Home.
 *
 * Section 12. The landing experience is STYLING, not a shop window: the primary action is
 * Dido and the catalogue is one destination within the platform rather than its front door.
 * That single decision is the difference between a clothing store with extras and a
 * platform with a shop in it.
 */
export default function HomePage() {
  const catalog = useCatalog();

  useEffect(() => {
    document.title = "DEDUNET — Personal fashion intelligence";
  }, []);

  return (
    <>
      <Container>
        <div className={styles.hero} data-testid="hero">
          <img
            className={styles.heroPattern}
            src={brand.assets.pattern ? `${brand.assets.pattern}` : ""}
            alt=""
            aria-hidden="true"
            onError={(e) => {
              /* The pattern is decoration. If it is missing the hero must still compose,
                 so it removes itself rather than leaving a broken image behind the type. */
              e.currentTarget.style.display = "none";
            }}
          />

          <div className={styles.heroCopy}>
            <Eyebrow>Personal fashion intelligence</Eyebrow>
            <h1 className={styles.heroTitle}>DEDUNET</h1>
            <p className={styles.heroPromise}>
              Decide what to wear. Then find it.
            </p>
            <p className={styles.heroLede}>
              Tell Dido where you are going and what you are working with. It builds complete
              looks, explains why each piece is there, and traces every one back to the brand
              that makes it.
            </p>
            <div className={styles.heroCtas}>
              <ButtonLink to="/dido" variant="accent">
                Style with Dido
              </ButtonLink>
              <ButtonLink to="/discover" variant="secondary">
                Discover looks
              </ButtonLink>
            </div>
          </div>

          <div className={styles.heroMedia}>
            <Media
              src={brand.assets.hero}
              alt="DEDUNET concept artwork for the first capsule"
              ratio="editorial"
              slot="home-hero"
              fit="contain"
              priority
              note="Concept artwork, not product photography"
            />
          </div>
        </div>
      </Container>

      {/* ---------------------------------------------------------- occasions */}
      <Container>
        <Section tight aria-labelledby="occasions-heading">
          <SectionHead
            eyebrow="Start here"
            title="What are you dressing for?"
            level={2}
            id="occasions-heading"
          />
          <div className={styles.occasionGrid} data-testid="occasions">
            {OCCASIONS.map((occasion) => (
              <OccasionCard
                key={occasion.slug}
                to={`/discover/${occasion.slug}`}
                name={occasion.name}
                hint={occasion.hint}
              />
            ))}
          </div>
        </Section>
      </Container>

      {/* ------------------------------------------------------------- looks */}
      <Container>
        <Section tight aria-labelledby="looks-heading">
          <SectionHead
            eyebrow="Complete outfits"
            title="Looks"
            level={2}
            id="looks-heading"
            action={
              <ButtonLink to="/looks" variant="quiet">
                All looks
              </ButtonLink>
            }
          />

          {/* Section 47: these are editorially arranged, not personally selected. Saying
              "selected for you" with no personalisation engine behind it is the kind of
              claim this programme keeps closing. */}
          <Stack gap="tight" style={{ marginBottom: "var(--ds-space-5)" }}>
            <div style={{ display: "flex", gap: "var(--ds-space-2)", flexWrap: "wrap" }}>
              <FixtureBadge>Editorially arranged</FixtureBadge>
            </div>
            <Subtle>
              Assembled by hand from pieces that exist in the catalogue. Personalised
              selection is not built — see My Style for what DEDUNET does and does not know
              about you.
            </Subtle>
          </Stack>

          {catalog.status === "loading" ? <SkeletonGrid count={4} label="Loading looks" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}
          {catalog.status === "success" ? (
            <Rail label="Looks">
              {LOOKS.map((look) => {
                const lead = look.items[0];
                const product = lead ? bySlug(catalog.data, lead.productSlug) : undefined;
                const image = product ? primaryImage(product) : undefined;
                return (
                  <Card
                    key={look.slug}
                    to={`/look/${look.slug}`}
                    title={look.name}
                    brand="DEDUNET"
                    meta={`${look.items.length} pieces · ${look.descriptors.join(", ")}`}
                    image={image?.url}
                    imageAlt={image?.alt_text ?? `Concept artwork for ${look.name}`}
                    slot={`home-look-${look.slug}`}
                    testId="look-card"
                  />
                );
              })}
            </Rail>
          ) : null}
        </Section>
      </Container>

      {/* --------------------------------------------------------------- dido */}
      <Container>
        <Section tight>
          <div className={styles.didoModule}>
            <div className={styles.didoCopy}>
              <Eyebrow style={{ color: "inherit", opacity: 0.7 }}>Meet Dido</Eyebrow>
              <h2 className={styles.didoTitle}>
                Dido Net reads the occasion, not just the catalogue.
              </h2>
              <p className={styles.didoBody}>
                Dido is the styling layer: it asks what you are dressing for, what you already
                own and what you are willing to spend, then assembles complete looks and
                explains each choice.
              </p>
              <div>
                <ButtonLink to="/dido" variant="accent">
                  Start with Dido
                </ButtonLink>
              </div>
              <Subtle style={{ color: "inherit", opacity: 0.6 }}>
                The conversation is built. The intelligence behind it is not — Dido will tell
                you so itself rather than inventing a recommendation.
              </Subtle>
            </div>

            <Media
              src={brand.assets.collection_cover}
              alt="DEDUNET first capsule concept artwork"
              ratio="editorial"
              slot="home-dido"
              fit="contain"
            />
          </div>
        </Section>
      </Container>

      {/* -------------------------------------------------------- the capsule */}
      <Container>
        <Section tight aria-labelledby="capsule-heading">
          <SectionHead
            eyebrow="First Passage / 01"
            title="The capsule"
            level={2}
            id="capsule-heading"
            action={
              <ButtonLink to="/shop" variant="quiet">
                See everything
              </ButtonLink>
            }
          />

          {catalog.status === "loading" ? <SkeletonGrid count={5} label="Loading the capsule" /> : null}
          {catalog.status === "error" ? (
            <ErrorState error={catalog.error} onRetry={catalog.retry} />
          ) : null}
          {catalog.status === "success" ? (
            <Grid>
              {(catalog.data ?? []).map((product) => {
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
                    footer={<Badge tone="neutral" dot>Preview</Badge>}
                  />
                );
              })}
            </Grid>
          ) : null}
        </Section>
      </Container>

      {/* ------------------------------------------------------------ by style */}
      <Container>
        <Section tight aria-labelledby="style-heading">
          <SectionHead eyebrow="Another way in" title="By style" level={2} id="style-heading" />
          <div className={styles.occasionGrid}>
            {STYLE_CATEGORIES.map((category) => (
              <OccasionCard
                key={category.slug}
                to={`/discover/${category.slug}`}
                name={category.name}
                hint={category.description}
              />
            ))}
          </div>
        </Section>
      </Container>

      {/* ---------------------------------------------------------- for brands */}
      <Container>
        <Section tight>
          <div className={styles.editorialBand}>
            <Media
              src={brand.assets.about}
              alt="DEDUNET brand concept artwork"
              ratio="editorial"
              slot="home-for-brands"
              fit="contain"
            />
            <div className={styles.editorialCopy}>
              <Eyebrow>For brands</Eyebrow>
              <h2>Reach customers through styling, not search.</h2>
              <p>
                DEDUNET puts a brand in front of someone who has already described the
                occasion, the fit and the budget. That is a different kind of placement from a
                search result, and a different kind of customer.
              </p>
              <div>
                <ButtonLink to="/for-brands" variant="secondary">
                  DEDUNET for Brands
                </ButtonLink>
              </div>
              <Subtle>
                DEDUNET is not accepting brands and has no commercial agreement with any.
              </Subtle>
            </div>
          </div>
        </Section>
      </Container>

      {/* -------------------------------------------------------- continue */}
      <Container>
        <Section tight>
          <Stack gap="loose">
            <SectionHead eyebrow="Pick up where you left off" title="Continue" level={2} />
            <div style={{ display: "flex", gap: "var(--ds-space-3)", flexWrap: "wrap" }}>
              <ButtonLink to="/saved" variant="quiet">
                Saved
              </ButtonLink>
              <ButtonLink to="/my-style" variant="quiet">
                My Style
              </ButtonLink>
              <ButtonLink to="/brands" variant="quiet">
                Brands
              </ButtonLink>
            </div>
          </Stack>
        </Section>
      </Container>
    </>
  );
}
