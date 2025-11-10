import { create } from "zustand";
import { fetchResults } from "../services/api.js";

const TTL_DB_MS = 30 * 1000;
const TTL_CHAIN_MS = 60 * 1000;

const useResultsStore = create((set, get) => ({
  items: {},
  loadingDb: {},
  loadingChain: {},
  error: null,

  getResult(id) {
    const entry = get().items[id];
    return entry?.chain?.data || entry?.db?.data || null;
  },

  isChainLoading(id) {
    return Boolean(get().loadingChain[id]);
  },

  async fetchResult(id) {
    await get()._ensureDb(id);
    get()._ensureChain(id);
  },

  async _ensureDb(id) {
    const entry = get().items[id];
    if (entry?.db && Date.now() - entry.db.fetchedAt < TTL_DB_MS) {
      return entry.db.data;
    }
    if (get().loadingDb[id]) {
      return entry?.db?.data;
    }
    set((state) => ({
      loadingDb: { ...state.loadingDb, [id]: true },
      error: null,
    }));
    try {
      const data = await fetchResults(id, { includeBlockchain: false });
      set((state) => ({
        items: {
          ...state.items,
          [id]: {
            ...state.items[id],
            db: { data, fetchedAt: Date.now() },
          },
        },
      }));
      return data;
    } catch (error) {
      set((state) => ({ error }));
      throw error;
    } finally {
      set((state) => {
        const next = { ...state.loadingDb };
        delete next[id];
        return { loadingDb: next };
      });
    }
  },

  async _ensureChain(id) {
    const entry = get().items[id];
    if (entry?.chain && Date.now() - entry.chain.fetchedAt < TTL_CHAIN_MS) {
      return entry.chain.data;
    }
    if (get().loadingChain[id]) {
      return entry?.chain?.data;
    }
    set((state) => ({
      loadingChain: { ...state.loadingChain, [id]: true },
    }));
    try {
      const data = await fetchResults(id);
      if (data.source === "blockchain") {
        set((state) => ({
          items: {
            ...state.items,
            [id]: {
              ...state.items[id],
              chain: { data, fetchedAt: Date.now() },
            },
          },
        }));
      }
      return data;
    } catch (error) {
      // ignore individual chain errors; store last error for reference
      set((state) => ({ error }));
      return null;
    } finally {
      set((state) => {
        const next = { ...state.loadingChain };
        delete next[id];
        return { loadingChain: next };
      });
    }
  },

  invalidate(id) {
    if (id) {
      set((state) => {
        const next = { ...state.items };
        delete next[id];
        return { items: next };
      });
    } else {
      set({ items: {} });
    }
  },
}));

export default useResultsStore;
