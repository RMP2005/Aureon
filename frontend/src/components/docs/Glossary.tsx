import ConceptBlock from './ConceptBlock';

/**
 * Glossary — operator vocabulary (Phase 11F).
 * Plain-language definitions; one line each, no walls of text.
 */
const TERMS: { term: string; kind: 'system' | 'intelligence' | 'evidence'; def: string }[] = [
  {
    term: 'ETA',
    kind: 'system',
    def: 'Estimated arrival time — how long a unit needs to reach the scene or a hospital.',
  },
  {
    term: 'Coverage',
    kind: 'system',
    def: 'How well available units protect the zones that currently have none nearby.',
  },
  {
    term: 'Severity',
    kind: 'evidence',
    def: 'Emergency priority. Higher severity claims faster units and sirens.',
  },
  {
    term: 'Decision Evidence',
    kind: 'intelligence',
    def: "The information Aureon's AI used when choosing an action — factors, tradeoffs, and the alternatives it rejected.",
  },
  {
    term: 'Baseline',
    kind: 'evidence',
    def: 'The conventional strategy — always send the closest available unit. Every comparison measures improvement against it.',
  },
  {
    term: 'Route Flow',
    kind: 'system',
    def: "Moving particles along arteries showing the city's ambient traffic. Context, not live ambulances.",
  },
  {
    term: 'Golden Hour',
    kind: 'evidence',
    def: 'The first hour after traumatic injury, when treatment most affects survival.',
  },
  {
    term: 'Custom Scenario',
    kind: 'intelligence',
    def: "A demo emergency you define — type, location, severity, and conditions. Aureon's recommendation is a stamped teaching example.",
  },
  {
    term: 'Decision Ledger',
    kind: 'evidence',
    def: "The command center's audit trail — every observed incident, dispatch and resolution, with the engine's own reasoning attached.",
  },
  {
    term: 'Response Zone',
    kind: 'system',
    def: 'A geographic sector of the city whose crews cover it — and whose neighbours must stay protected during any dispatch.',
  },
];

export default function Glossary() {
  return (
    <div className="grid gap-x-10 gap-y-6 md:grid-cols-2">
      {TERMS.map((t) => (
        <ConceptBlock key={t.term} title={t.term.toUpperCase()} kind={t.kind}>
          {t.def}
        </ConceptBlock>
      ))}
    </div>
  );
}
