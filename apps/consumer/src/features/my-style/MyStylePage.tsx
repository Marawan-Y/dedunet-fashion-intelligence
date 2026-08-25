import { useEffect } from "react";
import { ButtonLink } from "../../components/Button";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  SectionHead,
  Stack,
  Subtle,
} from "../../components/primitives";
import { NotBuiltState } from "../../components/States";
import { STYLE_CATEGORIES } from "../content";
import styles from "./MyStylePage.module.css";

/**
 * My Style — the foundation for Style DNA.
 *
 * Section 21 is explicit: do not fabricate AI-derived percentages before the Style DNA
 * logic exists. There are no percentages on this page, no "82% minimal", no confidence
 * meters and no inferred profile. Those numbers are the single easiest thing to invent and
 * the single most misleading thing to show, because they imply a model that has looked at
 * something.
 *
 * What is here is the STRUCTURE: the signals DEDUNET would need, named and grouped, with an
 * honest statement of which are collected today. The answer is none.
 */

const SIGNAL_GROUPS: { heading: string; body: string; signals: string[] }[] = [
  {
    heading: "How you dress",
    body: "The styles you gravitate to, and the ones you never wear.",
    signals: STYLE_CATEGORIES.map((c) => c.name),
  },
  {
    heading: "Colour",
    body: "What you reach for, and what you have decided against.",
    signals: ["Favourite colours", "Avoided colours", "Neutrals only", "High contrast"],
  },
  {
    heading: "Fit and size",
    body: "The measurements and the preferences that sit on top of them.",
    signals: ["Sizes", "Preferred fit", "Length preference", "Fit notes"],
  },
  {
    heading: "Material",
    body: "What your skin, your climate and your principles allow.",
    signals: ["Preferred fibres", "Avoided fibres", "Care effort", "Seasonality"],
  },
  {
    heading: "Brands and budget",
    body: "Who you already trust, and what a piece is worth to you.",
    signals: ["Brands you follow", "Brands to exclude", "Budget per piece", "Budget per look"],
  },
];

export default function MyStylePage() {
  useEffect(() => {
    document.title = "My Style — DEDUNET";
  }, []);

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Style DNA</Eyebrow>
            <h1>My Style</h1>
            <Lede>
              Everything DEDUNET would need to know to style you well — and a straight answer
              about how much of it exists today.
            </Lede>
          </Stack>

          <NotBuiltState
            title="DEDUNET knows nothing about you yet"
            body="There is no style profile behind this page. No preference has been collected, nothing has been inferred from what you have looked at, and no score has been calculated. The sections below are the signals the model would use, not a profile of you."
            action={
              <ButtonLink to="/dido" variant="secondary">
                Talk to Dido instead
              </ButtonLink>
            }
          />

          <div data-testid="style-sections">
            <Stack gap="loose">
              {SIGNAL_GROUPS.map((group) => (
                <section key={group.heading} className={styles.group}>
                  <SectionHead eyebrow="Signal" title={group.heading} level={2} />
                  <p className={styles.groupBody}>{group.body}</p>
                  <ul className={styles.signals}>
                    {group.signals.map((signal) => (
                      <li key={signal} className={styles.signal}>
                        {signal}
                        <span className={styles.notSet}>Not set</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </Stack>
          </div>

          <section aria-labelledby="personalisation-controls">
            <SectionHead
              eyebrow="Your control"
              title="Personalisation"
              level={2}
              id="personalisation-controls"
            />
            <Subtle>
              When personalisation exists you will be able to see every signal DEDUNET holds,
              correct it, and switch it off entirely. Building the controls alongside the
              model rather than after it is the point of listing them here first.
            </Subtle>
          </section>
        </Stack>
      </Section>
    </Container>
  );
}
