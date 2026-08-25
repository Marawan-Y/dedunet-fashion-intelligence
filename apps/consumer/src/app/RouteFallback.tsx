import { Container, Section } from "../components/primitives";
import { SkeletonGrid } from "../components/States";

/**
 * Shown while a lazily-loaded route chunk is being fetched.
 *
 * Deliberately a skeleton rather than a spinner or an empty div: it reserves roughly the
 * space the route is about to occupy, so the arrival does not shift the layout. It also
 * carries a live label, because a chunk fetched over a slow connection is otherwise a
 * silence a screen reader cannot interpret.
 */
export function RouteFallback() {
  return (
    <Container>
      <Section>
        <SkeletonGrid count={6} label="Loading page" />
      </Section>
    </Container>
  );
}
