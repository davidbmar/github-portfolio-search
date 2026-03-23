/**
 * Collections Manager for GitHub Portfolio Search.
 * Lets users save groups of repos as named collections in localStorage.
 */

const CollectionsManager = (() => {
  const STORAGE_KEY = "ghps_collections";

  function _load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.collections)) {
          return parsed;
        }
      }
    } catch (e) {
      // corrupted data — reset
    }
    return { collections: [] };
  }

  function _save(data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  function getAll() {
    return _load().collections;
  }

  function getCollection(name) {
    return getAll().find((c) => c.name === name) || null;
  }

  function create(name) {
    const data = _load();
    if (data.collections.some((c) => c.name === name)) {
      return data.collections.find((c) => c.name === name);
    }
    const collection = {
      name: name,
      repos: [],
      created: new Date().toISOString(),
    };
    data.collections.push(collection);
    _save(data);
    return collection;
  }

  function addRepo(collectionName, repoName) {
    const data = _load();
    const collection = data.collections.find((c) => c.name === collectionName);
    if (!collection) return null;
    if (!collection.repos.includes(repoName)) {
      collection.repos.push(repoName);
      _save(data);
    }
    return collection;
  }

  function removeRepo(collectionName, repoName) {
    const data = _load();
    const collection = data.collections.find((c) => c.name === collectionName);
    if (!collection) return null;
    collection.repos = collection.repos.filter((r) => r !== repoName);
    _save(data);
    return collection;
  }

  function deleteCollection(name) {
    const data = _load();
    const idx = data.collections.findIndex((c) => c.name === name);
    if (idx === -1) return false;
    data.collections.splice(idx, 1);
    _save(data);
    return true;
  }

  return {
    getAll,
    getCollection,
    create,
    addRepo,
    removeRepo,
    deleteCollection,
  };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = CollectionsManager;
}
