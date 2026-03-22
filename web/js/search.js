/**
 * Client-side search engine for GitHub Portfolio Search.
 * Matches text across repo name, description, topics, and README excerpts.
 * Supports faceted filtering by language, topics, and stars.
 */

const SearchEngine = (() => {
  // --- Search index state (populated by loadSearchIndex) ---
  let _invertedIndex = null; // term -> Set of repo names
  let _chunkTextMap = null;  // repo_name -> concatenated chunk text (lowercase)
  let _chunkRawMap = null;   // repo_name -> array of { source, text } (original case)
  let _totalRepos = 0;       // N for IDF computation

  /**
   * Tokenize a query string into lowercase terms.
   */
  function tokenize(text) {
    if (!text) return [];
    return text
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 0);
  }

  /**
   * Load a search index (parsed search-index.json array) and build:
   *  - An inverted index: term -> Set of repo names (for IDF)
   *  - A per-repo chunk text map: repo_name -> concatenated lowercase text
   *  - A per-repo raw chunks map for snippet extraction
   */
  function loadSearchIndex(data) {
    if (!Array.isArray(data) || data.length === 0) return;

    _invertedIndex = {};
    _chunkTextMap = {};
    _chunkRawMap = {};
    _totalRepos = data.length;

    for (const entry of data) {
      const repo = entry.repo;
      if (!repo) continue;

      // Build inverted index from keywords
      const keywords = entry.keywords || [];
      for (const kw of keywords) {
        const term = kw.toLowerCase();
        if (!term) continue;
        if (!_invertedIndex[term]) {
          _invertedIndex[term] = new Set();
        }
        _invertedIndex[term].add(repo);
      }

      // Build chunk text map (concatenated lowercase for matching)
      const chunks = entry.chunks || [];
      const texts = chunks.map((c) => c.text || "");
      _chunkTextMap[repo] = texts.join(" ").toLowerCase();
      _chunkRawMap[repo] = chunks;
    }
  }

  /**
   * Check if a term matches a text field.
   * For terms longer than 5 characters, also matches as a substring of
   * any word (fuzzy tolerance). For shorter terms, requires exact inclusion.
   */
  function termMatches(term, text) {
    return text.includes(term);
  }

  /**
   * Compute IDF weight for a term: log(N / df).
   * Returns 1.0 if inverted index is not loaded or term not found.
   */
  function _idfWeight(term) {
    if (!_invertedIndex || !_totalRepos) return 1.0;
    const docSet = _invertedIndex[term];
    const df = docSet ? docSet.size : 0;
    if (df === 0) return 1.0;
    return Math.log(_totalRepos / df);
  }

  /**
   * Compute a relevance score for a repo against query terms.
   * Higher score = better match.
   *
   * Scoring weights:
   *  - Exact phrase match (all terms in order): 50 point bonus
   *  - Repo name match: 10 points per term
   *  - Topic match: 6 points per term
   *  - Description match: 3 points per term
   *  - README excerpt match: 1 point per term
   *  - Chunk text match: 2 points per term (when search index loaded)
   *  - Multi-term bonus: extra points when more terms match
   *  - TF-IDF weighting: all field scores multiplied by IDF when index loaded
   *
   * Uses OR logic: a repo matches if ANY term matches at least one field.
   * Returns 0 only if no terms match at all.
   */
  function scoreRepo(repo, terms, fullQuery) {
    if (!terms.length) return 1; // No query = show everything equally

    const name = (repo.name || "").toLowerCase();
    const desc = (repo.description || "").toLowerCase();
    const topics = (repo.topics || []).map((t) => t.toLowerCase());
    const readme = (repo.readme_excerpt || "").toLowerCase();
    const chunkText = _chunkTextMap ? (_chunkTextMap[repo.name] || "") : "";

    let score = 0;
    let matched = 0;

    for (const term of terms) {
      let termScore = 0;

      if (termMatches(term, name)) {
        termScore += 10;
        // Bonus for exact name match
        if (name === term) termScore += 5;
      }

      for (const topic of topics) {
        if (termMatches(term, topic)) {
          termScore += 6;
          break;
        }
      }

      if (termMatches(term, desc)) {
        termScore += 3;
      }

      if (termMatches(term, readme)) {
        termScore += 1;
      }

      // Chunk text matching (when search index is loaded)
      if (chunkText && termMatches(term, chunkText)) {
        termScore += 2;
      }

      // Apply IDF weighting when search index is loaded
      if (termScore > 0) {
        const idf = _idfWeight(term);
        termScore *= idf;
        matched++;
        score += termScore;
      }
    }

    // OR logic: at least one term must match
    if (matched === 0) return 0;

    // Bonus for multiple term matches (rewards broader relevance)
    if (terms.length > 1 && matched > 1) {
      score += matched * 5;
    }

    // Exact phrase bonus: if the full multi-word query appears verbatim
    if (fullQuery && terms.length > 1) {
      const phrase = fullQuery.toLowerCase();
      if (
        name.includes(phrase) ||
        desc.includes(phrase) ||
        readme.includes(phrase) ||
        topics.some((t) => t.includes(phrase))
      ) {
        score += 50;
      }
    }

    // Boost by stars (logarithmic)
    const starBoost = Math.log2((repo.stars || 0) + 1) * 0.5;
    return score + starBoost;
  }

  /**
   * Search repos by query string.
   * Returns sorted array of { repo, score } objects.
   * Handles empty or missing repos array gracefully.
   */
  function search(repos, query) {
    if (!Array.isArray(repos) || repos.length === 0) return [];

    const terms = tokenize(query);
    const fullQuery = (query || "").trim();
    const results = [];

    for (const repo of repos) {
      const score = scoreRepo(repo, terms, fullQuery);
      if (score > 0) {
        results.push({ repo, score });
      }
    }

    results.sort((a, b) => b.score - a.score);
    return results;
  }

  /**
   * Apply faceted filters to a list of repos.
   *
   * filters: {
   *   languages: string[],    // empty = all
   *   topics: string[],       // empty = all
   *   minStars: number,       // 0 = no minimum
   * }
   */
  function applyFilters(repos, filters) {
    if (!Array.isArray(repos) || repos.length === 0) return [];
    return repos.filter((repo) => {
      // Language filter
      if (filters.languages && filters.languages.length > 0) {
        if (!filters.languages.includes(repo.language)) return false;
      }

      // Topics filter
      if (filters.topics && filters.topics.length > 0) {
        const repoTopics = repo.topics || [];
        const hasMatchingTopic = filters.topics.some((t) =>
          repoTopics.includes(t)
        );
        if (!hasMatchingTopic) return false;
      }

      // Stars filter
      if (filters.minStars && (repo.stars || 0) < filters.minStars) {
        return false;
      }

      return true;
    });
  }

  /**
   * Extract available facets from a list of repos.
   * Returns { languages: [{name, count}], topics: [{name, count}], maxStars }
   */
  function extractFacets(repos) {
    if (!Array.isArray(repos) || repos.length === 0) {
      return { languages: [], topics: [], maxStars: 0 };
    }
    const langCounts = {};
    const topicCounts = {};
    let maxStars = 0;

    for (const repo of repos) {
      if (repo.language) {
        langCounts[repo.language] = (langCounts[repo.language] || 0) + 1;
      }

      const topics = repo.topics || [];
      for (const t of topics) {
        topicCounts[t] = (topicCounts[t] || 0) + 1;
      }

      if ((repo.stars || 0) > maxStars) {
        maxStars = repo.stars || 0;
      }
    }

    const languages = Object.entries(langCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    const topics = Object.entries(topicCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15); // Cap at top 15 topics

    return { languages, topics, maxStars };
  }

  /**
   * Sort search results by the given mode.
   * Modes: "relevance" (default, by score), "recent" (by updated_at desc), "name" (A-Z).
   */
  function sortResults(results, mode) {
    if (!Array.isArray(results)) return [];
    const sorted = results.slice();
    if (mode === "recent") {
      sorted.sort((a, b) => (b.repo.updated_at || "").localeCompare(a.repo.updated_at || ""));
    } else if (mode === "name") {
      sorted.sort((a, b) => (a.repo.name || "").localeCompare(b.repo.name || ""));
    }
    // "relevance" is the default order from search(), no re-sort needed
    return sorted;
  }

  /**
   * Find a ~200 char excerpt from a repo's chunks that best matches the query.
   * Returns null if no match or search index not loaded.
   * Does NOT do HTML escaping (caller handles that).
   */
  function getSnippet(repoName, query) {
    if (!_chunkRawMap || !_chunkRawMap[repoName]) return null;

    const terms = tokenize(query);
    if (terms.length === 0) return null;

    const chunks = _chunkRawMap[repoName];
    let bestChunk = null;
    let bestCount = 0;

    // Find the chunk with the most matching terms
    for (const chunk of chunks) {
      const text = (chunk.text || "").toLowerCase();
      let count = 0;
      for (const term of terms) {
        if (text.includes(term)) count++;
      }
      if (count > bestCount) {
        bestCount = count;
        bestChunk = chunk;
      }
    }

    if (!bestChunk || bestCount === 0) return null;

    const text = bestChunk.text || "";
    const textLower = text.toLowerCase();

    // Find position of first matching term
    let firstPos = text.length;
    for (const term of terms) {
      const pos = textLower.indexOf(term);
      if (pos !== -1 && pos < firstPos) {
        firstPos = pos;
      }
    }

    // Extract ~200 char excerpt centered on the first match
    const excerptLen = 200;
    const half = Math.floor(excerptLen / 2);
    let start = Math.max(0, firstPos - half);
    let end = Math.min(text.length, start + excerptLen);
    // Adjust start if we're near the end
    if (end - start < excerptLen) {
      start = Math.max(0, end - excerptLen);
    }

    let snippet = text.slice(start, end).trim();
    if (start > 0) snippet = "..." + snippet;
    if (end < text.length) snippet = snippet + "...";

    return snippet;
  }

  return { search, applyFilters, extractFacets, tokenize, sortResults, loadSearchIndex, getSnippet };
})();

// Export for testing or module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = SearchEngine;
}
