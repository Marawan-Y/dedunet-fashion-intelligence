import { useEffect, useRef, useState } from "react";
import { ButtonLink } from "../../components/Button";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { OCCASIONS } from "../content";
import { DidoFigure, didoStateLabel, type DidoState } from "./DidoFigure";
import styles from "./DidoPage.module.css";

/* Section 11: Dido asks one useful thing at a time. Never a form. */
interface Turn {
  id: number;
  from: "dido" | "you";
  text: string;
}

type Step = "occasion" | "formality" | "budget" | "done";

const QUESTIONS: Record<Exclude<Step, "done">, { prompt: string; options: string[] }> = {
  occasion: {
    prompt: "Where are you going?",
    options: OCCASIONS.slice(0, 6).map((o) => o.name),
  },
  formality: {
    prompt: "How formal does it need to be?",
    options: ["Relaxed", "Smart casual", "Formal", "Not sure"],
  },
  budget: {
    prompt: "What are you working with?",
    options: ["Under 100", "100 to 250", "250 plus", "Rather not say"],
  },
};

/* The inputs a styling model needs, and the honest state of each.
 *
 * Listed rather than described in prose because the state column is the point: a reader
 * should be able to see at a glance how much of this exists, and the answer is none of it.
 * Section 47 — the structure is real, the capability is not, and both are stated. */
const DIDO_INPUTS = [
  { name: "Style profile", body: "How you dress, and what you never wear", state: "Not built" },
  { name: "Occasion", body: "Where you are going and what it asks of you", state: "Asked, not modelled" },
  { name: "Dress code", body: "What the invitation actually requires", state: "Not built" },
  { name: "Fit and size", body: "Your measurements and how you like things to sit", state: "Not built" },
  { name: "Colour", body: "What you reach for and what you avoid", state: "Not built" },
  { name: "Budget", body: "What a piece and a whole look are worth to you", state: "Asked, not applied" },
  { name: "Weather", body: "The forecast where you will be wearing it", state: "Not built" },
  { name: "Catalogue", body: "What is actually available, in your size", state: "Read-only, five pieces" },
] as const;

const NEXT: Record<Exclude<Step, "done">, Step> = {
  occasion: "formality",
  formality: "budget",
  budget: "done",
};

/**
 * Style with Dido.
 *
 * THIS IS AN EXPERIENCE SHELL AND IT SAYS SO. Section 22 is explicit that a Dido phase
 * shell must be labelled as a shell until the AI phase, and section 47 forbids fake AI
 * responses.
 *
 * So the conversation is real — the state machine, the one-question-at-a-time flow, the
 * transitions, the live region, the reduced-motion behaviour all work and are all worth
 * having early. What Dido will not do is invent a recommendation. At the end of the flow it
 * says, in as many words, that it cannot style anyone yet and what it would need in order
 * to. Scripting a plausible outfit here would be the single most misleading thing this
 * platform could do, because it is the thing a reviewer would most want to believe.
 */
export default function DidoPage() {
  const [state, setState] = useState<DidoState>("welcome");
  const [step, setStep] = useState<Step>("occasion");
  const [turns, setTurns] = useState<Turn[]>([
    {
      id: 0,
      from: "dido",
      text: "I am Dido. Tell me where you are going and I will work out what you should wear.",
    },
  ]);

  const nextId = useRef(1);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    document.title = "Style with Dido — DEDUNET";
    /* Settle from welcome into listening, so the first thing a visitor sees is Dido
       arriving rather than Dido already waiting. */
    const t = window.setTimeout(() => setState("listening"), 900);
    return () => window.clearTimeout(t);
  }, []);

  /* Every timer is tracked and cleared on unmount. A pending setState after navigation is
     a React warning at best and a leak at worst, and this component sets several. */
  useEffect(() => {
    const pending = timers.current;
    return () => {
      for (const id of pending) window.clearTimeout(id);
    };
  }, []);

  function later(fn: () => void, ms: number) {
    const id = window.setTimeout(fn, ms);
    timers.current.push(id);
  }

  function say(from: Turn["from"], text: string) {
    setTurns((prev) => [...prev, { id: nextId.current++, from, text }]);
  }

  function answer(option: string) {
    if (step === "done") return;

    say("you", option);
    setState("thinking");

    const upcoming = NEXT[step];

    later(() => {
      if (upcoming === "done") {
        setState("error");
        say(
          "dido",
          "This is where I would build you a look — and I have to be straight with you: I cannot yet.",
        );
        later(() => {
          say(
            "dido",
            "I have your occasion, your formality and your budget, and nothing to do with them. There is no styling model behind me, no outfit engine and no way to score one piece against another. What you told me was recorded by this page and by nothing else.",
          );
          setStep("done");
        }, 1100);
      } else {
        setState("asking");
        say("dido", QUESTIONS[upcoming].prompt);
        setStep(upcoming);
      }
    }, 1200);
  }

  function restart() {
    setTurns([
      {
        id: nextId.current++,
        from: "dido",
        text: "Again. Where are you going?",
      },
    ]);
    setStep("occasion");
    setState("listening");
  }

  const question = step === "done" ? null : QUESTIONS[step];

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Dido Net</Eyebrow>
            <h1>Style with Dido</h1>
            <Lede>
              Tell Dido where you are going. It asks one thing at a time, the way a stylist
              would, rather than handing you a form.
            </Lede>
          </Stack>

          {/* The shell disclosure, at the top where it is read before the conversation
              rather than after it. */}
          <div className={styles.disclosure} data-testid="dido-disclosure" role="note">
            <strong>This is the conversation, not the intelligence.</strong> Dido can ask and
            listen. It cannot style anyone yet: there is no model behind it, and it will tell
            you so rather than inventing an outfit.
          </div>

          <div className={styles.stage}>
            <div className={styles.figureWrap}>
              <DidoFigure state={state} />
              <p className={styles.stateLabel}>{didoStateLabel(state)}</p>
            </div>

            <div className={styles.conversation} data-testid="dido-convo">
              {/* The log is a live region so each new turn is announced. Polite, so it
                  waits for the reader rather than cutting across them. */}
              <ol className={styles.log} data-testid="dido-log" aria-live="polite" aria-label="Conversation with Dido">
                {turns.map((turn) => (
                  <li
                    key={turn.id}
                    className={turn.from === "dido" ? styles.fromDido : styles.fromYou}
                  >
                    <span className={styles.who}>{turn.from === "dido" ? "Dido" : "You"}</span>
                    <p className={styles.message}>{turn.text}</p>
                  </li>
                ))}

                {state === "thinking" ? (
                  <li className={styles.fromDido}>
                    <span className={styles.who}>Dido</span>
                    <p className={styles.thinking} aria-label="Dido is thinking">
                      <span />
                      <span />
                      <span />
                    </p>
                  </li>
                ) : null}
              </ol>

              {question ? (
                <div className={styles.options} data-testid="dido-options">
                  <p className={styles.optionsPrompt}>{question.prompt}</p>
                  <div className={styles.optionRow} role="group" aria-label={question.prompt}>
                    {question.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={styles.option}
                        onClick={() => answer(option)}
                        disabled={state === "thinking"}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className={styles.options}>
                  <Stack gap="tight">
                    <Subtle>
                      When the styling model exists, this is where the look would appear —
                      complete, priced, and explained piece by piece.
                    </Subtle>
                    <div className={styles.optionRow}>
                      <button type="button" className={styles.option} onClick={restart}>
                        Start again
                      </button>
                      <ButtonLink to="/looks" variant="secondary">
                        See looks built by hand
                      </ButtonLink>
                    </div>
                  </Stack>
                </div>
              )}
            </div>
          </div>

          <section aria-labelledby="dido-what" className={styles.explainer}>
            <h2 id="dido-what">What Dido will need</h2>
            <p>
              Styling is not a language model guessing at an outfit. It is a set of inputs
              scored against each other, then assembled into a look that holds together and
              explained back to you.
            </p>

            <ul className={styles.inputs}>
              {DIDO_INPUTS.map((input) => (
                <li key={input.name} className={styles.input}>
                  <span className={styles.inputName}>{input.name}</span>
                  <span className={styles.inputBody}>{input.body}</span>
                  <span className={styles.inputState}>{input.state}</span>
                </li>
              ))}
            </ul>

            <p>
              The conversation above is the part that is built, because getting the questions
              right is worth doing before there is an engine to answer them.
            </p>

            <div className={styles.optionRow}>
              <ButtonLink to="/my-style" variant="secondary">
                See what DEDUNET knows about you
              </ButtonLink>
              <ButtonLink to="/discover" variant="quiet">
                Browse instead
              </ButtonLink>
            </div>
          </section>
        </Stack>
      </Section>
    </Container>
  );
}
