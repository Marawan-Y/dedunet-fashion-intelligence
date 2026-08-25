import { useCallback, useEffect, useRef, useState } from "react";

/* Async state, with every state section 23 requires and no blank page anywhere.
 *
 * "idle" is not modelled: a request either has not been made or is in flight, and a
 * component that renders nothing while deciding which is exactly the blank page this
 * exists to prevent. It starts in "loading". */
export type AsyncStatus = "loading" | "success" | "error";

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: unknown;
  /** Re-run the request. Every error surface must offer this. */
  retry: () => void;
}

/**
 * Run an async function and track its outcome.
 *
 * `deps` behaves like an effect dependency list. The request is aborted when the
 * dependencies change or the component unmounts, so a slow response for a product the
 * customer has already navigated away from cannot overwrite the one they are looking at.
 */
export function useAsync<T>(
  run: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): AsyncState<T> {
  const [state, setState] = useState<{ status: AsyncStatus; data: T | null; error: unknown }>({
    status: "loading",
    data: null,
    error: null,
  });
  const [attempt, setAttempt] = useState(0);

  /* Held in a ref so changing the callback identity between renders does not re-fire the
     request. The dependency list is the contract for when to re-run, not the closure. */
  const runRef = useRef(run);
  runRef.current = run;

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    setState((prev) => ({ status: "loading", data: prev.data, error: null }));

    runRef
      .current(controller.signal)
      .then((data) => {
        if (live) setState({ status: "success", data, error: null });
      })
      .catch((error: unknown) => {
        /* An abort is this component doing its job, not a failure to report. */
        if (controller.signal.aborted) return;
        if (live) setState({ status: "error", data: null, error });
      });

    return () => {
      live = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { ...state, retry };
}
