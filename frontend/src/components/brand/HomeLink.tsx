'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';

/**
 * HomeLink — navigation to the landing journey with a guaranteed clean
 * scroll state. Client component so the pre-nav reset can run anywhere,
 * including server-rendered pages like the System Guide.
 */
export default function HomeLink({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link
      href="/"
      onClick={() =>
        window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior })
      }
      className={className}
    >
      {children}
    </Link>
  );
}
