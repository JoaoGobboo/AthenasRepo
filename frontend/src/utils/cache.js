const CACHE_PREFIX = "athenas-cache::";

export const loadCache = (key, ttlSeconds = 0) => {
  try {
    const stored = sessionStorage.getItem(`${CACHE_PREFIX}${key}`);
    if (!stored) {
      return null;
    }
    const payload = JSON.parse(stored);
    if (!payload?.timestamp) {
      return payload?.data ?? null;
    }
    if (ttlSeconds > 0) {
      const age = Date.now() - payload.timestamp;
      if (age > ttlSeconds * 1000) {
        sessionStorage.removeItem(`${CACHE_PREFIX}${key}`);
        return null;
      }
    }
    return payload.data;
  } catch (error) {
    console.warn("Failed to load cache", key, error);
    return null;
  }
};

export const saveCache = (key, data) => {
  try {
    const payload = {
      timestamp: Date.now(),
      data
    };
    sessionStorage.setItem(`${CACHE_PREFIX}${key}`, JSON.stringify(payload));
  } catch (error) {
    console.warn("Failed to save cache", key, error);
  }
};

export const clearCacheKey = (key) => {
  sessionStorage.removeItem(`${CACHE_PREFIX}${key}`);
};
