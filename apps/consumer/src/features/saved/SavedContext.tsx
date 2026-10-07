import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, type SaveKind, type SavedState } from "../../api/types";
import { applyToggle, nextStatus, type SaveStatus } from "./savedState";
import { fetchSavedState, saveItem, unsaveItem } from "../../api/endpoints";
import { onSessionChange, session } from "../../api/client";

/* ONE source of truth for "is this saved", shared by every surface.
 *
 * WHY A CONTEXT AND NOT A PER-CARD REQUEST.
 *
 * The obvious implementation gives each save control its own `GET /saved/status?product=x`.
 * Home renders more than twenty cards, so that is twenty-odd requests for heart icons
 * against an API that limits 300 per minute per client — a rate-limit budget spent on
 * decoration, and a measurable one: this platform already recorded 22 API requests for a
 * single Home load before any of this existed.
 *
 * So the saved set is fetched ONCE when a session appears, held here, and PATCHED LOCALLY
 * on every mutation. Cross-surface consistency falls out of that: saving on the product
 * page updates the same set the Shop card reads, with no refetch and no full-page reload.
 *
 * ROLLBACK IS THE POINT OF THE OPTIMISTIC UPDATE, not an afterthought. The set is changed
 * before the request so the icon responds immediately, and the previous value is restored if
 * the request fails. An optimistic update without a rollback is just a lie with good latency
 * — the control would show "saved" for something the server refused.
 *
 * SIGNED OUT, NOTHING IS STORED. There is no local saved list for anonymous visitors. A
 * saved item that lives only in `localStorage` and is later described as "saved" is exactly
 * the fake persistence this phase forbids: it survives a refresh, looks identical to the
 * real thing, and vanishes on the next device. Signed-out save asks the visitor to sign in.
 */

export type { SaveStatus };

interface SavedContextValue {
  /** Null until the first fetch resolves, or while signed out. */
  state: SavedState | null;
  signedIn: boolean;
  ready: boolean;
  isSaved: (kind: SaveKind, slug: string) => boolean;
  statusOf: (kind: SaveKind, slug: string) => SaveStatus;
  errorOf: (kind: SaveKind, slug: string) => unknown;
  counts: { products: number; brands: number; looks: number };
  /**
   * Bumped once a mutation has SETTLED against the server.
   *
   * Lists depend on this rather than on the saved set, and the difference is a real race.
   * The set changes optimistically, BEFORE the DELETE has committed -- so a list refetched
   * on that change can be served the row the server is still deleting, and nothing would
   * trigger a second fetch. WebKit exposed it consistently while Chromium hid it.
   */
  version: number;
  /** Returns true when the state changed, false when it was refused or failed. */
  toggle: (kind: SaveKind, slug: string) => Promise<boolean>;
  /** Re-read from the server. Used by the Saved page after a removal. */
  refresh: () => void;
}

const EMPTY: SavedState = { products: [], brands: [], looks: [] };

const SavedContext = createContext<SavedContextValue>({
  state: null,
  signedIn: false,
  ready: false,
  isSaved: () => false,
  statusOf: () => "idle",
  errorOf: () => null,
  counts: { products: 0, brands: 0, looks: 0 },
  version: 0,
  toggle: async () => false,
  refresh: () => {},
});

function key(kind: SaveKind, slug: string): string {
  return `${kind}:${slug}`;
}

export function SavedProvider({ children }: { children: ReactNode }) {
  const [signedIn, setSignedIn] = useState(() => session.signedIn);
  const [state, setState] = useState<SavedState | null>(null);
  const [ready, setReady] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, SaveStatus>>({});
  const [errors, setErrors] = useState<Record<string, unknown>>({});
  const [nonce, setNonce] = useState(0);
  const [version, setVersion] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  /* Follow the session. Signing out must clear the set immediately rather than leave
     another customer's saved items on screen until something refetches. */
  useEffect(() => onSessionChange(() => setSignedIn(session.signedIn)), []);

  useEffect(() => {
    if (!signedIn) {
      setState(null);
      setReady(true);
      return;
    }
    const controller = new AbortController();
    setReady(false);
    fetchSavedState(controller.signal)
      .then((next) => {
        if (!mounted.current || controller.signal.aborted) return;
        setState(next);
        setReady(true);
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        /* A 401 here means the stored token is stale. The api client already clears it,
           which fires onSessionChange and brings us back through the signed-out path, so
           there is nothing to do but stop pretending we have a saved set. */
        if (!mounted.current) return;
        setState(null);
        setReady(true);
        if (!(error instanceof ApiError && error.status === 401)) {
          // Anything else is a genuine failure; surfaces render controls as unsaved.
          setState(null);
        }
      });
    return () => controller.abort();
  }, [signedIn, nonce]);

  const isSaved = useCallback(
    (kind: SaveKind, slug: string) => Boolean(state?.[kind]?.includes(slug)),
    [state],
  );

  const statusOf = useCallback(
    (kind: SaveKind, slug: string) => statuses[key(kind, slug)] ?? "idle",
    [statuses],
  );

  const errorOf = useCallback(
    (kind: SaveKind, slug: string) => errors[key(kind, slug)] ?? null,
    [errors],
  );

  const counts = useMemo(
    () => ({
      products: state?.products.length ?? 0,
      brands: state?.brands.length ?? 0,
      looks: state?.looks.length ?? 0,
    }),
    [state],
  );

  const toggle = useCallback(
    async (kind: SaveKind, slug: string): Promise<boolean> => {
      if (!session.signedIn) return false;

      const current = state ?? EMPTY;
      const wasSaved = current[kind].includes(slug);
      const k = key(kind, slug);

      // Optimistic. `current` is kept for the rollback below; applyToggle does not mutate it.
      setState(applyToggle(current, kind, slug));
      setStatuses((s) => ({ ...s, [k]: nextStatus(wasSaved) }));
      setErrors((e) => ({ ...e, [k]: null }));

      try {
        if (wasSaved) await unsaveItem(kind, slug);
        else await saveItem(kind, slug);
        if (mounted.current) {
          setStatuses((s) => ({ ...s, [k]: "idle" }));
          // Only now is the server's state settled. Lists may refetch.
          setVersion((v) => v + 1);
        }
        return true;
      } catch (error) {
        /* ROLLBACK. Without this the control keeps showing the optimistic value for a
           request the server refused, which is worse than never having updated it. */
        if (mounted.current) {
          setState(current);
          setStatuses((s) => ({ ...s, [k]: "error" }));
          setErrors((e) => ({ ...e, [k]: error }));
          // The rollback is also a settled state a list should reflect.
          setVersion((v) => v + 1);
        }
        return false;
      }
    },
    [state],
  );

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  const value = useMemo(
    () => ({
      state, signedIn, ready, isSaved, statusOf, errorOf, counts, version, toggle, refresh,
    }),
    [state, signedIn, ready, isSaved, statusOf, errorOf, counts, version, toggle, refresh],
  );

  return <SavedContext.Provider value={value}>{children}</SavedContext.Provider>;
}

export function useSaved(): SavedContextValue {
  return useContext(SavedContext);
}
