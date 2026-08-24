'use client';

import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { getLiveBuffer } from '@/lib/twin/live-buffer';

/**
 * MapLegend — minimal operator-HUD key for the twin.
 *
 * Honesty contract: a row exists ONLY while its layer is actually rendered.
 *   Road network / Hospital / Route flow — static layers, always mounted.
 *   Ambulance / Incident — live layers; rows surface with the entities.
 *
 * Deliberately quiet: hairline edge, translucent void fill, tiny stamps.
 * Purely presentational; never intercepts pointer events.
 */

const POLL_MS = 500;

interface LayerPresence {
  ambulances: boolean;
  incidents: boolean;
}

function readPresence(): LayerPresence {
  try {
    const buf = getLiveBuffer();
    return {
      ambulances: buf.ambulances.size > 0,
      incidents: buf.incidents.length > 0,
    };
  } catch {
    return { ambulances: false, incidents: false };
  }
}

export default function MapLegend({ className = '' }: { className?: string }) {
  const [presence, setPresence] = useState<LayerPresence>({
    ambulances: false,
    incidents: false,
  });

  useEffect(() => {
    setPresence(readPresence());
    const id = setInterval(() => setPresence(readPresence()), POLL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      aria-label="Map legend"
      className={`pointer-events-none select-none border border-hairline bg-void/50 px-2.5 py-2 backdrop-blur-sm ${className}`}
    >
      <p className="hud-stamp !text-[8px] mb-1.5 text-[var(--color-text-muted)]">
        MAP KEY
      </p>
      <ul className="space-y-1">
        <LegendRow label="Road network">
          <span aria-hidden className="h-px w-5 bg-[#aab8cf]/80" />
        </LegendRow>
        <LegendRow label="Hospital">
          <span
            aria-hidden
            className="h-2 w-2 rounded-full bg-[color:var(--color-infra-blue)] shadow-[0_0_6px_rgba(77,163,255,0.9)]"
          />
        </LegendRow>
        {presence.ambulances && (
          <LegendRow label="Ambulance">
            <span aria-hidden className="h-1.5 w-3.5 rounded-full bg-teal-core" />
          </LegendRow>
        )}
        {presence.incidents && (
          <LegendRow label="Incident">
            <span aria-hidden className="flex h-2.5 w-2.5 items-center justify-center rounded-full border-[1.5px] border-crit-red" />
          </LegendRow>
        )}
        <LegendRow label="Route flow">
          <span aria-hidden className="flex gap-[3px]">
            {[0, 1, 2].map((d) => (
              <span key={d} className="h-1 w-1 rounded-full bg-teal-core/70" />
            ))}
          </span>
        </LegendRow>
      </ul>
    </div>
  );
}

function LegendRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <li className="flex items-center gap-2.5">
      {children}
      <span className="hud-stamp !text-[8px] text-[var(--color-text-secondary)]">
        {label}
      </span>
    </li>
  );
}
