import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button, ButtonLink } from "../../components/Button";
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
import { onSessionChange, session as apiSession } from "../../api/client";
import {
  completeDidoSession,
  correctDidoBrief,
  deleteDidoSession,
  fetchCurrentDidoSession,
  fetchDidoInUse,
  fetchDidoOptions,
  sendDidoMessage,
  startDidoSession,
} from "../../api/endpoints";
import type {
  BriefEntry,
  DidoInUse,
  DidoOptions,
  DidoSessionPayload,
} from "../../api/types";
import { DidoFigure, type DidoState } from "./DidoFigure";
import {
  countedEntries,
  degradedNotice,
  didoErrorMessage,
  labelFor,
  newMessageId,
  stateFor,
  valueFor,
  type DidoUiState,
} from "./didoState";
import styles from "./DidoPage.module.css";

/**
 * Style with Dido — the conversational styling intake.
 *
 * WHAT CHANGED, AND WHAT DELIBERATELY DID NOT.
 *
 * The shell is gone: this talks to a real server-side conversation that understands free
 * text, applies accepted Style DNA when personalisation is on, and accumulates a
 * structured Styling Brief. The old disclosure — "this is the conversation, not the
 * intelligence" — was true and is now false, so it had to go.
 *
 * What replaced it is NOT silence. The boundary moved; it did not disappear. Dido
 * understands and records. It does not rank products, build outfits, check availability
 * or know what anything costs beyond what it was told, and the page says so in the place
 * a customer would otherwise assume otherwise: at the end, where a recommendation would
 * have gone.
 *
 * THE BRIEF IS THE AUTHORITY, NOT THE PROSE. Every value on the review panel comes from
 * the server's structured brief, grouped by where it came from. Dido's sentences are
 * composed server-side from that same state, so the two cannot disagree.
 *
 * THE FIGURE ONLY SHOWS STATES THAT EXIST. `DidoFigure` can depict searching, styling,
 * comparing and assembling. None of those happens, so none of them is used here — an
 * animation implying a catalogue search would be a fake capability with no words to
 * correct it.
 */

/** Figure states this page is allowed to use. See the note above. */
const FIGURE_FOR: Record<DidoUiState, DidoState> = {
  loading: "idle",
  "signed-out": "idle",
  welcome: "welcome",
  listening: "listening",
  interpreting: "thinking",
  asking: "asking",
  conflict: "asking",
  "brief-ready": "success",
  completed: "success",
  degraded: "error",
  "rate-limited": "error",
  error: "error",
};

export default function DidoPage() {
  const [signedIn, setSignedIn] = useState(() => Boolean(apiSession.token));
  const [options, setOptions] = useState<DidoOptions | null>(null);
  const [session, setSession] = useState<DidoSessionPayload | null>(null);
  const [pending, setPending] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [inUse, setInUse] = useState<DidoInUse | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const logEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  /** Held so a retry reuses the key rather than storing the message twice. */
  const messageIdRef = useRef<string>(newMessageId());

  useEffect(() => {
    document.title = "Style with Dido — DEDUNET";
  }, []);

  useEffect(() => onSessionChange(() => setSignedIn(Boolean(apiSession.token))), []);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadError(null);
    try {
      const [opts, current] = await Promise.all([
        fetchDidoOptions(signal),
        apiSession.token
          ? fetchCurrentDidoSession(signal)
          : Promise.resolve({ session: null }),
      ]);
      setOptions(opts);
      setSession(current.session);
    } catch (err) {
      if ((err as { name?: string }).name !== "AbortError") setLoadError(err);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load, signedIn]);

  const uiState = stateFor(session, { pending, signedIn });

  /* Scroll the newest turn into view WITHOUT moving focus.
   * Stealing focus on every reply would throw a screen-reader user out of whatever they
   * were reading, and would fight a keyboard user mid-sentence. The log is a polite live
   * region; it announces itself. */
  useEffect(() => {
    if (!session?.turns?.length) return;
    logEndRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [session?.turns?.length]);

  const begin = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setSession(await startDidoSession());
      setInUse(null);
    } catch (err) {
      setError(didoErrorMessage(err));
    } finally {
      setPending(false);
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      // Guards the double submit that keeping the textarea enabled makes possible.
      if (!session || !text.trim() || pending) return;
      setPending(true);
      setError(null);
      try {
        const updated = await sendDidoMessage(
          session.session_id,
          text.trim(),
          session.revision,
          messageIdRef.current,
        );
        setSession(updated);
        setDraft("");
        // A new key only once the message has landed; a failed send keeps its key so a
        // retry is recognised as the same message.
        messageIdRef.current = newMessageId();
      } catch (err) {
        setError(didoErrorMessage(err));
      } finally {
        setPending(false);
      }
    },
    [session, pending],
  );

  const complete = useCallback(async () => {
    if (!session) return;
    setPending(true);
    try {
      setSession(await completeDidoSession(session.session_id));
    } catch (err) {
      setError(didoErrorMessage(err));
    } finally {
      setPending(false);
    }
  }, [session]);

  const remove = useCallback(async () => {
    if (!session) return;
    setPending(true);
    try {
      await deleteDidoSession(session.session_id);
      setSession(null);
      setInUse(null);
    } catch (err) {
      setError(didoErrorMessage(err));
    } finally {
      setPending(false);
    }
  }, [session]);

  const askWhatYouKnow = useCallback(async () => {
    if (!session) return;
    try {
      setInUse(await fetchDidoInUse(session.session_id));
    } catch (err) {
      setError(didoErrorMessage(err));
    }
  }, [session]);

  const correct = useCallback(
    async (field: string, value: unknown) => {
      if (!session) return;
      setPending(true);
      try {
        setSession(await correctDidoBrief(session.session_id, { [field]: value }, session.revision));
      } catch (err) {
        setError(didoErrorMessage(err));
      } finally {
        setPending(false);
      }
    },
    [session],
  );

  // ---- shells -------------------------------------------------------------

  if (loadError) {
    return (
      <Container>
        <Section>
          <ErrorState error={loadError} onRetry={() => void load()} testId="dido-error" />
        </Section>
      </Container>
    );
  }

  if (!signedIn) {
    return (
      <Container>
        <Section>
          <Stack gap="loose">
            <Header />
            <Boundary />
            <EmptyState
              title="Sign in to style with Dido"
              body="A styling conversation is kept to your account, so you can leave it and come back to it on any device."
              action={
                <ButtonLink to="/account?next=/dido" variant="primary">
                  Sign in
                </ButtonLink>
              }
            />

            {/* A SIGNED-OUT VISITOR STILL SEES WHAT DIDO WILL ASK.
              *
              * The same mistake I made on My Style, caught by the same substance test:
              * replacing a page with a sign-in panel tells a visitor nothing about what
              * they are being asked to sign in FOR. "Sign in to find out what we want to
              * know about you" is a worse offer than showing them.
              *
              * The vocabularies are public because they are the platform's words rather
              * than anybody's data, which is what makes this possible without a session
              * and keeps it from drifting from what the conversation actually offers. */}
            {options ? (
              <div data-testid="dido-preview">
                <Stack gap="loose">
                  {([
                    ["What you are dressing for", options.occasions],
                    ["How formal it needs to be", options.dress_codes],
                    ["Where it is", options.settings],
                  ] as [string, { slug: string; label: string }[]][]).map(([title, terms]) => (
                    <section key={title} className={styles.previewGroup}>
                      <SectionHead eyebrow="Dido asks about" title={title} level={2} />
                      <ul className={styles.previewList}>
                        {terms.map((term) => (
                          <li key={term.slug} className={styles.previewItem}>
                            {term.label}
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </Stack>
              </div>
            ) : null}

            <Subtle>
              Dido asks one thing at a time and only what it still needs. If you have a Style
              DNA and personalisation is on, it starts from that instead of asking again.
            </Subtle>
          </Stack>
        </Section>
      </Container>
    );
  }

  if (!options) {
    return (
      <Container>
        <Section>
          <p data-testid="dido-loading">Loading…</p>
        </Section>
      </Container>
    );
  }

  const question = session?.next_question ?? null;
  const guided = question ? guidedOptionsFor(question.key, options) : [];

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Header />
          <Boundary />

          <div className={styles.stage}>
            <div className={styles.figureWrap}>
              <DidoFigure state={FIGURE_FOR[uiState]} />
              <p className={styles.stateLabel} data-testid="dido-state">
                {STATE_COPY[uiState]}
              </p>
            </div>

            <div className={styles.conversation} data-testid="dido-convo">
              {!session ? (
                <div className={styles.options}>
                  <p className={styles.optionsPrompt}>
                    Tell Dido where you are going and what it needs to be. You can write it
                    however you like.
                  </p>
                  <Button onClick={() => void begin()} disabled={pending} data-testid="dido-start">
                    {pending ? "Starting…" : "Start a styling session"}
                  </Button>
                </div>
              ) : (
                <>
                  <ol
                    className={styles.log}
                    data-testid="dido-log"
                    aria-live="polite"
                    aria-label="Conversation with Dido"
                  >
                    {(session.turns ?? []).map((turn) => (
                      <li
                        key={turn.ordinal}
                        className={turn.role === "DIDO" ? styles.fromDido : styles.fromYou}
                      >
                        <span className={styles.who}>
                          {turn.role === "DIDO" ? "Dido" : "You"}
                        </span>
                        <p className={styles.message}>{turn.body}</p>
                      </li>
                    ))}
                    {pending ? (
                      <li className={styles.fromDido}>
                        <span className={styles.who}>Dido</span>
                        <p className={styles.thinking} aria-label="Dido is reading that">
                          <span />
                          <span />
                          <span />
                        </p>
                      </li>
                    ) : null}
                    <div ref={logEndRef} />
                  </ol>

                  {session.interpretation?.degraded ? (
                    <p className={styles.notice} role="status" data-testid="dido-degraded">
                      {degradedNotice(session.interpretation.reason)}
                    </p>
                  ) : null}

                  {session.brief.contradictions.length ? (
                    <div className={styles.conflict} data-testid="dido-conflict" role="status">
                      <strong>These cannot both be true.</strong>{" "}
                      {session.brief.contradictions[0]?.detail}
                    </div>
                  ) : null}

                  {session.status !== "BRIEF_READY" ? (
                    <form
                      className={styles.composer}
                      onSubmit={(event) => {
                        event.preventDefault();
                        void send(draft);
                      }}
                    >
                      <label className={styles.composerLabel} htmlFor="dido-input">
                        {question ? question.prompt : "Anything else?"}
                      </label>
                      <textarea
                        id="dido-input"
                        ref={inputRef}
                        className={styles.input}
                        value={draft}
                        rows={2}
                        maxLength={options.limits.message_length ?? 1000}
                        /* NOT disabled while sending.
                         *
                         * A disabled element loses focus, so disabling this threw a
                         * keyboard user out of the box they had just pressed Enter in,
                         * on every single message. The send button carries the pending
                         * state instead, and `send` refuses a second submit itself. */
                        readOnly={pending}
                        aria-busy={pending}
                        placeholder="Outdoor wedding next weekend, smart but not too formal, around 300, no wool."
                        data-testid="dido-input"
                        onChange={(event) => setDraft(event.target.value)}
                        onKeyDown={(event) => {
                          // Enter sends; Shift+Enter is a newline. A styling answer is a
                          // sentence, not an essay, so sending is the common case.
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            void send(draft);
                          }
                        }}
                      />
                      <div className={styles.composerRow}>
                        <Button type="submit" disabled={pending || !draft.trim()} data-testid="dido-send">
                          {pending ? "Sending…" : "Send"}
                        </Button>
                        {question ? (
                          <button
                            type="button"
                            className={styles.whyLink}
                            onClick={() => setShowWhy((v) => !v)}
                            data-testid="dido-why"
                          >
                            Why do you need this?
                          </button>
                        ) : null}
                      </div>
                      {showWhy && question ? (
                        <p className={styles.why} data-testid="dido-why-answer">
                          {question.why}
                        </p>
                      ) : null}
                    </form>
                  ) : null}

                  {guided.length && session.status !== "BRIEF_READY" ? (
                    <div className={styles.options} data-testid="dido-options">
                      <div className={styles.optionRow} role="group" aria-label={question?.prompt}>
                        {guided.map((option) => (
                          <button
                            key={option.slug}
                            type="button"
                            className={styles.option}
                            disabled={pending}
                            data-testid={`dido-option-${option.slug}`}
                            onClick={() => void send(option.label)}
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>

          {session ? (
            <BriefPanel
              session={session}
              onCorrect={correct}
              onComplete={complete}
              onDelete={remove}
              onNew={begin}
              onAsk={askWhatYouKnow}
              inUse={inUse}
              pending={pending}
            />
          ) : null}

          {error ? (
            <p className={styles.notice} role="alert" data-testid="dido-message-error">
              {error}
            </p>
          ) : null}
        </Stack>
      </Section>
    </Container>
  );
}

const STATE_COPY: Record<DidoUiState, string> = {
  loading: "Dido is waiting",
  "signed-out": "Dido is waiting",
  welcome: "Dido is ready",
  listening: "Dido is listening",
  interpreting: "Dido is reading that",
  asking: "Dido is asking a question",
  conflict: "Dido found a conflict",
  "brief-ready": "Your brief is ready to review",
  completed: "Your brief is agreed",
  degraded: "Dido could not read that",
  "rate-limited": "Dido is busy",
  error: "Dido could not continue",
};

function Header() {
  return (
    <Stack gap="tight">
      <Eyebrow>Dido Net</Eyebrow>
      <h1>Style with Dido</h1>
      <Lede>
        Tell Dido where you are going. It asks one thing at a time, the way a stylist would,
        rather than handing you a form.
      </Lede>
    </Stack>
  );
}

/**
 * The boundary, stated before the conversation rather than after it.
 *
 * The previous disclosure said there was no intelligence at all. That is no longer true,
 * so repeating it would understate the platform — the same disclosure rule that forbids
 * overstating. What is still true is the harder half: understanding is not recommending.
 */
function Boundary() {
  return (
    <div className={styles.disclosure} data-testid="dido-disclosure" role="note">
      <strong>Dido understands your brief. It does not pick the clothes.</strong> It can read
      what you write, use your Style DNA when personalisation is on, and build a styling brief
      with you. DEDUNET does not yet rank products or assemble outfits from it, and Dido will
      say so rather than inventing a look.
    </div>
  );
}

function guidedOptionsFor(
  key: string,
  options: DidoOptions,
): { slug: string; label: string }[] {
  /* Controlled choices beside the text box, not instead of it.
   * These are what make the degraded path usable: when the interpreter is unavailable the
   * client already holds the vocabulary and can offer real answers without a model. */
  if (key === "occasion") return options.occasions.slice(0, 6);
  if (key === "dress_code") return options.dress_codes;
  if (key === "budget") {
    return [
      { slug: "100", label: "Around 100" },
      { slug: "250", label: "Around 250" },
      { slug: "500", label: "Around 500" },
      { slug: "skip", label: "Rather not say" },
    ];
  }
  return [];
}

function BriefPanel({
  session,
  onCorrect,
  onComplete,
  onDelete,
  onNew,
  onAsk,
  inUse,
  pending,
}: {
  session: DidoSessionPayload;
  onCorrect: (field: string, value: unknown) => void;
  onComplete: () => void;
  onDelete: () => void;
  onNew: () => void;
  onAsk: () => void;
  inUse: DidoInUse | null;
  pending: boolean;
}) {
  const { brief } = session;
  const total = useMemo(() => countedEntries(brief), [brief]);

  return (
    <section className={styles.brief} aria-labelledby="brief-heading" data-testid="dido-brief">
      <SectionHead eyebrow="Your brief" title="What Dido has so far" level={2} id="brief-heading" />

      {/* The personalisation state, said plainly. A customer who turned it off is
          entitled to see that it stayed off. */}
      <p className={styles.personalisation} data-testid="dido-personalisation">
        {session.personalization_used
          ? "Dido is using your Style DNA. The values it took are marked below."
          : "Your Style DNA is not being used — either you have not made one, or personalisation is off."}
      </p>

      {total === 0 ? (
        <Subtle>Nothing yet. Tell Dido what you need and it will fill in.</Subtle>
      ) : (
        <div className={styles.groups}>
          <BriefGroup
            title="From this conversation"
            testId="brief-session"
            entries={[...brief.from_session, ...brief.derived_from_your_words]}
            currency={brief.currency}
            onClear={(field) => onCorrect(field, null)}
            pending={pending}
          />
          <BriefGroup
            title="From your Style DNA"
            testId="brief-style-dna"
            entries={brief.from_style_dna}
            currency={brief.currency}
            onClear={(field) => onCorrect(field, null)}
            pending={pending}
          />
        </div>
      )}

      {brief.size_context.length ? (
        <div className={styles.sizes} data-testid="brief-sizes">
          <h3 className={styles.groupTitle}>Sizes you have stated</h3>
          <ul className={styles.entryList}>
            {brief.size_context.map((size) => (
              <li key={`${size.garment_category}-${size.size_system}`} className={styles.entry}>
                <span className={styles.entryLabel}>{size.garment_category}</span>
                <span className={styles.entryValue}>
                  {size.size_system} {size.size_label}
                </span>
              </li>
            ))}
          </ul>
          <Subtle>
            Kept exactly as you stated them. DEDUNET does not convert between size systems or
            between brands.
          </Subtle>
        </div>
      ) : null}

      {brief.unplaced.length ? (
        <div className={styles.unplaced} data-testid="brief-unplaced">
          <h3 className={styles.groupTitle}>Noted, but not understood</h3>
          <ul className={styles.entryList}>
            {brief.unplaced.map((note) => (
              <li key={note} className={styles.entry}>
                {note}
              </li>
            ))}
          </ul>
          <Subtle>
            Dido kept these rather than dropping them, but has not turned them into
            constraints.
          </Subtle>
        </div>
      ) : null}

      {brief.still_unset.length ? (
        <p className={styles.stillUnset} data-testid="brief-still-unset">
          Still unset: {brief.still_unset.map(labelFor).join(", ")}
        </p>
      ) : null}

      <div className={styles.briefActions}>
        {session.status === "BRIEF_READY" ? (
          <>
            {/* WHERE A RECOMMENDATION WOULD GO. It says what does not exist, because this
                is the exact moment a customer expects an outfit to appear. */}
            <p className={styles.completed} data-testid="dido-completed">
              Your styling brief is ready. <strong>DEDUNET does not yet rank products or
              build the outfit from it.</strong> You can browse the catalogue or look at the
              curated Looks, which are composed by a person.
            </p>
            <ButtonLink to="/looks" variant="secondary">
              See curated Looks
            </ButtonLink>
            <ButtonLink to="/shop" variant="secondary">
              Browse manually
            </ButtonLink>
            <Button variant="quiet" onClick={onNew} disabled={pending} data-testid="dido-new">
              Start a new session
            </Button>
          </>
        ) : (
          <Button
            onClick={onComplete}
            disabled={pending || !brief.ready}
            data-testid="dido-complete"
          >
            {brief.ready ? "Accept this brief" : "Keep going"}
          </Button>
        )}
        <Button variant="quiet" onClick={onAsk} disabled={pending} data-testid="dido-what-you-know">
          What do you know about me?
        </Button>
        <Button variant="quiet" onClick={onDelete} disabled={pending} data-testid="dido-delete">
          Delete this session
        </Button>
      </div>

      {inUse ? (
        <div className={styles.inUse} data-testid="dido-in-use" role="status">
          <p>{inUse.note}</p>
          <p className={styles.inUseDetail}>
            From your Style DNA: {inUse.from_style_dna.length} value
            {inUse.from_style_dna.length === 1 ? "" : "s"} · From this conversation:{" "}
            {inUse.from_this_conversation.length}
          </p>
        </div>
      ) : null}

      <Subtle>
        Nothing you say here changes your Style DNA. <Link to="/my-style">My Style</Link> is the
        only place that does.
      </Subtle>
    </section>
  );
}

function BriefGroup({
  title,
  entries,
  currency,
  onClear,
  pending,
  testId,
}: {
  title: string;
  entries: BriefEntry[];
  currency: string;
  onClear: (field: string) => void;
  pending: boolean;
  testId: string;
}) {
  if (!entries.length) return null;
  return (
    <div className={styles.group} data-testid={testId}>
      <h3 className={styles.groupTitle}>{title}</h3>
      <ul className={styles.entryList}>
        {entries.map((entry) => (
          <li key={entry.field} className={styles.entry}>
            <span className={styles.entryLabel}>{labelFor(entry.field)}</span>
            <span className={styles.entryValue} data-testid={`brief-${entry.field}`}>
              {valueFor(entry, currency)}
            </span>
            <button
              type="button"
              className={styles.clear}
              disabled={pending}
              aria-label={`Remove ${labelFor(entry.field)} from this brief`}
              data-testid={`brief-clear-${entry.field}`}
              onClick={() => onClear(entry.field)}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
