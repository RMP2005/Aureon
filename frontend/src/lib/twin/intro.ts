/**
 * Landing → operations camera handoff (Phase 10F-1).
 *
 * A one-shot module flag: the command page sets it when the operator
 * arrives from the landing journey (`?intro=1`), and the twin's camera rig
 * consumes it on mount to descend from the landing's hero framing into the
 * operational view. Cancelable by any user input — the operator always wins.
 */

let pending = false;

export function requestIntroSweep(): void {
  pending = true;
}

export function consumeIntroSweep(): boolean {
  if (!pending) return false;
  pending = false;
  return true;
}
