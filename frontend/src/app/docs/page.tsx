import type { Metadata } from 'next';
import Link from 'next/link';
import AureonMark from '@/components/brand/AureonMark';
import HomeLink from '@/components/brand/HomeLink';
import SystemTour from '@/components/docs/SystemTour';
import InteractiveSystemMap from '@/components/docs/InteractiveSystemMap';
import ConceptBlock from '@/components/docs/ConceptBlock';
import ExampleDecision from '@/components/docs/ExampleDecision';
import Glossary from '@/components/docs/Glossary';
import ArchitectureSection from '@/components/docs/ArchitectureSection';

export const metadata: Metadata = {
  title: 'Aureon — System Guide',
  description:
    'Understanding the digital twin, decisions, and intelligence layer of the Aureon urban intelligence platform.',
};

function SectionStamp({ n, title }: { n: string; title: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <span className="tnum hud-stamp !text-[10px] text-teal-core">{n}</span>
      <h2 className="font-display text-xl font-semibold tracking-tight md:text-2xl">
        {title}
      </h2>
      <span aria-hidden className="h-px flex-1 bg-hairline" />
    </div>
  );
}

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-void text-[var(--color-text-primary)]">
      {/* Top bar */}
      <header className="border-b border-hairline">
        <div className="flex h-16 items-center justify-between px-6 lg:px-10">
          <HomeLink className="flex items-center gap-3 select-none">
            <AureonMark size={22} />
            <span className="font-display text-lg font-semibold tracking-tight">
              Aureon
            </span>
            <span aria-hidden className="mx-1 text-teal-core">/</span>
            <span className="hud-label align-middle text-[var(--color-text-muted)]">
              System Guide
            </span>
          </HomeLink>
          <nav className="flex items-center gap-3">
            <Link
              href="/command"
              className="rounded-md border border-hairline-strong px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] transition-colors hover:border-white/20 hover:text-[var(--color-text-primary)]"
            >
              ← COMMAND CENTER
            </Link>
          </nav>
        </div>
      </header>

      <div className="px-6 lg:px-10 pb-24">
        {/* Hero */}
        <section className="pt-20 pb-16">
          <p className="hud-stamp !text-[10px] text-teal-core mb-5">
            OPERATOR HANDBOOK · REV 11
          </p>
          <h1 className="font-display font-bold tracking-tight leading-[1.02] text-balance break-words text-[clamp(2rem,5vw,3.6rem)] max-w-3xl">
            Aureon System Guide
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-titanium">
            Understanding the digital twin, decisions, and intelligence layer.
          </p>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
            An explainable urban intelligence platform that simulates emergency
            response decisions across Bengaluru.
          </p>

          <div className="mt-10">
            <SystemTour />
          </div>
        </section>

        <div className="space-y-20">
          {/* 01 — System map */}
          <section className="space-y-7">
            <SectionStamp n="01" title="How the system fits together" />
            <p className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
              Five stages turn a living city into accountable decisions. Select
              any stage to read what happens there.
            </p>
            <InteractiveSystemMap />
          </section>

          {/* 02 — Concepts */}
          <section className="space-y-7">
            <SectionStamp n="02" title="Core concepts" />
            <div className="grid gap-x-12 gap-y-8 md:grid-cols-2">
              <ConceptBlock title="THE DIGITAL TWIN" kind="system">
                A live model of Bengaluru&apos;s emergency network — roads,
                hospitals, response bases and moving units rendered in real
                time from engine state.
              </ConceptBlock>
              <ConceptBlock title="EXPLAINABLE AI" kind="intelligence">
                Every dispatch decision includes the factors considered and the
                tradeoffs made. The interface renders the engine&apos;s own
                words; it never invents a justification.
              </ConceptBlock>
              <ConceptBlock title="EVIDENCE REPLAY" kind="evidence">
                Runs are frame-recorded as they happen. Debriefs are assembled
                from recorded facts — reported, dispatched, closed — with
                measured response times.
              </ConceptBlock>
              <ConceptBlock title="COVERAGE-FIRST DISPATCH" kind="system">
                Sending the nearest unit is not always right. The strategy
                weighs how a choice leaves the rest of the city protected.
              </ConceptBlock>
              <ConceptBlock title="THE DECISION LEDGER" kind="evidence">
                A running audit trail of everything the engine actually did —
                incidents observed, units dispatched, cases resolved. Newest
                entries appear as the run unfolds; scroll inside the panel for
                full history. Entries marked EXPLAIN carry the engine&apos;s own
                reasoning — open them to see factors and tradeoffs.
              </ConceptBlock>
            </div>
          </section>

          {/* 03 — Reading the map */}
          <section className="space-y-7">
            <SectionStamp n="03" title="Reading the map" />
            <p className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
              Every layer in the Command Center&apos;s twin has a meaning. If it
              moves, glows, or pulses, it is telling you something about the
              network.
            </p>
            <div className="grid gap-x-12 gap-y-8 md:grid-cols-2">
              <ConceptBlock title="ROAD NETWORK" kind="system">
                White luminous lines are Bengaluru&apos;s real street network,
                drawn from map data. Brighter lines are major arteries; fainter
                ones are secondary streets.
              </ConceptBlock>
              <ConceptBlock title="HOSPITALS" kind="evidence">
                Blue beacons with a rising light pillar mark real hospitals.
                Click one for its identity and live status.
              </ConceptBlock>
              <ConceptBlock title="AMBULANCE STATIONS" kind="system">
                Teal pads on the ground are response bases — where units wait
                between calls.
              </ConceptBlock>
              <ConceptBlock title="AMBULANCES" kind="system">
                Moving teal markers are live units. They appear once a run is
                active; between runs they rest at their stations.
              </ConceptBlock>
              <ConceptBlock title="INCIDENTS" kind="critical">
                Red signals pulse where emergencies happen during a run.
              </ConceptBlock>
              <ConceptBlock title="ROUTE FLOW" kind="system">
                Small moving particles stream along arteries — the city&apos;s
                ambient traffic. Always present, even between runs.
              </ConceptBlock>
            </div>
          </section>

          {/* 04 — Compare mode */}
          <section className="space-y-7">
            <SectionStamp n="04" title="Compare mode" />
            <p className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
              The <span className="font-mono text-[13px] text-teal-core">/compare</span>{' '}
              page answers one question: what changes when Aureon dispatches?
            </p>
            <div className="grid gap-x-12 gap-y-8 md:grid-cols-2">
              <ConceptBlock title="SCENARIO DEMO" kind="intelligence">
                A guided walkthrough of four canonical emergencies — cardiac,
                collision, fire, multiple casualties — animated side by side.
                Values are clearly stamped teaching examples, not measurements.
              </ConceptBlock>
              <ConceptBlock title="CUSTOM SCENARIO SIMULATOR" kind="intelligence">
                Build your own emergency: pick the incident type, type or
                choose a Bengaluru locality, set severity, and add context —
                traffic, weather, time of day. Run Aureon Analysis, then read
                the prediction top to bottom: unit, response time, hospital,
                and the reasoning behind each choice.
              </ConceptBlock>
              <ConceptBlock title="LOCATION INTELLIGENCE" kind="intelligence">
                The simulator reasons over real city context — locality
                coordinates, hospital capability profiles, ambulance base
                positions and response zones. Distances are measured, not
                invented; ETA bends with traffic, weather, hour and priority.
                A stamped demonstration of how the engine reads the city.
              </ConceptBlock>
              <ConceptBlock title="WHAT THE ANALYSIS RETURNS" kind="intelligence">
                Three answers — a recommended unit with its medical class, an
                estimated response time shaped by your conditions, and a
                destination hospital — followed by the reasoning: why this
                unit won, what was traded off, and why that hospital.
              </ConceptBlock>
              <ConceptBlock title="BASELINE DISPATCH" kind="evidence">
                The conventional strategy: always send the closest available
                unit. Every comparison measures improvement against it.
              </ConceptBlock>
              <ConceptBlock title="ENGINE EVIDENCE" kind="evidence">
                Two paths produce engine-reported numbers only: paired replays
                of completed runs sharing an identical scenario, and a
                controlled benchmark that runs both strategies on the same
                schedule.
              </ConceptBlock>
              <ConceptBlock title="OUTCOME DELTA" kind="evidence">
                Metric-by-metric difference between strategies — response
                times, golden-hour compliance, capability match — with every
                improved or degraded line counted.
              </ConceptBlock>
            </div>
          </section>

          {/* 05 — Why this decision */}
          <section className="space-y-7">
            <SectionStamp n="05" title="Why this decision?" />
            <p className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
              This is what an explanation looks like inside Aureon — same
              structure as the live panel, filled here with a teaching example.
            </p>
            <div className="max-w-2xl">
              <ExampleDecision />
            </div>
          </section>

          {/* 06 — Glossary */}
          <section className="space-y-7">
            <SectionStamp n="06" title="Glossary" />
            <Glossary />
          </section>

          {/* 07 — Architecture (collapsed) */}
          <section className="space-y-7">
            <SectionStamp n="07" title="Under the hood" />
            <p className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
              In plain terms: a deterministic city simulation runs on a Python
              backend, makes dispatch decisions with recorded reasoning, and
              streams evidence to this console.
            </p>
            <ArchitectureSection />
          </section>
        </div>

        {/* Footer handoff */}
        <footer className="mt-24 border-t border-hairline pt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-md text-sm leading-relaxed text-[var(--color-text-secondary)]">
            Ready to see it live? The Command Center runs real simulations with
            full decision evidence.
          </p>
          <Link
            href="/command?intro=1"
            className="shrink-0 rounded-md bg-teal-core px-8 py-3.5 text-sm font-semibold tracking-wide text-black transition-all hover:brightness-110 hover:shadow-[0_0_24px_rgba(22,242,212,0.25)]"
          >
            ENTER COMMAND CENTER →
          </Link>
        </footer>
      </div>
    </main>
  );
}
