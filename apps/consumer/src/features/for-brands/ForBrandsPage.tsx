import { useEffect } from "react";
import { ButtonLink } from "../../components/Button";
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
import { brand } from "../../lib/brand";
import styles from "./ForBrandsPage.module.css";

const PITCH = [
  {
    title: "Intent, not keywords",
    body: "A customer reaches DEDUNET having already said what the occasion is, what they are willing to spend and what fits them. A brand is placed against that, not against a search term.",
  },
  {
    title: "The whole outfit",
    body: "Pieces are shown inside complete looks, so a brand appears in the context that makes it make sense rather than as a lone thumbnail in a grid.",
  },
  {
    title: "Your identity stays yours",
    body: "A brand on DEDUNET keeps its own name, story and imagery. Where it sells is a separate decision from who owns it.",
  },
  {
    title: "For brands without a shop",
    body: "A brand with no site of its own can be hosted on DEDUNET: a catalogue, a brand page and order routing, without building a storefront first.",
  },
];

/**
 * DEDUNET for Brands.
 *
 * The one page on this platform most likely to overstate. It describes an intended
 * proposition and it must not read as an open programme: there is no merchant backend, no
 * onboarding, no contract and no partner. The honesty block is not a footnote at the bottom
 * — it is a section with its own heading, at the size a reader will actually see.
 */
export default function ForBrandsPage() {
  useEffect(() => {
    document.title = "DEDUNET for Brands";
  }, []);

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <div className={styles.hero}>
            <div className={styles.heroCopy}>
              <Eyebrow>DEDUNET for Brands</Eyebrow>
              <h1>Reach customers through styling intelligence.</h1>
              <Lede>
                DEDUNET puts a brand in front of someone who has already described the
                occasion, the fit and the budget — a different kind of placement, and a
                different kind of customer, from a search result.
              </Lede>
            </div>

            <Media
              src={brand.assets.email_banner}
              alt="DEDUNET brand concept artwork"
              ratio="editorial"
              slot="for-brands-hero"
              fit="contain"
            />
          </div>

          <section aria-labelledby="pitch-heading" data-testid="for-brands-pitch">
            <SectionHead
              eyebrow="The proposition"
              title="What DEDUNET intends to offer"
              level={2}
              id="pitch-heading"
            />
            <Grid variant="two">
              {PITCH.map((item) => (
                <article key={item.title} className={styles.pitchItem}>
                  <h3 className={styles.pitchTitle}>{item.title}</h3>
                  <p className={styles.pitchBody}>{item.body}</p>
                </article>
              ))}
            </Grid>
          </section>

          {/* The honesty section. A heading, not fine print. */}
          <section
            aria-labelledby="honesty-heading"
            className={styles.honesty}
            data-testid="for-brands-honesty"
          >
            <h2 id="honesty-heading" className={styles.honestyTitle}>
              What is true today
            </h2>

            <ul className={styles.honestyList}>
              <li>
                <strong>DEDUNET is not accepting brands.</strong> There is no application, no
                waiting list and no way to sign up from this page.
              </li>
              <li>
                <strong>There are no commercial agreements with any brand.</strong> Nothing on
                this platform is a partnership, and no brand shown here has one.
              </li>
              <li>
                <strong>The merchant platform is not built.</strong> There is no merchant
                account, no catalogue upload, no inventory, no order routing, no analytics and
                no billing. Not a limited version of those — none of them.
              </li>
              <li>
                <strong>The styling intelligence described above does not exist yet.</strong>{" "}
                Dido cannot style anyone today, and the recommendation and outfit engines are
                not built.
              </li>
              <li>
                <strong>DEDUNET itself is a prototype.</strong> No company, factory, supplier
                or certification exists, and the brand is not legally cleared.
              </li>
            </ul>

            <Subtle>
              This page describes an intention. Everything on it is a plan rather than a
              product, and it says so here rather than at the foot of the page.
            </Subtle>
          </section>

          <div style={{ display: "flex", gap: "var(--ds-space-3)", flexWrap: "wrap" }}>
            <ButtonLink to="/brands" variant="secondary">
              See how brands appear
            </ButtonLink>
            <ButtonLink to="/" variant="quiet">
              Back to DEDUNET
            </ButtonLink>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
