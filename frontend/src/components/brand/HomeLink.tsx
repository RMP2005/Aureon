'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';

/**
 * HomeLink — navigation to the landing journey with a guaranteed clean
 * scroll state. Resets every possible scroller (window, html, body — the
 * landing scrolls on BODY because html/body are height-capped) so no stale
 * position survives, including same-route clicks while already on "/".
 */
export function resetAllScrollers() {
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
  if ('scrollTop' in document.documentElement) document.documentElement.scrollTop = 0;
  if ('scrollTop' in document.body) document.body.scrollTop = 0;
}

export default function HomeLink({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href="/" onClick={resetAllScrollers} className={className}>
      {children}
    </Link>
  );
}
