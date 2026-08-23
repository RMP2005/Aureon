'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { NAV_ITEMS } from '@/lib/constants';
import { getHealth } from '@/lib/api';

type ConnectionState = 'connecting' | 'online' | 'offline';

const CONNECTION_STYLES: Record<ConnectionState, { dot: string; text: string; label: string }> = {
  connecting: {
    dot: 'bg-amber-warn animate-pulse',
    text: 'text-amber-warn',
    label: 'Connecting',
  },
  online: {
    dot: 'bg-teal-core',
    text: 'text-teal-core',
    label: 'System Online',
  },
  offline: {
    dot: 'bg-crit-red',
    text: 'text-crit-red',
    label: 'Backend Offline',
  },
};

export default function Navbar() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 15_000,
    retry: 1,
  });

  const state: ConnectionState = healthQuery.isPending
    ? 'connecting'
    : healthQuery.isError
      ? 'offline'
      : 'online';
  const style = CONNECTION_STYLES[state];

  // Defensive envelope read: the health payload may be null, the inner
  // data object absent, or version missing on older backends. The label
  // degrades to plain connection state instead of crashing.
  const version = (() => {
    if (state !== 'online') return null;
    const d = healthQuery.data as { data?: { version?: unknown } } | undefined;
    const v = d?.data?.version;
    return typeof v === 'string' && v.length > 0 ? v : null;
  })();

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <nav className="glass-panel mx-4 mt-4 rounded-lg px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-md bg-teal-core/10 border border-teal-core/30 flex items-center justify-center">
            <span className="font-display font-bold text-sm text-teal-core">A</span>
          </div>
          <span className="font-display text-lg font-semibold tracking-tight">Aureon</span>
        </Link>

        <div className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="px-4 py-2 rounded-md text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-all duration-200"
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full border"
          data-testid="connection-state"
        >
          <div className={`h-2 w-2 rounded-full ${style.dot}`} />
          <span className={`hud-label !tracking-[0.04em] ${style.text}`}>
            {version ? `v${version}` : style.label}
          </span>
        </div>
      </nav>
    </motion.header>
  );
}
