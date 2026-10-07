import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button, ButtonLink } from "../../components/Button";
import { SelectField, TextField } from "../../components/Field";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  SectionHead,
  Stack,
  Subtle,
} from "../../components/primitives";
import { EmptyState, ErrorState } from "../../components/States";
import {
  deleteStyleProfile,
  fetchStyleOptions,
  fetchStyleProfile,
  patchStyleProfile,
} from "../../api/endpoints";
import { onSessionChange, session } from "../../api/client";
import type { StyleOptions, StyleProfile, StyleTerm } from "../../api/types";
import { fetchBrands } from "../../api/endpoints";
import {
  BudgetFormatError,
  SECTION_COUNT,
  buildPatch,
  cycleBrandStance,
  cycleStance,
  draftFromProfile,
  fitOf,
  isDirty,
  saveErrorMessage,
  sectionsWithPreferences,
  setFit,
  setSize,
  sizeOf,
  stanceOf,
  toggleSingle,
  type StyleDraft,
} from "./styleDraft";
import styles from "./MyStylePage.module.css";

/**
 * My Style — the Style DNA editor.
 *
 * WHAT THIS PAGE IS ALLOWED TO SAY.
 *
 * Only what the customer told us. There is no score, no percentage, no "82% minimalist"
 * and no confidence meter anywhere on it, because there is no model behind the page to
 * produce one. Completion is reported as "N of 5 sections" -- a fact the reader can check
 * against what is in front of them.
 *
 * Every value carries "Set by you", and that label is currently true of every row in the
 * database by database constraint, not by convention. If a later phase adds inferred
 * signals they will arrive with a different source and will have to be labelled
 * differently here, which is the point of showing the label now.
 *
 * SAVED ACTIVITY IS NOT USED, AND THE PAGE SAYS SO. Leaving that unstated would let a
 * reasonable person assume otherwise -- every other platform does infer -- and an
 * assumption we know people will make is one we are responsible for correcting.
 *
 * TWO CONTROLS, NOT ONE. "Stop using this" and "forget this" are different requests, and a
 * single control that did both would destroy data somebody meant to keep.
 */

const SECTION_TITLES = [
  "How you dress",
  "Colour",
  "Fit and size",
  "Material",
  "Brands and budget",
] as const;

type Brand = { slug: string; name: string; is_development_fixture?: boolean };

export default function MyStylePage() {
  const [signedIn, setSignedIn] = useState(() => Boolean(session.token));
  const [options, setOptions] = useState<StyleOptions | null>(null);
  const [profile, setProfile] = useState<StyleProfile | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [draft, setDraft] = useState<StyleDraft | null>(null);
  const [original, setOriginal] = useState<StyleDraft | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [conflict, setConflict] = useState(false);
  const liveRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    document.title = "My Style — DEDUNET";
  }, []);

  useEffect(() => onSessionChange(() => setSignedIn(Boolean(session.token))), []);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadError(null);
    try {
      /* ONE round of requests for the whole page: vocabulary, profile, brand list.
       * Not one request per preference, and not a catalogue fetch -- the brand list is
       * the existing brands endpoint, which is already small and already cached. */
      const [opts, prof, brandPayload] = await Promise.all([
        fetchStyleOptions(signal),
        session.token ? fetchStyleProfile(signal) : Promise.resolve(null),
        fetchBrands(signal).catch(() => null),
      ]);
      setOptions(opts);
      const list = Array.isArray(brandPayload)
        ? (brandPayload as Brand[])
        : ((brandPayload as { items?: Brand[] } | null)?.items ?? []);
      // Development fixtures are never offered as something to follow: the server refuses
      // them, and showing a choice the server rejects is a trap rather than an option.
      setBrands(list.filter((b) => !b.is_development_fixture));
      if (prof) {
        setProfile(prof);
        const next = draftFromProfile(prof);
        setDraft(next);
        setOriginal(next);
      }
    } catch (error) {
      if ((error as { name?: string }).name !== "AbortError") setLoadError(error);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load, signedIn]);

  const dirty = draft && original ? isDirty(draft, original) : false;
  const filled = draft ? sectionsWithPreferences(draft) : 0;

  const update = useCallback((patch: Partial<StyleDraft>) => {
    setSaveError(null);
    setConflict(false);
    setSavedAt(null);
    setDraft((current) => (current ? { ...current, ...patch } : current));
  }, []);

  const save = useCallback(async () => {
    if (!draft || !original) return;
    setSaving(true);
    setSaveError(null);
    try {
      const patch = buildPatch(draft, original);
      if (!Object.keys(patch).length) {
        setSaving(false);
        return;
      }
      const updated = await patchStyleProfile(patch, profile?.exists ? profile.revision : 0);
      setProfile(updated);
      const next = draftFromProfile(updated);
      setDraft(next);
      setOriginal(next);
      setSavedAt(Date.now());
    } catch (error) {
      if (error instanceof BudgetFormatError) {
        setSaveError(error.message);
      } else {
        if ((error as { status?: number }).status === 409) setConflict(true);
        setSaveError(saveErrorMessage(error));
      }
    } finally {
      setSaving(false);
    }
  }, [draft, original, profile]);

  const remove = useCallback(async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const result = await deleteStyleProfile();
      setProfile(result.profile);
      const next = draftFromProfile(result.profile);
      setDraft(next);
      setOriginal(next);
      setConfirmingDelete(false);
      setSavedAt(null);
    } catch (error) {
      setSaveError(saveErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }, []);

  if (!signedIn) {
    return (
      <Container>
        <Section>
          <Stack gap="loose">
            <Header filled={0} exists={false} />
            <EmptyState
              title="Sign in to build your Style DNA"
              body="Your Style DNA is kept to your account rather than to this browser, so it is the same wherever you sign in."
              action={
                <ButtonLink to="/account?next=/my-style" variant="primary">
                  Sign in
                </ButtonLink>
              }
            />
          </Stack>
        </Section>
      </Container>
    );
  }

  if (loadError) {
    return (
      <Container>
        <Section>
          <ErrorState
            title="My Style could not be loaded"
            body="DEDUNET could not reach the server."
            action={<Button onClick={() => void load()}>Try again</Button>}
          />
        </Section>
      </Container>
    );
  }

  if (!options || !draft) {
    return (
      <Container>
        <Section>
          <p data-testid="style-loading">Loading your Style DNA…</p>
        </Section>
      </Container>
    );
  }

  const disabled = saving;

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Header filled={filled} exists={Boolean(profile?.exists)} />

          {/* The one sentence that stops a reasonable assumption. */}
          <Subtle data-testid="saved-boundary-notice">
            Saved activity is not currently used to infer your Style DNA. Everything below is
            here because you chose it.
          </Subtle>

          {profile?.exists && !draft.personalizationEnabled ? (
            <p className={styles.disabledBanner} data-testid="personalisation-off-banner">
              Personalisation is off. Your Style DNA is kept exactly as it is and is not being
              used.
            </p>
          ) : null}

          {conflict ? (
            <p className={styles.conflict} role="alert" data-testid="style-conflict">
              You changed your Style DNA somewhere else.{" "}
              <Button variant="secondary" onClick={() => void load()}>
                Reload the latest version
              </Button>
            </p>
          ) : null}

          {/* ---------------------------------------------------------- 1. how you dress */}
          <EditorSection title={SECTION_TITLES[0]} testId="section-how-you-dress"
            body="The styles you gravitate to, and the ones you never wear.">
            <StanceGrid
              terms={options.style_directions}
              entries={draft.styleDirections}
              onToggle={(slug) =>
                update({ styleDirections: cycleStance(draft.styleDirections, slug) })
              }
              disabled={disabled}
              groupLabel="Style directions"
            />
          </EditorSection>

          {/* ---------------------------------------------------------------- 2. colour */}
          <EditorSection title={SECTION_TITLES[1]} testId="section-colour"
            body="What you reach for, and what you have decided against.">
            <StanceGrid
              terms={options.colours}
              entries={draft.colours}
              onToggle={(slug) => update({ colours: cycleStance(draft.colours, slug) })}
              disabled={disabled}
              groupLabel="Colours"
            />
            <SingleChoice
              legend="How you want colour to work"
              terms={options.colour_approaches}
              value={draft.colourApproach}
              onChange={(slug) => update({ colourApproach: toggleSingle(draft.colourApproach, slug) })}
              disabled={disabled}
              testId="colour-approach"
            />
          </EditorSection>

          {/* --------------------------------------------------------- 3. fit and size */}
          <EditorSection title={SECTION_TITLES[2]} testId="section-fit-and-size"
            body="How you like things to sit, and the sizes you already know.">
            <div className={styles.rows}>
              {options.garment_categories.map((category) => (
                <div key={category.slug} className={styles.row}>
                  <SelectField
                    label={`${category.label} — fit`}
                    value={fitOf(draft.fits, category.slug) ?? ""}
                    disabled={disabled}
                    data-testid={`fit-${category.slug}`}
                    onChange={(event) =>
                      update({
                        fits: setFit(draft.fits, category.slug, event.target.value || null),
                      })
                    }
                  >
                    <option value="">Not set</option>
                    {options.fits.map((fit) => (
                      <option key={fit.slug} value={fit.slug}>
                        {fit.label}
                      </option>
                    ))}
                  </SelectField>
                  <SizeRow
                    category={category}
                    systems={options.size_systems}
                    draft={draft}
                    disabled={disabled}
                    maxLength={options.limits.size_label_length ?? 12}
                    onChange={(system, label) =>
                      update({ sizes: setSize(draft.sizes, category.slug, system, label) })
                    }
                  />
                </div>
              ))}
            </div>
            {/* Stated as a fact about the platform, not as a disclaimer in small print. */}
            <Subtle>
              Sizes are kept exactly as you state them. DEDUNET does not convert between size
              systems or between brands, because those equivalences are approximate everywhere
              and exact nowhere.
            </Subtle>
            <TextField
              label="Fit notes"
              optional
              hint={`Anything about how clothes fit you. ${options.limits.fit_notes_length ?? 280} characters.`}
              value={draft.fitNotes}
              maxLength={options.limits.fit_notes_length ?? 280}
              disabled={disabled}
              data-testid="fit-notes"
              onChange={(event) => update({ fitNotes: event.target.value })}
            />
          </EditorSection>

          {/* -------------------------------------------------------------- 4. material */}
          <EditorSection title={SECTION_TITLES[3]} testId="section-material"
            body="What your skin, your climate and your principles allow.">
            <StanceGrid
              terms={options.materials}
              entries={draft.materials}
              onToggle={(slug) => update({ materials: cycleStance(draft.materials, slug) })}
              disabled={disabled}
              groupLabel="Materials"
            />
            <SingleChoice
              legend="Care effort"
              terms={options.care_efforts}
              value={draft.careEffort}
              onChange={(slug) => update({ careEffort: toggleSingle(draft.careEffort, slug) })}
              disabled={disabled}
              testId="care-effort"
            />
            <SingleChoice
              legend="Climate"
              terms={options.seasonalities}
              value={draft.seasonality}
              onChange={(slug) => update({ seasonality: toggleSingle(draft.seasonality, slug) })}
              disabled={disabled}
              testId="seasonality"
            />
            <Subtle>
              A material preference is about you, not about any garment. DEDUNET does not treat
              it as evidence that a product is made of anything — composition stays stated and
              unverified until supplier documents and testing say otherwise.
            </Subtle>
          </EditorSection>

          {/* ------------------------------------------------------ 5. brands and budget */}
          <EditorSection title={SECTION_TITLES[4]} testId="section-brands-and-budget"
            body="Who you already trust, and what a piece is worth to you.">
            {brands.length ? (
              <fieldset className={styles.fieldset}>
                <legend className={styles.legend}>Brands</legend>
                <div className={styles.chips} role="group" aria-label="Brands">
                  {brands.map((brand) => {
                    const stance = stanceOf(draft.brands, brand.slug);
                    return (
                      <StanceChip
                        key={brand.slug}
                        label={brand.name}
                        stance={stance}
                        disabled={disabled}
                        testId={`brand-${brand.slug}`}
                        onClick={() =>
                          update({ brands: cycleBrandStance(draft.brands, brand.slug, brand.name) })
                        }
                      />
                    );
                  })}
                </div>
                <Subtle>
                  Following a brand is your preference and nothing more. DEDUNET has no
                  partnership, endorsement or commercial agreement with any brand.
                </Subtle>
              </fieldset>
            ) : null}

            <div className={styles.rows}>
              <TextField
                label={`Budget per piece (${draft.currency})`}
                optional
                inputMode="decimal"
                hint="What one garment is worth to you."
                value={draft.budgetPerPiece}
                disabled={disabled}
                data-testid="budget-per-piece"
                onChange={(event) => update({ budgetPerPiece: event.target.value })}
              />
              <TextField
                label={`Budget per look (${draft.currency})`}
                optional
                inputMode="decimal"
                hint="What a complete outfit is worth to you."
                value={draft.budgetPerLook}
                disabled={disabled}
                data-testid="budget-per-look"
                onChange={(event) => update({ budgetPerLook: event.target.value })}
              />
            </div>
            <Subtle>
              A budget is what you told DEDUNET you want to spend. It is not an estimate of what
              you can afford, and nothing here infers your income.
            </Subtle>
          </EditorSection>

          {/* ------------------------------------------------------------- the controls */}
          <section aria-labelledby="personalisation-controls" className={styles.controls}>
            <SectionHead
              eyebrow="Your control"
              title="Personalisation"
              level={2}
              id="personalisation-controls"
            />
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={draft.personalizationEnabled}
                disabled={disabled}
                data-testid="personalisation-toggle"
                onChange={(event) => update({ personalizationEnabled: event.target.checked })}
              />
              <span>Use my Style DNA for personalisation</span>
            </label>
            <Subtle>
              Switching this off keeps everything you have told DEDUNET and stops it being used.
              It does not delete anything — deleting is the separate control below.
            </Subtle>

            <div className={styles.actions}>
              <Button onClick={() => void save()} disabled={disabled || !dirty} data-testid="style-save">
                {saving ? "Saving…" : "Save Style DNA"}
              </Button>
              {profile?.exists ? (
                confirmingDelete ? (
                  <span className={styles.confirm} data-testid="delete-confirm">
                    <span>Delete everything in your Style DNA? Your saved items and account are
                      not affected.</span>
                    <Button variant="secondary" onClick={() => void remove()} disabled={disabled}
                      data-testid="delete-confirm-yes">
                      Yes, delete it
                    </Button>
                    <Button variant="ghost" onClick={() => setConfirmingDelete(false)}
                      disabled={disabled}>
                      Keep it
                    </Button>
                  </span>
                ) : (
                  <Button variant="ghost" onClick={() => setConfirmingDelete(true)}
                    disabled={disabled} data-testid="style-delete">
                    Delete my Style DNA
                  </Button>
                )
              ) : null}
            </div>

            <p className={styles.live} role="status" aria-live="polite" ref={liveRef}
              data-testid="style-status">
              {saveError
                ? saveError
                : savedAt
                  ? "Your Style DNA is saved."
                  : dirty
                    ? "You have unsaved changes."
                    : ""}
            </p>
          </section>

          <Subtle>
            Dido does not use your Style DNA yet. It is stored, and it is yours to change or
            delete. <Link to="/dido">See what Dido can and cannot do</Link>.
          </Subtle>
        </Stack>
      </Section>
    </Container>
  );
}

function Header({ filled, exists }: { filled: number; exists: boolean }) {
  return (
    <Stack gap="tight">
      <Eyebrow>Style DNA</Eyebrow>
      <h1>My Style</h1>
      <Lede>
        What you have told DEDUNET about how you dress. Nothing here is guessed, and you can
        change or delete any of it.
      </Lede>
      {exists ? (
        /* A COUNT, never a percentage. There is no model to produce a score. */
        <p className={styles.completeness} data-testid="style-completeness">
          {filled} of {SECTION_COUNT} sections contain preferences
        </p>
      ) : null}
    </Stack>
  );
}

function EditorSection({
  title,
  body,
  testId,
  children,
}: {
  title: string;
  body: string;
  testId: string;
  children: React.ReactNode;
}) {
  return (
    <section className={styles.group} data-testid={testId}>
      <SectionHead eyebrow="Section" title={title} level={2} />
      <p className={styles.groupBody}>{body}</p>
      <Stack gap="base">{children}</Stack>
    </section>
  );
}

function StanceChip({
  label,
  stance,
  onClick,
  disabled,
  testId,
}: {
  label: string;
  stance: "PREFERRED" | "AVOIDED" | null;
  onClick: () => void;
  disabled?: boolean;
  testId: string;
}) {
  /* One control, three states. aria-pressed carries the binary "is this selected", and the
   * visible text carries which of the two selected meanings it is -- a screen reader user
   * should not have to infer "avoided" from a colour. */
  const spoken = stance === "PREFERRED" ? "preferred" : stance === "AVOIDED" ? "avoided" : "not set";
  return (
    <button
      type="button"
      className={styles.chip}
      data-stance={stance ?? "unset"}
      data-testid={testId}
      aria-pressed={stance !== null}
      aria-label={`${label}: ${spoken}. Activate to change.`}
      disabled={disabled}
      onClick={onClick}
    >
      <span className={styles.chipLabel}>{label}</span>
      <span className={styles.chipState}>
        {stance === "PREFERRED" ? "Like" : stance === "AVOIDED" ? "Avoid" : "—"}
      </span>
    </button>
  );
}

function StanceGrid({
  terms,
  entries,
  onToggle,
  disabled,
  groupLabel,
}: {
  terms: StyleTerm[];
  entries: { slug: string; stance: "PREFERRED" | "AVOIDED" }[];
  onToggle: (slug: string) => void;
  disabled: boolean;
  groupLabel: string;
}) {
  const chosen = useMemo(() => entries.length, [entries]);
  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.legend}>
        {groupLabel}
        <span className={styles.legendHint}>
          {chosen ? `${chosen} set by you` : "Tap once to like, twice to avoid"}
        </span>
      </legend>
      <div className={styles.chips} role="group" aria-label={groupLabel}>
        {terms.map((term) => (
          <StanceChip
            key={term.slug}
            label={term.label}
            stance={stanceOf(entries, term.slug)}
            disabled={disabled}
            testId={`chip-${term.slug}`}
            onClick={() => onToggle(term.slug)}
          />
        ))}
      </div>
    </fieldset>
  );
}

function SingleChoice({
  legend,
  terms,
  value,
  onChange,
  disabled,
  testId,
}: {
  legend: string;
  terms: StyleTerm[];
  value: string | null;
  onChange: (slug: string) => void;
  disabled: boolean;
  testId: string;
}) {
  return (
    <fieldset className={styles.fieldset} data-testid={testId}>
      <legend className={styles.legend}>{legend}</legend>
      <div className={styles.chips} role="group" aria-label={legend}>
        {terms.map((term) => (
          <button
            key={term.slug}
            type="button"
            className={styles.chip}
            data-stance={value === term.slug ? "PREFERRED" : "unset"}
            data-testid={`${testId}-${term.slug}`}
            aria-pressed={value === term.slug}
            disabled={disabled}
            onClick={() => onChange(term.slug)}
          >
            <span className={styles.chipLabel}>{term.label}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function SizeRow({
  category,
  systems,
  draft,
  disabled,
  maxLength,
  onChange,
}: {
  category: StyleTerm;
  systems: StyleTerm[];
  draft: StyleDraft;
  disabled: boolean;
  maxLength: number;
  onChange: (system: string, label: string) => void;
}) {
  /* One visible size input per category, plus the system it is stated in. Showing all six
   * systems per category would be twenty-four inputs on a phone to express something most
   * people know one way. A customer who knows two can switch the system and add the other;
   * both are kept, and neither is derived from the other. */
  const existing = draft.sizes.filter((s) => s.garment_category === category.slug);
  const [system, setSystem] = useState(existing[0]?.size_system ?? "ALPHA");
  const label = sizeOf(draft.sizes, category.slug, system);

  return (
    <div className={styles.sizeRow}>
      <SelectField
        label={`${category.label} — size system`}
        value={system}
        disabled={disabled}
        data-testid={`size-system-${category.slug}`}
        onChange={(event) => setSystem(event.target.value)}
      >
        {systems.map((s) => (
          <option key={s.slug} value={s.slug}>
            {s.label}
          </option>
        ))}
      </SelectField>
      <TextField
        label={`${category.label} — your size`}
        optional
        value={label}
        maxLength={maxLength}
        disabled={disabled}
        data-testid={`size-${category.slug}`}
        onChange={(event) => onChange(system, event.target.value)}
      />
      {existing.length > 1 ? (
        <p className={styles.alsoStated} data-testid={`size-also-${category.slug}`}>
          Also stated:{" "}
          {existing
            .filter((s) => s.size_system !== system)
            .map((s) => `${s.size_system} ${s.size_label}`)
            .join(", ")}
        </p>
      ) : null}
    </div>
  );
}
