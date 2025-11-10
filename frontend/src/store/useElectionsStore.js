import { create } from "zustand";
import { fetchElections } from "../services/api.js";
import { loadCache, saveCache, clearCacheKey } from "../utils/cache.js";

const CACHE_KEY = "global-elections";
const TTL_SECONDS = 60;
const initialCache = loadCache(CACHE_KEY, TTL_SECONDS) || [];

const useElectionsStore = create((set, get) => ({
  elections: initialCache,
  loading: false,
  error: null,
  lastFetched: initialCache.length ? Date.now() : 0,
  async fetchElections({ forceRefresh = false } = {}) {
    const { loading, lastFetched, elections } = get();
    if (
      !forceRefresh &&
      elections.length &&
      Date.now() - lastFetched < TTL_SECONDS * 1000
    ) {
      return elections;
    }
    if (loading) {
      return elections;
    }
    set({ loading: true, error: null });
    try {
      const data = await fetchElections();
      saveCache(CACHE_KEY, data);
      set({ elections: data, loading: false, lastFetched: Date.now() });
      return data;
    } catch (error) {
      set({ error, loading: false });
      throw error;
    }
  },
  invalidate() {
    clearCacheKey(CACHE_KEY);
    set({ lastFetched: 0 });
  }
}));

export default useElectionsStore;
