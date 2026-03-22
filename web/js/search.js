/**
 * Client-side search engine for GitHub Portfolio Search.
 * Matches text across repo name, description, topics, and README excerpts.
 * Supports faceted filtering by language, topics, and stars.
 */

const SearchEngine = (() => {
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
   * Compute a relevance score for a repo against query terms.
   * Higher score = better match.
   *
   * Scoring weights:
   *  - Repo name match: 10 points per term
   *  - Topic match: 6 points per term
   *  - Description match: 3 points per term
   *  - README excerpt match: 1 point per term
   *
   * Returns 0 if no terms match at all.
   */
  function scoreRepo(repo, terms) {
    if (!terms.length) return 1; // No query = show everything equally

    const name = (repo.name || "").toLowerCase();
    const desc = (repo.description || "").toLowerCase();
    const topics = (repo.topics || []).map((t) => t.toLowerCase());
    const readme = (repo.readme_excerpt || "").toLowerCase();

    let score = 0;
    let matched = 0;

    for (const term of terms) {
      let termScore = 0;

      if (name.includes(term)) {
        termScore += 10;
        // Bonus for exact name match
        if (name === term) termScore += 5;
      }

      for (const topic of topics) {
        if (topic.includes(term)) {
          termScore += 6;
          break;
        }
      }

      if (desc.includes(term)) {
        termScore += 3;
      }

      if (readme.includes(term)) {
        termScore += 1;
      }

      if (termScore > 0) {
        matched++;
        score += termScore;
      }
    }

    // All terms must match at least one field
    if (matched < terms.length) return 0;

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
    const results = [];

    for (const repo of repos) {
      const score = scoreRepo(repo, terms);
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
      .slice(0, 20); // Cap at top 20 topics

    return { languages, topics, maxStars };
  }

  return { search, applyFilters, extractFacets, tokenize };
})();

// Export for testing or module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = SearchEngine;
}
