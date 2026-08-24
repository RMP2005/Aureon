'use client';

import { useEffect, useState } from 'react';

/**
 * SSR-safe media query hook for responsive composition switches.
 *
 * Returns false on first render (server + hydration) so the desktop
 * layout — the frozen, approved experience — is always the default;
 * compact arrangements attach only after mount on matching viewports.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

/** True below Tailwind's `lg` breakpoint (1024px) — tablet + mobile. */
export function useIsCompactViewport(): boolean {
  return !useMediaQuery('(min-width: 1024px)');
}
