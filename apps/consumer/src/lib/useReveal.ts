import { useEffect, useRef, useState } from "react";

/**
 * Reveal an element the first time it enters the viewport.
 *
 * IntersectionObserver rather than a scroll listener: the callback fires off the main
 * thread's scroll path, so a page with a dozen revealing sections does not spend every
 * frame recalculating positions. On a phone that difference is the whole performance
 * budget for section 28.
 *
 * It unobserves after firing. A reveal that re-triggers on the way back up is a page that
 * will not sit still, and nobody scrolls up to watch an animation again.
 *
 * REDUCED MOTION IS HONOURED BY STARTING REVEALED. The durations are already zeroed
 * centrally in tokens.css, but zero-duration is still a state change; beginning in the
 * final state means there is nothing to change at all.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: {
  /** Fraction of the element that must be visible. Small, so tall sections fire early. */
  threshold?: number;
  /** Fires early, so content is already settled by the time it is read. */
  rootMargin?: string;
}) {
  const ref = useRef<T | null>(null);

  const [revealed, setRevealed] = useState(() => {
    if (typeof window === "undefined") return true;
    if (!("IntersectionObserver" in window)) return true;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (revealed) return;
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          setRevealed(true);
          observer.unobserve(entry.target);
        }
      },
      {
        threshold: options?.threshold ?? 0.08,
        rootMargin: options?.rootMargin ?? "0px 0px -8% 0px",
      },
    );

    observer.observe(node);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealed]);

  return { ref, revealed } as const;
}
