import { create } from 'zustand';

export type TwinSelection =
  | { kind: 'ambulance'; id: string }
  | { kind: 'hospital'; id: string }
  | { kind: 'incident'; id: string }
  | null;

interface TwinStore {
  selection: TwinSelection;
  hovered: string | null;
  select: (selection: TwinSelection) => void;
  /** Deterministic selection (no toggle) — used by replay evidence clicks. */
  focus: (selection: NonNullable<TwinSelection>) => void;
  setHovered: (id: string | null) => void;
}

/** Selection state for the twin scene. Low-frequency — safe for React. */
export const useTwinStore = create<TwinStore>((set) => ({
  selection: null,
  hovered: null,
  select: (selection) =>
    set((s) => ({
      // Clicking the selected entity again deselects
      selection:
        s.selection && selection && s.selection.id === selection.id
          ? null
          : selection,
    })),
  focus: (selection) => set({ selection }),
  setHovered: (hovered) => set({ hovered }),
}));
