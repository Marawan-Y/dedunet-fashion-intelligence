import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/Button";
import { CheckboxField, Form, PasswordField, TextField } from "../../components/Field";
import {
  Container,
  Eyebrow,
  Lede,
  Section,
  Stack,
  Subtle,
} from "../../components/primitives";
import { ErrorState } from "../../components/States";
import { register, signIn, signOut } from "../../api/endpoints";
import { onSessionChange, session } from "../../api/client";
import styles from "./AccountPage.module.css";

/**
 * Account.
 *
 * THIS IS THE PAGE THAT FAILED HUMAN ACCEPTANCE. At 9b63791 it rendered bare labels and
 * inputs with no CSS behind them — index.html had stopped loading the stylesheet that
 * styled `.form` and `.two`, and nothing noticed. "Fields and labels ran together" is
 * exactly what an unstyled form looks like.
 *
 * The fix is not margins. Every control here comes from the design system's Field
 * components, which bind label, hint and error through generated ids and cannot be rendered
 * without their styling, because the styling is a CSS Module the component imports rather
 * than a global class it hopes someone loaded.
 */
export default function AccountPage() {
  const [signedIn, setSignedIn] = useState(session.signedIn);

  useEffect(() => {
    document.title = "Account — DEDUNET";
    return onSessionChange(() => setSignedIn(session.signedIn));
  }, []);

  return signedIn ? <SignedIn onSignOut={() => setSignedIn(false)} /> : <SignedOut />;
}

/* ------------------------------------------------------------------- signed out */

function SignedOut() {
  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Your account</Eyebrow>
            <h1>Sign in to DEDUNET</h1>
            <Lede>
              An account keeps your looks, your saved pieces and your style profile together
              across every device you use.
            </Lede>
          </Stack>

          <div className={styles.columns}>
            <section className={styles.panel} aria-labelledby="signin-heading">
              <h2 id="signin-heading" className={styles.panelTitle}>
                Sign in
              </h2>
              <SignInForm />
            </section>

            <section className={styles.panel} aria-labelledby="register-heading">
              <h2 id="register-heading" className={styles.panelTitle}>
                Create an account
              </h2>
              <RegisterForm />
            </section>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}

function SignInForm() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);

    /* Validated here rather than left to the browser, so the message is ours, is bound to
       the field through aria-describedby, and reads the same in every browser. */
    const next: typeof errors = {};
    if (!email.trim()) next.email = "Enter the email address you signed up with.";
    else if (!email.includes("@")) next.email = "That does not look like an email address.";
    if (!password) next.password = "Enter your password.";

    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    try {
      const result = await signIn(email.trim(), password);
      session.adopt(result.access_token, result.role);
      navigate("/account", { replace: true });
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Form onSubmit={submit} aria-busy={busy}>
      <TextField
        label="Email"
        type="email"
        name="email"
        autoComplete="email"
        value={email}
        error={errors.email}
        onChange={(e) => setEmail(e.currentTarget.value)}
      />

      <PasswordField
        label="Password"
        name="password"
        autoComplete="current-password"
        value={password}
        error={errors.password}
        onChange={(e) => setPassword(e.currentTarget.value)}
      />

      {failure ? <ErrorState error={failure} testId="signin-error" /> : null}

      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
        <Link to="/account" className={styles.forgot}>
          Forgot your password?
        </Link>
      </div>

      <Subtle>
        Password reset is not built. There is no email delivery configured, so a reset link
        could not be sent.
      </Subtle>
    </Form>
  );
}

function RegisterForm() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<{ fullName?: string; email?: string; password?: string }>({});
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);

    const next: typeof errors = {};
    if (!fullName.trim()) next.fullName = "Enter your name.";
    if (!email.trim()) next.email = "Enter an email address.";
    else if (!email.includes("@")) next.email = "That does not look like an email address.";
    if (password.length < 8) next.password = "Use at least 8 characters.";

    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    try {
      const result = await register({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        marketing_consent: consent,
      });
      session.adopt(result.access_token, result.role);
      navigate("/account", { replace: true });
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Form onSubmit={submit} aria-busy={busy}>
      <TextField
        label="Full name"
        name="full_name"
        autoComplete="name"
        value={fullName}
        error={errors.fullName}
        onChange={(e) => setFullName(e.currentTarget.value)}
      />

      <TextField
        label="Email"
        type="email"
        name="email"
        autoComplete="email"
        value={email}
        error={errors.email}
        onChange={(e) => setEmail(e.currentTarget.value)}
      />

      <PasswordField
        label="Password"
        name="password"
        autoComplete="new-password"
        hint="At least 8 characters."
        value={password}
        error={errors.password}
        onChange={(e) => setPassword(e.currentTarget.value)}
      />

      <CheckboxField
        label="Send me occasional updates about DEDUNET"
        name="marketing_consent"
        checked={consent}
        onChange={(e) => setConsent(e.currentTarget.checked)}
      />

      {failure ? <ErrorState error={failure} testId="register-error" /> : null}

      <div className={styles.formActions}>
        <Button type="submit" variant="secondary" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </Button>
      </div>

      <Subtle>
        Consent is stored with your account and is not acted on: no email is sent from this
        build, because no delivery provider is configured.
      </Subtle>
    </Form>
  );
}

/* -------------------------------------------------------------------- signed in */

const SECTIONS = [
  { to: "/orders", title: "Orders", body: "Everything you have ordered, and where it is." },
  { to: "/saved", title: "Saved", body: "Looks, pieces and brands you kept." },
  { to: "/my-style", title: "My Style", body: "What DEDUNET knows about how you dress." },
];

function SignedIn({ onSignOut }: { onSignOut: () => void }) {
  const navigate = useNavigate();

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>Your account</Eyebrow>
            <h1>Account</h1>
            <Lede>You are signed in to DEDUNET.</Lede>
          </Stack>

          <div className={styles.sections} data-testid="account-sections">
            {SECTIONS.map((item) => (
              <Link key={item.to} to={item.to} className={styles.sectionCard}>
                <span className={styles.sectionTitle}>{item.title}</span>
                <span className={styles.sectionBody}>{item.body}</span>
              </Link>
            ))}
          </div>

          <section aria-labelledby="preferences-heading" className={styles.panel}>
            <h2 id="preferences-heading" className={styles.panelTitle}>
              Preferences and privacy
            </h2>
            <Subtle>
              Notification preferences, privacy controls and data export are not built on this
              surface yet. The account itself is real — it is a session against the commerce
              API — but these controls have nothing behind them and are not shown as if they
              did.
            </Subtle>
          </section>

          <div>
            <Button
              variant="secondary"
              onClick={() => {
                signOut();
                onSignOut();
                navigate("/", { replace: true });
              }}
            >
              Sign out
            </Button>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
