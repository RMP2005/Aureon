import Link from 'next/link';

/**
 * LandingCTAs (Phase 11H polish) — three distinct actions with generous
 * spacing. No boxed container: a primary teal action flanked by two quiet
 * companions. Reads as a product landing, not a dashboard control group.
 */
export default function LandingCTAs({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={`pointer-events-auto flex flex-col items-stretch justify-center gap-4 sm:flex-row sm:items-center ${
        compact ? 'sm:gap-3' : 'sm:gap-6'
      }`}
    >
      <Link
        href="/command?intro=1"
        className={`group flex items-center justify-center gap-2.5 rounded-lg bg-teal-core font-semibold tracking-wide text-black transition-all hover:brightness-110 hover:shadow-[0_0_32px_rgba(22,242,212,0.3)] ${
          compact ? 'px-8 py-3 text-[14px]' : 'px-10 py-[1.05rem] text-[15px]'
        }`}
      >
        ENTER COMMAND CENTER
        <span aria-hidden className="transition-transform group-hover:translate-x-1">→</span>
      </Link>

      <Link
        href="/simulation"
        className={`flex items-center justify-center rounded-lg border border-hairline-strong font-medium tracking-wide text-[var(--color-text-primary)] transition-colors hover:border-white/25 hover:bg-white/5 ${
          compact ? 'px-7 py-3 text-[13px]' : 'px-9 py-[0.95rem] text-[14px]'
        }`}
      >
        RUN SIMULATION
      </Link>

      <Link
        href="/docs"
        className={`flex items-center justify-center rounded-lg px-5 font-medium tracking-wide text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] sm:px-2 ${
          compact ? 'py-3 text-[13px]' : 'py-[0.95rem] text-[14px]'
        }`}
      >
        SYSTEM GUIDE
      </Link>
    </div>
  );
}
