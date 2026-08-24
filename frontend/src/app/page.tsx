'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import LandingCanvas from '@/components/landing/LandingCanvas';
import ActOverlays from '@/components/landing/ActOverlays';
import AureonMark from '@/components/brand/AureonMark';
import LandingHud from '@/components/landing/LandingHud';
import LandingLegend from '@/components/landing/LandingLegend';
import LandingCTAs from '@/components/landing/LandingCTAs';
import { setLandingProgress } from '@/lib/landing/progress';
import { useCinematicAudio } from '@/hooks/useCinematicAudio';

/**
 * Cinematic landing journey (Phase 10C).
 *
 * One pinned canvas, five acts, zero dashboard chrome. The command center's
 * zero-scroll discipline lives at /twin — these two experiences never mix.
 */

export default function Home() {
  // Decide after mount — server and client must agree at hydration.
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  return reducedMotion ? <StaticLanding /> : <JourneyLanding />;
}

/** Full cinematic experience: sticky canvas + scrubbed acts + audio. */
function JourneyLanding() {
  const journeyRef = useRef<HTMLDivElement>(null);
  const audio = useCinematicAudio();

  // Clean entry (logo-nav fix): kill browser scroll restoration and force
  // the journey to progress zero BEFORE first paint — no partial scenes,
  // no jump, no flash. Runs on every mount, including client navigations.
  useLayoutEffect(() => {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
    setLandingProgress(0);
  }, []);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    // Start from a known-clean state regardless of what ran before mount.
    setLandingProgress(0);

    const ctx = gsap.context(() => {
      // Master scrub — one trigger drives scene progress…
      ScrollTrigger.create({
        trigger: journeyRef.current,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => {
          setLandingProgress(self.progress);
          audio.setIntensity(
            // Siren swells through the pulse act, recedes after.
            Math.max(0, 1 - Math.abs(self.progress - 0.56) / 0.24),
          );
          hideScrollHint(self.progress);
        },
      });

      // …and per-act copy choreography.
      gsap.utils.toArray<HTMLElement>('[data-act]').forEach((section) => {
        const copies = section.querySelectorAll('[data-act-copy]');
        gsap.fromTo(
          copies,
          { autoAlpha: 0, y: 34 },
          {
            autoAlpha: 1,
            y: 0,
            stagger: 0.12,
            duration: 0.85,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: section,
              start: 'top 62%',
              end: 'center 42%',
              toggleActions: 'play reverse play reverse',
            },
          },
        );
      });
    }, journeyRef);

    // Late-restoration guard: browsers can restore scroll asynchronously
    // AFTER mount. Re-assert the clean state, then measure.
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
      setLandingProgress(0);
      ScrollTrigger.refresh();
    });

    return () => ctx.revert();
    // Audio setters are stable refs — safe to omit from deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    return () => {
      document.documentElement.style.scrollBehavior = '';
    };
  }, []);

  return (
    <main ref={journeyRef} className="relative bg-void">
      {/* Pinned stage */}
      <div className="sticky top-0 h-screen w-full overflow-hidden">
        <div className="absolute inset-0">
          <LandingCanvas />
        </div>

        {/* Wordmark */}
        <div className="pointer-events-none absolute left-6 top-6 z-20 flex select-none items-center gap-3">
          <AureonMark size={22} />
          <p className="font-display text-lg font-semibold tracking-tight">
            Aureon
            <span className="mx-3 text-teal-core">/</span>
            <span className="hud-label align-middle text-[var(--color-text-muted)]">
              Urban Intelligence OS
            </span>
          </p>
        </div>

        {/* Scientific instrument overlay (Phase 11-refinement) */}
        <LandingHud />

        {/* Map key — surfaces with the final reveal (Phase 11H) */}
        <LandingLegend />

        {/* Opening splash — dissolves into Act I */}
        <Splash />

        {/* Scroll invitation */}
        <div
          id="scroll-hint"
          className="pointer-events-none absolute bottom-7 inset-x-0 z-20 flex flex-col items-center gap-2 transition-opacity"
        >
          <span className="hud-label text-[var(--color-text-muted)]">Scroll</span>
          {/* Solid hairline pulse — no decorative gradients (Phase 11H) */}
          <div className="h-8 w-px bg-teal-core/50 animate-pulse" />
        </div>

        {/* Sound opt-in (autoplay-policy compliant) */}
        <button
          onClick={audio.enabled ? audio.disable : audio.enable}
          className="absolute bottom-6 right-6 z-30 hud-stamp rounded-full border border-hairline-strong px-4 py-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-white/20 transition-colors"
        >
          {audio.enabled ? '◉ SOUND ON' : '◎ SOUND OFF'}
        </button>
      </div>

      {/* Scroll narrative above the stage */}
      <div className="relative z-10 -mt-[100vh] pointer-events-none">
        <ActOverlays />
      </div>
    </main>
  );
}

function Splash() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const el = ref.current;
    if (!el) return;
    const st = ScrollTrigger.create({
      start: 40,
      end: 'max',
      onUpdate: (self) => {
        el.style.opacity = String(Math.max(0, 1 - self.scroll() / 260));
      },
    });
    return () => st.kill();
  }, []);
  return (
    <div
      ref={ref}
      className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"
    >
      <h1 className="font-display text-[clamp(2.6rem,8.5vw,6.5rem)] font-bold tracking-tight text-center leading-none break-words max-w-full px-4">
        Aureon<span className="text-teal-core">.</span>
      </h1>
    </div>
  );
}

function hideScrollHint(progress: number) {
  const hint = document.getElementById('scroll-hint');
  if (hint) hint.style.opacity = progress > 0.04 ? '0' : '1';
}

/** Reduced-motion fallback: final-frame city, no scrubbing, plain flow. */
function StaticLanding() {
  useLayoutEffect(() => {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
    setLandingProgress(1);
  }, []);
  return (
    <main className="relative bg-void">
      <div className="sticky top-0 h-screen w-full overflow-hidden">
        <div className="absolute inset-0 opacity-70">
          <LandingCanvas />
        </div>
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-center px-6">
          <p className="font-display text-[clamp(2.2rem,6.5vw,4.5rem)] font-bold tracking-tight break-words">
            Aureon<span className="text-teal-core">.</span>
          </p>
          <p className="mt-4 max-w-xl text-[var(--color-text-secondary)]">
            The urban intelligence operating system. A living digital twin of
            Bengaluru with explainable emergency-dispatch intelligence.
          </p>
          <div className="pointer-events-auto mt-8 flex justify-center">
            <LandingCTAs compact />
          </div>
        </div>
      </div>
    </main>
  );
}
