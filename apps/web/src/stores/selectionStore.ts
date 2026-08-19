import { create } from 'zustand';

interface SelectionStore {
  selectedHandles: string[];
  toggle: (handle: string) => void;
  select: (handle: string) => void;
  deselect: (handle: string) => void;
  clear: () => void;
  selectAll: (handles: string[]) => void;
}

export const useSelectionStore = create<SelectionStore>((set) => ({
  selectedHandles: [],
  toggle: (handle) =>
    set((state) => ({
      selectedHandles: state.selectedHandles.includes(handle)
        ? state.selectedHandles.filter((h) => h !== handle)
        : [...state.selectedHandles, handle],
    })),
  select: (handle) =>
    set((state) => ({
      selectedHandles: state.selectedHandles.includes(handle)
        ? state.selectedHandles
        : [...state.selectedHandles, handle],
    })),
  deselect: (handle) =>
    set((state) => ({
      selectedHandles: state.selectedHandles.filter((h) => h !== handle),
    })),
  clear: () => set({ selectedHandles: [] }),
  selectAll: (handles) => set({ selectedHandles: handles }),
}));
