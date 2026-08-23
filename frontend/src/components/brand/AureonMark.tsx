/**
 * Aureon identity mark (Phase 11-refinement).
 *
 * Brutalist technical glyph: a framed "A" with a live-systems crossbar.
 * Deliberately small — it is a signature, never a centerpiece. Allowed
 * surfaces: navbar, mission bar, favicon, metadata.
 */
export default function AureonMark({
  size = 20,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      {/* Frame — the instrument bezel */}
      <rect x="1" y="1" width="30" height="30" stroke="#3A4658" strokeWidth="2" />
      {/* A — ink silhouette */}
      <path d="M16 6.5 L26 25.5 H21.4 L16 13.9 L10.6 25.5 H6 Z" fill="#EDF2F7" />
      {/* Crossbar — operational state (teal = live systems) */}
      <rect x="12.4" y="19.2" width="7.2" height="2.6" fill="#16F2D4" />
    </svg>
  );
}
