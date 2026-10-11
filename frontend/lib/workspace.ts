"use client";
import { create } from "zustand";

const safe = <T,>(f: () => T, d: T): T => { try { return f(); } catch { return d; } };
const read = <T,>(k: string, d: T): T => safe(() => { const v = localStorage.getItem(k); return v ? (JSON.parse(v) as T) : d; }, d);
const write = (k: string, v: unknown) => safe(() => localStorage.setItem(k, JSON.stringify(v)), undefined);

export type SavedLayout = { id: string; name: string; layout: Record<string, any>; savedAt: string };

/** UI-only workspace state. Business data never lives here (it comes from the API); layouts are saved per browser, not on the server. */
type W = {
  collapsed: boolean; toggleCollapsed: () => void;
  paletteOpen: boolean; setPalette: (o: boolean) => void;
  /** entity selection shared by the investigation panels */
  productId: string | null; locationId: string | null; selectProduct: (id: string | null) => void; selectLocation: (id: string | null) => void;
  layouts: SavedLayout[]; saveLayout: (name: string, layout: Record<string, any>) => void; deleteLayout: (id: string) => void;
  hydrate: () => void;
};
export const useWorkspace = create<W>((set, get) => ({
  collapsed: false, paletteOpen: false, productId: null, locationId: null, layouts: [],
  toggleCollapsed: () => { const collapsed = !get().collapsed; write("mb_sidebar_collapsed", collapsed); set({ collapsed }); },
  setPalette: (paletteOpen) => set({ paletteOpen }),
  selectProduct: (productId) => set({ productId }),
  selectLocation: (locationId) => set({ locationId }),
  saveLayout: (name, layout) => { const layouts = [...get().layouts.filter((l) => l.name !== name), { id: `${Date.now()}`, name, layout, savedAt: new Date().toISOString() }].slice(-12); write("mb_layouts", layouts); set({ layouts }); },
  deleteLayout: (id) => { const layouts = get().layouts.filter((l) => l.id !== id); write("mb_layouts", layouts); set({ layouts }); },
  hydrate: () => set({ collapsed: read("mb_sidebar_collapsed", false), layouts: read<SavedLayout[]>("mb_layouts", []) }),
}));
