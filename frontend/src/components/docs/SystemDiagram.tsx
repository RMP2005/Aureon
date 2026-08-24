import type { ReactNode } from 'react';

/**
 * SystemDiagram — node-based flow (Phase 11F).
 *
 * Vertical chain of labeled nodes joined by rails. `activeIndex` marks the
 * stage under discussion; `onNodeClick` makes it an interactive map.
 */
export default function SystemDiagram({
  nodes,
  activeIndex = -1,
  onNodeClick,
}: {
  nodes: { label: string; sub?: string; icon?: ReactNode }[];
  activeIndex?: number;
  onNodeClick?: (index: number) => void;
}) {
  return (
    <ol className="flex flex-col items-stretch">
      {nodes.map((n, i) => {
        const active = i === activeIndex;
        const interactive = Boolean(onNodeClick);
        return (
          <li key={n.label} className="flex flex-col items-stretch">
            {i > 0 && (
              <span aria-hidden className="mx-auto block h-4 w-px bg-hairline-strong" />
            )}
            <button
              type="button"
              disabled={!interactive}
              onClick={() => onNodeClick?.(i)}
              className={`group flex items-center gap-3 border px-4 py-2.5 text-left transition-colors ${
                active
                  ? 'border-teal-core/50 bg-panel-3'
                  : 'border-hairline bg-panel-1 hover:border-hairline-strong'
              } ${interactive ? 'cursor-pointer' : 'cursor-default'}`}
            >
              <span
                className={`tnum hud-stamp !text-[9px] w-6 shrink-0 ${
                  active ? 'text-teal-core' : 'text-[var(--color-text-muted)]'
                }`}
              >
                {String(i + 1).padStart(2, '0')}
              </span>
              {n.icon && <span className="shrink-0">{n.icon}</span>}
              <span className="min-w-0">
                <span
                  className={`block font-display text-sm font-medium tracking-tight ${
                    active ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'
                  }`}
                >
                  {n.label}
                </span>
                {n.sub && (
                  <span className="block text-[11px] leading-snug text-[var(--color-text-muted)]">
                    {n.sub}
                  </span>
                )}
              </span>
              {active && (
                <span aria-hidden className="ml-auto h-1.5 w-1.5 shrink-0 rotate-45 bg-teal-core" />
              )}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
