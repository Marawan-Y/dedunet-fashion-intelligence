import { useRouteError } from "react-router-dom";
import { ButtonLink } from "../components/Button";
import { Container, Section, Stack, Lede, Eyebrow } from "../components/primitives";
import { ErrorState } from "../components/States";

/**
 * The 404.
 *
 * A heading, an explanation and a way out. At 9b63791 this route rendered 92 characters
 * with no h1 at all, which is a dead end wearing an error message — the recovery link is
 * the part that matters.
 */
export function NotFound() {
  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <Stack gap="tight">
            <Eyebrow>404</Eyebrow>
            <h1>This page does not exist</h1>
          </Stack>

          <Lede>
            The address you followed does not lead anywhere on DEDUNET. It may have been
            mistyped, or it may have pointed at something that was never published.
          </Lede>

          <div style={{ display: "flex", gap: "var(--ds-space-3)", flexWrap: "wrap" }}>
            <ButtonLink to="/" variant="primary">
              Back to DEDUNET
            </ButtonLink>
            <ButtonLink to="/discover" variant="secondary">
              Discover looks
            </ButtonLink>
            <ButtonLink to="/dido" variant="quiet">
              Style with Dido
            </ButtonLink>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}

/**
 * The last line of defence.
 *
 * React unmounts the whole tree when a render throws, leaving a white screen with the
 * failure only in the console. This turns that into a page that still has the shell, still
 * says what happened, and still offers a way forward.
 */
export function RouteError() {
  const error = useRouteError();

  return (
    <Container>
      <Section>
        <Stack gap="loose">
          <h1>Something failed on this page</h1>
          <ErrorState
            error={error}
            onRetry={() => window.location.reload()}
            testId="route-error"
          />
          <div>
            <ButtonLink to="/" variant="secondary">
              Back to DEDUNET
            </ButtonLink>
          </div>
        </Stack>
      </Section>
    </Container>
  );
}
