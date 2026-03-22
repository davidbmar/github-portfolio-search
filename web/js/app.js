/**
 * Main application for GitHub Portfolio Search.
 * Handles data loading, hash routing, rendering, and user interaction.
 *
 * Security: All dynamic content is escaped via escapeHtml() / escapeAttr()
 * before DOM insertion. escapeHtml uses createTextNode which is XSS-safe.
 */

// --- Public-First Initialization ---
// All content is publicly browsable without sign-in.
// Sign-in is optional and enables gated features.
(() => {
  document.addEventListener("DOMContentLoaded", async () => {
    await Auth.loadConfig();

    // Listen for auth changes (sign-in / sign-out)
    Auth.onAuthChange(() => {
      // Full reload ensures clean state after sign-in/sign-out
      location.reload();
    });

    _updateHeaderUserInfo();
    App.init();
  });
})();

/**
 * Update the header to show auth state:
 * - Unauthenticated: "Sign In" button in the nav bar
 * - Authenticated: user avatar + name + "Sign Out" button
 */
function _updateHeaderUserInfo() {
  const nav = document.querySelector(".site-nav");
  if (!nav) return;

  // Remove any existing user-info element
  const existing = document.getElementById("user-info");
  if (existing) existing.remove();

  const userInfo = document.createElement("div");
  userInfo.id = "user-info";
  userInfo.style.cssText = "display:flex;align-items:center;gap:8px;margin-left:auto";

  if (Auth.isAuthenticated()) {
    // Authenticated: show avatar + name + Sign Out
    const user = Auth.getUser();

    if (user && user.picture) {
      const avatar = document.createElement("img");
      avatar.src = user.picture.replace(/^http:\/\//, "https://");
      avatar.alt = (user.name || "User") + " avatar";
      avatar.referrerPolicy = "no-referrer";
      avatar.style.cssText = "width:28px;height:28px;border-radius:50%;border:1px solid #30363d";
      userInfo.appendChild(avatar);
    }

    if (user && user.name) {
      const nameSpan = document.createElement("span");
      nameSpan.textContent = user.name;
      nameSpan.style.cssText = "color:#c9d1d9;font-size:14px;white-space:nowrap";
      userInfo.appendChild(nameSpan);
    }

    const signOutBtn = document.createElement("button");
    signOutBtn.textContent = "Sign Out";
    signOutBtn.style.cssText = "padding:4px 12px;border-radius:6px;border:1px solid #30363d;background:transparent;color:#8b949e;font-size:13px;cursor:pointer;margin-left:4px";
    signOutBtn.addEventListener("click", () => {
      Auth.signOut();
      _updateHeaderUserInfo();
    });
    userInfo.appendChild(signOutBtn);
  } else if (Auth.isOAuthEnabled()) {
    // Unauthenticated with OAuth configured: show Sign In button
    const signInBtn = document.createElement("button");
    signInBtn.textContent = "Sign In";
    signInBtn.style.cssText = "padding:4px 14px;border-radius:6px;border:1px solid #58a6ff;background:transparent;color:#58a6ff;font-size:13px;cursor:pointer;font-weight:500";
    signInBtn.addEventListener("click", () => {
      _showSignInPopup();
    });
    userInfo.appendChild(signInBtn);
  }

  nav.parentElement.appendChild(userInfo);
}

/**
 * Show a modal dialog with the Google Sign-In button.
 * Triggered by the nav bar "Sign In" button.
 */
function _showSignInPopup() {
  // Remove any existing popup
  const existingPopup = document.getElementById("signin-popup-overlay");
  if (existingPopup) existingPopup.remove();

  const overlay = document.createElement("div");
  overlay.id = "signin-popup-overlay";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999";

  const dialog = document.createElement("div");
  dialog.style.cssText = "background:#161b22;border:1px solid #30363d;border-radius:12px;padding:2rem;text-align:center;max-width:360px;width:90%;position:relative";

  const closeBtn = document.createElement("button");
  closeBtn.textContent = "\u00D7";
  closeBtn.style.cssText = "position:absolute;top:8px;right:12px;background:none;border:none;color:#8b949e;font-size:24px;cursor:pointer;line-height:1";
  closeBtn.addEventListener("click", () => overlay.remove());
  dialog.appendChild(closeBtn);

  const h3 = document.createElement("h3");
  h3.textContent = "Sign In";
  h3.style.cssText = "color:#e6edf3;margin:0 0 0.5rem 0";
  dialog.appendChild(h3);

  const p = document.createElement("p");
  p.textContent = "Sign in to access gated features like code search and file browsing.";
  p.style.cssText = "color:#8b949e;margin-bottom:1.5rem;font-size:14px";
  dialog.appendChild(p);

  const btnContainer = document.createElement("div");
  btnContainer.style.cssText = "display:flex;justify-content:center;margin-bottom:1rem";
  dialog.appendChild(btnContainer);

  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  // Close on overlay click (outside dialog)
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });

  Auth.renderSignInButton(btnContainer);
}

const App = (() => {
  // State
  let repos = [];
  let clusters = [];
  let similarity = null;
  let suggestions = null;
  let currentFilters = { languages: [], topics: [], minStars: 0 };
  let facets = { languages: [], topics: [], maxStars: 0 };
  let filtersOpen = false;
  let debounceTimer = null;
  let currentSortMode = "relevance";

  // Language colors (GitHub-style)
  const LANG_COLORS = {
    JavaScript: "#f1e05a",
    TypeScript: "#3178c6",
    Python: "#3572A5",
    Java: "#b07219",
    Go: "#00ADD8",
    Rust: "#dea584",
    C: "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    Ruby: "#701516",
    PHP: "#4F5D95",
    Swift: "#F05138",
    Kotlin: "#A97BFF",
    Shell: "#89e051",
    HTML: "#e34c26",
    CSS: "#563d7c",
    Dart: "#00B4AB",
    Lua: "#000080",
    Vim: "#199f4b",
    HCL: "#844FBA",
    Makefile: "#427819",
    Dockerfile: "#384d54",
  };

  /**
   * Escape HTML special characters to prevent XSS.
   * Uses createTextNode which is inherently safe.
   */
  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function escapeAttr(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // Sample fallback data shown when fetch fails or data is empty
  const SAMPLE_REPOS = [
    {
      name: "sample-project",
      description: "This is sample data shown when no real data is available. Run ghps index to populate.",
      language: "Python",
      stars: 0,
      topics: ["sample", "placeholder"],
      url: "",
      updated_at: new Date().toISOString(),
    },
  ];

  const SAMPLE_CLUSTERS = [
    {
      name: "Sample Cluster",
      repos: ["sample-project"],
      description: "Sample cluster shown when no data is loaded.",
    },
  ];

  /**
   * Build a loading skeleton using safe DOM methods.
   */
  function buildLoadingSkeleton() {
    const wrapper = document.createElement("div");
    wrapper.className = "loading-skeleton";
    const wide = document.createElement("div");
    wide.className = "skeleton-line skeleton-line-wide";
    const med = document.createElement("div");
    med.className = "skeleton-line skeleton-line-medium";
    const narrow = document.createElement("div");
    narrow.className = "skeleton-line skeleton-line-narrow";
    wrapper.appendChild(wide);
    wrapper.appendChild(med);
    wrapper.appendChild(narrow);
    return wrapper;
  }

  /**
   * Load repos.json and clusters.json data files.
   * Falls back to embedded sample data if fetch fails or data is empty.
   */
  async function loadData() {
    const content = document.getElementById("content");
    content.textContent = "";
    content.appendChild(buildLoadingSkeleton());

    try {
      const [reposRes, clustersRes] = await Promise.all([
        fetch("data/repos.json"),
        fetch("data/clusters.json"),
      ]);

      if (!reposRes.ok) throw new Error("Failed to load repos.json");
      if (!clustersRes.ok) throw new Error("Failed to load clusters.json");

      const reposText = await reposRes.text();
      const clustersText = await clustersRes.text();

      const parsedRepos = reposText.trim() ? JSON.parse(reposText) : [];
      const parsedClusters = clustersText.trim() ? JSON.parse(clustersText) : [];

      if (!Array.isArray(parsedRepos) || parsedRepos.length === 0) {
        useFallbackData(content, "No data available \u2014 run ghps index to populate");
        return;
      }

      repos = parsedRepos;
      clusters = Array.isArray(parsedClusters) ? parsedClusters : [];

      // Ensure topics are arrays
      repos = repos.map((r) => ({
        ...r,
        topics: Array.isArray(r.topics)
          ? r.topics
          : typeof r.topics === "string"
            ? tryParseJSON(r.topics, [])
            : [],
      }));

      facets = SearchEngine.extractFacets(repos);

      route();

      // Load optional data files AFTER route (fail silently, never block main render)
      try {
        const optionalFetches = [
          fetch("data/search-index.json").then((r) => r.ok ? r.json() : null).catch(() => null),
          fetch("data/similarity.json").then((r) => r.ok ? r.json() : null).catch(() => null),
          fetch("data/suggestions.json").then((r) => r.ok ? r.json() : null).catch(() => null),
        ];
        const [searchIndex, simData, sugData] = await Promise.all(optionalFetches);

        if (searchIndex && typeof SearchEngine.loadSearchIndex === "function") {
          SearchEngine.loadSearchIndex(searchIndex);
        }
        if (simData) similarity = simData;
        if (sugData) suggestions = sugData;
      } catch (optErr) {
        console.warn("[loadData] Optional data failed (non-critical):", optErr);
      }
    } catch (err) {
      console.error("[loadData] Error loading data:", err);
      useFallbackData(content, "No data available \u2014 run ghps index to populate");
    }
  }

  /**
   * Show a friendly error state with retry button and sample fallback data.
   */
  function useFallbackData(content, message) {
    repos = SAMPLE_REPOS;
    clusters = SAMPLE_CLUSTERS;
    facets = SearchEngine.extractFacets(repos);

    content.textContent = "";
    const banner = document.createElement("div");
    banner.className = "error-banner";

    const icon = document.createElement("span");
    icon.className = "error-banner-icon";
    icon.textContent = "\u26A0";
    banner.appendChild(icon);

    const text = document.createElement("span");
    text.textContent = message;
    banner.appendChild(text);

    const retryBtn = document.createElement("button");
    retryBtn.className = "retry-btn";
    retryBtn.textContent = "Retry";
    retryBtn.addEventListener("click", () => {
      loadData();
    });
    banner.appendChild(retryBtn);

    content.appendChild(banner);

    // Still render sample data below the banner
    const routeContainer = document.createElement("div");
    routeContainer.id = "content-inner";
    content.appendChild(routeContainer);
    renderHome(routeContainer);
  }

  function tryParseJSON(str, fallback) {
    try {
      return JSON.parse(str);
    } catch {
      return fallback;
    }
  }

  /**
   * Hash-based router.
   * Routes: #/ (home), #/search?q=X, #/cluster/name
   */
  function route() {
    const hash = window.location.hash || "#/";
    const content = document.getElementById("content");

    if (hash.startsWith("#/search")) {
      const params = new URLSearchParams(hash.split("?")[1] || "");
      const query = params.get("q") || "";
      renderSearchResults(query, content);
    } else if (hash.startsWith("#/repo/")) {
      const repoName = decodeURIComponent(hash.slice("#/repo/".length));
      renderRepoDetail(repoName, content);
    } else if (hash.startsWith("#/cluster/")) {
      const clusterName = decodeURIComponent(hash.slice("#/cluster/".length));
      renderClusterDetail(clusterName, content);
    } else if (hash === "#/clusters") {
      renderClustersPage(content);
    } else if (hash === "#/access") {
      renderAccessRequest(content);
    } else {
      renderHome(content);
    }
  }

  /**
   * Build sanitized HTML string. All dynamic values MUST pass through
   * escapeHtml() or escapeAttr() before inclusion.
   */

  /**
   * Render the home/landing page with search hero and cluster grid.
   */
  function computePortfolioStats() {
    const langCounts = {};
    let latestDate = "";
    for (const r of repos) {
      if (r.language) {
        langCounts[r.language] = (langCounts[r.language] || 0) + 1;
      }
      if (r.updated_at && r.updated_at > latestDate) {
        latestDate = r.updated_at;
      }
    }
    const sortedLangs = Object.entries(langCounts)
      .sort((a, b) => b[1] - a[1]);
    return { langCounts: sortedLangs, latestDate };
  }

  function renderHome(container) {
    const searchInput = document.getElementById("search-input");
    if (searchInput) searchInput.value = "";

    const stats = computePortfolioStats();

    let html = '<div class="search-hero">';
    html += "<h2>GitHub Portfolio Search</h2>";
    html += "<p>Explore repositories by topic, language, or keyword</p>";

    // Portfolio stats
    html += '<div class="portfolio-stats">';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(String(repos.length)) + '</span><span class="stat-label">Repositories</span></div>';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(String(clusters.length)) + '</span><span class="stat-label">Capability Areas</span></div>';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(String(stats.langCounts.length)) + '</span><span class="stat-label">Languages</span></div>';
    html += "</div>";

    // Language stat row
    if (stats.langCounts.length > 0) {
      html += '<div class="lang-stat-row">';
      for (const [lang, count] of stats.langCounts) {
        const pct = ((count / repos.length) * 100).toFixed(0);
        const color = LANG_COLORS[lang] || "#8b949e";
        html += '<div class="lang-stat-item">';
        html += '<span class="language-dot" style="background:' + escapeAttr(color) + '"></span>';
        html += '<span class="lang-stat-name">' + escapeHtml(lang) + '</span>';
        html += '<span class="lang-stat-bar"><span class="lang-stat-fill" style="width:' + escapeAttr(pct) + '%;background:' + escapeAttr(color) + '"></span></span>';
        html += '<span class="lang-stat-count">' + escapeHtml(String(count)) + '</span>';
        html += "</div>";
      }
      html += "</div>";
    }

    // Last updated
    if (stats.latestDate) {
      html += '<div class="last-updated">Last updated: ' + escapeHtml(formatDate(stats.latestDate)) + "</div>";
    }

    html += "</div>";

    // Cluster grid
    if (clusters.length > 0) {
      html += '<div class="section-header">';
      html += "<h3>Capability Clusters</h3>";
      html += '<span class="count">' + escapeHtml(String(clusters.length)) + " clusters</span>";
      html += "</div>";
      html += '<div class="cluster-grid">';

      for (const cluster of clusters) {
        const repoPreview = (cluster.repos || []).slice(0, 3).join(", ");
        const repoCount = (cluster.repos || []).length;
        html += '<div class="cluster-card" data-cluster="' + escapeAttr(cluster.name) + '">';
        html += "<h4>" + escapeHtml(cluster.name) + "</h4>";
        html += '<span class="repo-count">' + escapeHtml(String(repoCount)) + " repo" + (repoCount !== 1 ? "s" : "") + "</span>";
        if (repoPreview) {
          html += '<div class="repo-list-preview">' + escapeHtml(repoPreview) + "</div>";
        }
        html += "</div>";
      }

      html += "</div>";
    }

    // Recent Activity section
    if (repos.length > 0) {
      const recentRepos = repos
        .filter((r) => r.updated_at)
        .slice()
        .sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""))
        .slice(0, 10);

      if (recentRepos.length > 0) {
        html += '<div class="section-header">';
        html += "<h3>Recent Activity</h3>";
        html += '<span class="count">last updated</span>';
        html += "</div>";
        html += '<div class="recent-activity">';
        for (const repo of recentRepos) {
          const langColor = LANG_COLORS[repo.language] || "#8b949e";
          html += '<div class="recent-activity-item">';
          html += '<a href="#/repo/' + escapeAttr(encodeURIComponent(repo.name)) + '" class="recent-activity-name">' + escapeHtml(repo.name) + '</a>';
          if (repo.language) {
            html += '<span class="language-badge">';
            html += '<span class="language-dot" style="background:' + escapeAttr(langColor) + '"></span>';
            html += escapeHtml(repo.language);
            html += '</span>';
          }
          html += '<span class="recent-activity-date">' + escapeHtml(formatDate(repo.updated_at)) + '</span>';
          html += '</div>';
        }
        html += '</div>';
      }
    }

    // All repos section
    if (repos.length > 0) {
      html += '<div class="section-header">';
      html += "<h3>All Repositories</h3>";
      html += '<span class="count">' + escapeHtml(String(repos.length)) + " repos</span>";
      html += "</div>";
      html += renderRepoCards(
        repos.slice().sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 12)
      );
      if (repos.length > 12) {
        html += '<div class="empty-state"><p>Search to see all ' + escapeHtml(String(repos.length)) + " repositories</p></div>";
      }
    }

    // Footer with last-indexed timestamp
    html += '<footer class="site-footer">';
    const lastIndexed = repos.reduce((latest, r) => {
      return r.last_indexed && r.last_indexed > latest ? r.last_indexed : latest;
    }, "");
    if (lastIndexed) {
      html += '<p class="last-indexed-info">Last indexed: ' + escapeHtml(formatDate(lastIndexed)) + '</p>';
    }
    html += "<p>Powered by GitHub Portfolio Search &mdash; Built with Afterburner</p>";
    html += "</footer>";

    // Safe: all dynamic values above are escaped via escapeHtml/escapeAttr
    container.innerHTML = html;
    bindClusterClicks();
  }

  /**
   * Render search results with filter sidebar.
   */
  /**
   * Highlight query terms in text. Escapes text first, then wraps matches
   * in <mark> tags. Safe because we operate on already-escaped strings.
   */
  function highlightTerms(text, query) {
    if (!text || !query) return escapeHtml(text);
    const terms = SearchEngine.tokenize(query);
    if (terms.length === 0) return escapeHtml(text);
    let escaped = escapeHtml(text);
    for (const term of terms) {
      const escapedTerm = escapeHtml(term);
      const regex = new RegExp("(" + escapedTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      escaped = escaped.replace(regex, "<mark>$1</mark>");
    }
    return escaped;
  }

  function findRelatedRepos(repo, maxCount) {
    const max = maxCount || 3;

    // Try embedding-based similarity first
    if (similarity && similarity[repo.name] && similarity[repo.name].length > 0) {
      const simEntries = similarity[repo.name].slice(0, max);
      const related = simEntries
        .map((entry) => {
          const name = typeof entry === "string" ? entry : entry.name || entry.repo;
          return repos.find((r) => r.name === name);
        })
        .filter(Boolean);
      if (related.length > 0) {
        related._source = "similarity";
        return related;
      }
    }

    // Fall back to cluster-based lookup
    for (const cluster of clusters) {
      if ((cluster.repos || []).includes(repo.name)) {
        const related = (cluster.repos || [])
          .filter((n) => n !== repo.name)
          .slice(0, max)
          .map((name) => repos.find((r) => r.name === name))
          .filter(Boolean);
        related._source = "cluster";
        return related;
      }
    }
    return [];
  }

  function renderSearchResults(query, container) {
    const searchInput = document.getElementById("search-input");
    if (searchInput && searchInput.value !== query) {
      searchInput.value = query;
    }

    // Filter repos first, then search
    const filtered = SearchEngine.applyFilters(repos, currentFilters);
    const rawResults = SearchEngine.search(filtered, query);
    const results = SearchEngine.sortResults(rawResults, currentSortMode);
    const maxScore = rawResults.length > 0 ? rawResults[0].score : 1;

    // Safe: all dynamic values below pass through escapeHtml/escapeAttr
    let html = '<div class="content-layout">';

    // Filter sidebar
    html += renderFilterSidebar();

    // Results area
    html += '<div class="results-area">';
    html += '<button class="filter-toggle" id="filter-toggle">Filters</button>';

    // Sort dropdown
    html += '<div class="sort-controls">';
    html += '<label for="sort-select">Sort by:</label>';
    html += '<select id="sort-select" class="sort-select">';
    html += '<option value="relevance"' + (currentSortMode === "relevance" ? " selected" : "") + '>Relevance</option>';
    html += '<option value="recent"' + (currentSortMode === "recent" ? " selected" : "") + '>Recently Updated</option>';
    html += '<option value="name"' + (currentSortMode === "name" ? " selected" : "") + '>Name A-Z</option>';
    html += '</select>';
    html += '</div>';

    html += '<div class="section-header">';
    if (query) {
      const queryTerms = SearchEngine.tokenize(query);
      if (queryTerms.length > 1) {
        html += '<h3>' + escapeHtml(String(results.length)) + ' results for ' + escapeHtml(queryTerms.join(", ")) + '</h3>';
      } else {
        html += '<h3>Results for &ldquo;' + escapeHtml(query) + '&rdquo;</h3>';
      }
    } else {
      html += "<h3>All Repositories</h3>";
    }
    html += '<span class="count">' + escapeHtml(String(results.length)) + " found</span>";
    html += "</div>";

    if (results.length === 0) {
      html += '<div class="empty-state">';
      html += "<h3>No results found</h3>";
      html += "<p>Try a different search term or adjust filters</p>";
      html += "</div>";
    } else {
      html += renderRepoCards(
        results.map((r) => ({ ...r.repo, _score: r.score, _maxScore: maxScore })),
        query
      );
    }

    // Related repos section
    if (results.length > 0 && query) {
      const topRepo = results[0].repo;
      const related = findRelatedRepos(topRepo, 3);
      if (related.length > 0) {
        const relLabel = related._source === "similarity" ? "Semantically similar" : "from same cluster";
        html += '<div class="related-repos-section">';
        html += '<div class="section-header"><h3>Related Repositories</h3>';
        html += '<span class="count">' + escapeHtml(relLabel) + '</span></div>';
        html += renderRepoCards(related);
        html += "</div>";
      }
    }

    html += "</div>"; // results-area
    html += "</div>"; // content-layout

    // Safe: all dynamic values are escaped via escapeHtml/escapeAttr
    container.innerHTML = html;
    bindFilterEvents();
  }

  /**
   * Render cluster detail view showing repos in that cluster.
   */
  function renderClusterDetail(clusterName, container) {
    const cluster = clusters.find((c) => c.name === clusterName);

    let html = '<a href="#/" class="back-link">&larr; Back to clusters</a>';

    if (!cluster) {
      html += '<div class="empty-state"><h3>Cluster not found</h3></div>';
      container.innerHTML = html;
      return;
    }

    const clusterRepos = repos.filter((r) => (cluster.repos || []).includes(r.name));

    html += '<div class="section-header">';
    html += "<h3>" + escapeHtml(cluster.name) + "</h3>";
    html += '<span class="count">' + escapeHtml(String(clusterRepos.length)) + " repos</span>";
    html += "</div>";

    if (clusterRepos.length > 0) {
      html += renderRepoCards(clusterRepos);
    } else {
      html += '<div class="empty-state"><p>No repos found in this cluster</p></div>';
    }

    // Safe: all dynamic values are escaped
    container.innerHTML = html;
  }

  /**
   * Find which cluster a repo belongs to.
   */
  function findClusterForRepo(repoName) {
    for (const cluster of clusters) {
      if ((cluster.repos || []).includes(repoName)) {
        return cluster;
      }
    }
    return null;
  }

  /**
   * Render repo detail page showing full info about a single repository.
   * Safe: all dynamic values pass through escapeHtml()/escapeAttr() before
   * DOM insertion, consistent with the existing rendering pattern in this file.
   */
  function renderRepoDetail(repoName, container) {
    // NOTE: All dynamic values below are sanitized via escapeHtml() / escapeAttr()
    // before insertion. The github-link SVG and static HTML structure are safe literals.
    // This pattern is consistent with the rest of the codebase (renderHome, renderSearchResults).
    let html = '<a href="#/" class="back-link">&larr; Back to search</a>';

    const repo = repos.find((r) => r.name === repoName);
    if (!repo) {
      html += '<div class="empty-state"><h3>Repository not found</h3></div>';
      container.innerHTML = html;
      return;
    }

    const cluster = findClusterForRepo(repo.name);
    const langColor = LANG_COLORS[repo.language] || "#8b949e";
    const githubUrl = repo.html_url || repo.url;
    const freshness = getFreshnessBadge(repo.updated_at);

    html += '<div class="repo-detail">';

    // Header with name + action buttons
    html += '<div class="repo-detail-header">';
    html += '<h2 class="repo-detail-name">' + escapeHtml(repo.name) + '</h2>';
    html += '<div class="repo-detail-actions">';
    if (githubUrl) {
      html += '<a href="' + escapeAttr(githubUrl) + '" class="btn btn-primary" target="_blank" rel="noopener">';
      html += '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>';
      html += ' View on GitHub</a>';
    }
    html += '</div></div>';

    // Description
    if (repo.description) {
      html += '<p class="repo-detail-description">' + escapeHtml(repo.description) + '</p>';
    }

    // Stats bar
    html += '<div class="repo-detail-stats">';
    if (repo.language) {
      html += '<div class="stat-chip">';
      html += '<span class="language-dot" style="background:' + escapeAttr(langColor) + '"></span>';
      html += escapeHtml(repo.language);
      html += '</div>';
    }
    html += '<div class="stat-chip">&#9733; ' + escapeHtml(String(repo.stars || 0)) + ' stars</div>';
    if (freshness) {
      html += '<div class="stat-chip ' + escapeAttr(freshness.className) + '">' + escapeHtml(freshness.label) + '</div>';
    }
    if (repo.updated_at) {
      html += '<div class="stat-chip">Updated ' + escapeHtml(formatDate(repo.updated_at)) + '</div>';
    }
    if (cluster) {
      html += '<div class="stat-chip"><a href="#/cluster/' + escapeAttr(encodeURIComponent(cluster.name)) + '">' + escapeHtml(cluster.name) + '</a></div>';
    }
    html += '</div>';

    // Topics — clickable, search by topic
    const topics = repo.topics || [];
    if (topics.length > 0) {
      html += '<div class="repo-detail-topics">';
      for (const t of topics) {
        html += '<a href="#/search?q=' + escapeAttr(encodeURIComponent(t)) + '" class="topic-tag">' + escapeHtml(t) + '</a>';
      }
      html += '</div>';
    }

    // Quick start / clone section
    if (githubUrl) {
      const cloneUrl = escapeHtml(githubUrl + '.git');
      const cloneAttr = escapeAttr(githubUrl + '.git');
      html += '<div class="repo-detail-section">';
      html += '<h3>Quick Start</h3>';
      html += '<div class="clone-box">';
      html += '<code>git clone ' + cloneUrl + '</code>';
      html += '<button class="btn-copy" data-copy="' + cloneAttr + '">Copy</button>';
      html += '</div></div>';
    }

    // README section — assembled from search-index chunks or readme_excerpt
    const readmeContent = _getRepoReadme(repo);
    if (readmeContent) {
      html += '<div class="repo-detail-section">';
      html += '<h3>README</h3>';
      html += '<div class="readme-content">' + escapeHtml(readmeContent) + '</div>';
      if (githubUrl) {
        html += '<a href="' + escapeAttr(githubUrl + '#readme') + '" class="readme-more" target="_blank" rel="noopener">Read full README on GitHub &rarr;</a>';
      }
      html += '</div>';
    }

    html += '</div>'; // repo-detail

    // Related repos (similarity-based or cluster-based)
    const related = findRelatedRepos(repo, 6);
    if (related.length > 0) {
      const relLabel = related._source === "similarity" ? "Semantically similar" : "from same cluster";
      html += '<div class="related-repos-section">';
      html += '<div class="section-header"><h3>Related Repositories</h3>';
      html += '<span class="count">' + escapeHtml(relLabel) + '</span></div>';
      html += renderRepoCards(related);
      html += '</div>';
    }

    container.innerHTML = html;

    // Wire up copy button (event listener, not inline handler)
    const copyBtn = container.querySelector('.btn-copy');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const text = copyBtn.getAttribute('data-copy');
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = 'Copied!';
          setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1500);
        });
      });
    }
  }

  /**
   * Get README content for a repo from search index chunks or readme_excerpt.
   */
  function _getRepoReadme(repo) {
    // Try search index chunks (richer, from search-index.json)
    if (SearchEngine._chunkRawMap && SearchEngine._chunkRawMap[repo.name]) {
      const chunks = SearchEngine._chunkRawMap[repo.name];
      const readmeChunks = chunks.filter((c) =>
        c.source === "README" || c.source === "README.md"
      );
      if (readmeChunks.length > 0) {
        return readmeChunks.map((c) => c.text).join("\n\n");
      }
      // If no README-specific chunks, use all chunks
      if (chunks.length > 0) {
        return chunks.map((c) => c.text).join("\n\n");
      }
    }
    return repo.readme_excerpt || null;
  }

  /**
   * Render clusters listing page.
   */
  function renderClustersPage(container) {
    // Stats summary
    const langCounts = {};
    let mostActiveCluster = { name: "N/A", count: 0 };
    for (const r of repos) {
      if (r.language) langCounts[r.language] = (langCounts[r.language] || 0) + 1;
    }
    for (const c of clusters) {
      const count = (c.repos || []).length;
      if (count > mostActiveCluster.count) {
        mostActiveCluster = { name: c.name, count: count };
      }
    }
    const sortedLangs = Object.entries(langCounts).sort((a, b) => b[1] - a[1]);
    const topLang = sortedLangs.length > 0 ? sortedLangs[0][0] : "N/A";

    let html = '<div class="clusters-stats-summary">';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(String(repos.length)) + '</span><span class="stat-label">Total Repos</span></div>';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(mostActiveCluster.name) + '</span><span class="stat-label">Largest Cluster</span></div>';
    html += '<div class="stat-item"><span class="stat-number">' + escapeHtml(topLang) + '</span><span class="stat-label">Top Language</span></div>';
    html += '</div>';

    // Technology Distribution — top 10 topics as horizontal bar chart
    const topicCounts = {};
    for (const r of repos) {
      for (const t of (r.topics || [])) {
        topicCounts[t] = (topicCounts[t] || 0) + 1;
      }
    }
    const topTopics = Object.entries(topicCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15);

    if (topTopics.length > 0) {
      const maxTopicCount = topTopics[0][1];
      const barColors = [
        'var(--accent)', 'var(--green)', 'var(--purple)',
        'var(--yellow)', 'var(--orange)', '#f778ba'
      ];
      html += '<div class="section-header"><h3>Technology Distribution</h3>';
      html += '<span class="count">' + escapeHtml(String(topTopics.length)) + ' topics</span></div>';
      html += '<div class="topic-distribution">';
      for (let i = 0; i < topTopics.length; i++) {
        const [topic, count] = topTopics[i];
        const pct = Math.round((count / maxTopicCount) * 100);
        const color = barColors[i % barColors.length];
        html += '<div class="topic-bar-row">';
        html += '<span class="topic-bar-label">' + escapeHtml(topic) + '</span>';
        html += '<div class="topic-bar-track"><div class="topic-bar-fill" style="width:' + escapeAttr(String(pct)) + '%;background:' + escapeAttr(color) + '"></div></div>';
        html += '<span class="topic-bar-count">' + escapeHtml(String(count)) + '</span>';
        html += '</div>';
      }
      html += '</div>';
    }

    html += '<div class="section-header">';
    html += "<h3>All Clusters</h3>";
    html += '<span class="count">' + escapeHtml(String(clusters.length)) + " clusters</span>";
    html += "</div>";

    // D3 circle-packing visualization container
    html += '<div id="d3-viz-container" class="d3-viz-wrapper"></div>';

    if (clusters.length > 0) {
      html += '<div class="cluster-grid">';
      for (const cluster of clusters) {
        const repoPreview = (cluster.repos || []).slice(0, 3).join(", ");
        const repoCount = (cluster.repos || []).length;
        html += '<div class="cluster-card" data-cluster="' + escapeAttr(cluster.name) + '">';
        html += "<h4>" + escapeHtml(cluster.name) + "</h4>";
        html += '<span class="repo-count">' + escapeHtml(String(repoCount)) + " repo" + (repoCount !== 1 ? "s" : "") + "</span>";
        if (cluster.description) {
          html += '<div class="cluster-description">' + escapeHtml(cluster.description) + "</div>";
        }
        if (repoPreview) {
          html += '<div class="repo-list-preview">' + escapeHtml(repoPreview) + "</div>";
        }
        html += "</div>";
      }
      html += "</div>";
    } else {
      html += '<div class="empty-state"><p>No clusters available</p></div>';
    }

    // Safe: all dynamic values escaped via escapeHtml/escapeAttr
    container.innerHTML = html;
    bindClusterClicks();

    // Render D3 circle-packing after DOM is ready
    if (typeof D3Viz !== "undefined") {
      D3Viz.render(container, clusters, repos);
    }
  }

  /**
   * Render the Request Access page with form fields.
   * Note: This form contains only static HTML — no user-controlled values
   * are interpolated, so innerHTML is safe here.
   */
  function renderAccessRequest(container) {
    container.textContent = "";

    const page = document.createElement("div");
    page.className = "access-request-page";

    const h2 = document.createElement("h2");
    h2.textContent = "Request Access";
    page.appendChild(h2);

    const tierInfo = document.createElement("p");
    tierInfo.className = "access-tier-info";
    tierInfo.textContent = "Public tier \u2014 browse clusters and search descriptions. Gated access provides: Full code search, file tree browsing, and detailed repository analysis. Fill out the form below to request access.";
    page.appendChild(tierInfo);

    // Show sign-in prompt for unauthenticated users
    if (!Auth.isAuthenticated() && Auth.isOAuthEnabled()) {
      const signInSection = document.createElement("div");
      signInSection.style.cssText = "margin:1.5rem 0;padding:1rem;background:var(--card-bg, #161b22);border:1px solid var(--border, #30363d);border-radius:8px;text-align:center";

      const signInMsg = document.createElement("p");
      signInMsg.textContent = "Sign in with Google to auto-fill your details and request access.";
      signInMsg.style.cssText = "color:#8b949e;margin-bottom:1rem";
      signInSection.appendChild(signInMsg);

      const signInContainer = document.createElement("div");
      signInContainer.style.cssText = "display:flex;justify-content:center";
      signInSection.appendChild(signInContainer);

      page.appendChild(signInSection);
      Auth.renderSignInButton(signInContainer);
    }

    const form = document.createElement("form");
    form.className = "access-form";
    form.id = "access-form";

    // Name field
    const nameGroup = document.createElement("div");
    nameGroup.className = "form-group";
    const nameLabel = document.createElement("label");
    nameLabel.setAttribute("for", "access-name");
    nameLabel.textContent = "Name";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.id = "access-name";
    nameInput.name = "name";
    nameInput.placeholder = "Your name";
    nameInput.required = true;
    nameGroup.appendChild(nameLabel);
    nameGroup.appendChild(nameInput);
    form.appendChild(nameGroup);

    // Email field
    const emailGroup = document.createElement("div");
    emailGroup.className = "form-group";
    const emailLabel = document.createElement("label");
    emailLabel.setAttribute("for", "access-email");
    emailLabel.textContent = "Email";
    const emailInput = document.createElement("input");
    emailInput.type = "email";
    emailInput.id = "access-email";
    emailInput.name = "email";
    emailInput.placeholder = "you@example.com";
    emailInput.required = true;
    emailGroup.appendChild(emailLabel);
    emailGroup.appendChild(emailInput);
    form.appendChild(emailGroup);

    // Auto-fill from Google profile if authenticated
    const user = Auth.getUser();
    if (user) {
      if (user.name) nameInput.value = user.name;
      if (user.email) emailInput.value = user.email;
    }

    // Reason field
    const reasonGroup = document.createElement("div");
    reasonGroup.className = "form-group";
    const reasonLabel = document.createElement("label");
    reasonLabel.setAttribute("for", "access-reason");
    reasonLabel.textContent = "Reason for access";
    const reasonTextarea = document.createElement("textarea");
    reasonTextarea.id = "access-reason";
    reasonTextarea.name = "reason";
    reasonTextarea.placeholder = "Why would you like full access?";
    reasonTextarea.rows = 4;
    reasonTextarea.required = true;
    reasonGroup.appendChild(reasonLabel);
    reasonGroup.appendChild(reasonTextarea);
    form.appendChild(reasonGroup);

    // Submit button
    const submitBtn = document.createElement("button");
    submitBtn.type = "submit";
    submitBtn.className = "submit-btn";
    submitBtn.id = "access-submit";
    submitBtn.textContent = "Submit Request";
    form.appendChild(submitBtn);

    // Message area
    const msgDiv = document.createElement("div");
    msgDiv.className = "form-message";
    msgDiv.id = "form-message";
    form.appendChild(msgDiv);

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      msgDiv.textContent = "Coming soon \u2014 access request API is under development. Your interest has been noted!";
      msgDiv.className = "form-message visible";
    });

    page.appendChild(form);
    container.appendChild(page);
  }

  /**
   * Render a list of repo cards as HTML.
   * All dynamic repo data is escaped before insertion.
   */
  /**
   * Render a list of repo cards as HTML.
   * All dynamic repo data is escaped before insertion.
   * @param {Array} repoList - repos to render
   * @param {string} [query] - optional query for term highlighting
   */
  function renderRepoCards(repoList, query) {
    let html = '<div class="results-list">';

    for (const repo of repoList) {
      const langColor = LANG_COLORS[repo.language] || "#8b949e";

      html += '<div class="repo-card">';
      html += '<div class="repo-card-header">';

      html += '<a href="#/repo/' + escapeAttr(encodeURIComponent(repo.name)) + '" class="repo-name">' + escapeHtml(repo.name) + "</a>";

      // Relevance bar instead of raw score number
      if (repo._score !== undefined && repo._maxScore) {
        const pct = Math.round((repo._score / repo._maxScore) * 100);
        html += '<div class="relevance-bar" title="Relevance: ' + escapeAttr(repo._score.toFixed(1)) + '">';
        html += '<div class="relevance-fill" style="width:' + escapeAttr(String(pct)) + '%"></div>';
        html += "</div>";
      }
      html += "</div>";

      if (repo.description) {
        // Safe: highlightTerms escapes text first, then adds <mark> tags
        html += '<div class="description">' + highlightTerms(repo.description, query) + "</div>";
      }

      // Snippet from README chunks (if search-index loaded)
      if (query && typeof SearchEngine.getSnippet === "function") {
        const snippet = SearchEngine.getSnippet(repo.name, query);
        if (snippet) {
          html += '<div class="search-snippet">' + highlightTerms(snippet, query) + '</div>';
        }
      }

      // Meta row
      html += '<div class="repo-meta">';

      if (repo.language) {
        html += '<span class="language-badge">';
        html += '<span class="language-dot" style="background:' + escapeAttr(langColor) + '"></span>';
        html += escapeHtml(repo.language);
        html += "</span>";
      }

      // Freshness badge
      const badge = getFreshnessBadge(repo.updated_at);
      if (badge) {
        html += '<span class="' + escapeAttr(badge.className) + '">' + escapeHtml(badge.label) + '</span>';
      }

      if (repo.stars !== undefined && repo.stars !== null) {
        html += '<span class="stars-badge">&#9733; ' + escapeHtml(String(repo.stars)) + "</span>";
      }

      if (repo.updated_at) {
        html += "<span>Updated " + escapeHtml(formatDate(repo.updated_at)) + "</span>";
      }

      html += "</div>"; // repo-meta

      // Topics
      const topics = repo.topics || [];
      if (topics.length > 0) {
        html += '<div class="topic-tags">';
        for (const t of topics.slice(0, 8)) {
          html += '<span class="topic-tag">' + escapeHtml(t) + "</span>";
        }
        html += "</div>";
      }

      html += "</div>"; // repo-card
    }

    html += "</div>";
    return html;
  }

  /**
   * Render the filter sidebar HTML.
   */
  function renderFilterSidebar() {
    let html = '<div class="filter-sidebar" id="filter-sidebar">';

    // Language filters
    if (facets.languages.length > 0) {
      html += '<div class="filter-group">';
      html += "<h4>Language</h4>";
      for (const lang of facets.languages.slice(0, 10)) {
        const checked = currentFilters.languages.includes(lang.name) ? " checked" : "";
        html += "<label>";
        html += '<input type="checkbox" data-filter="language" value="' + escapeAttr(lang.name) + '"' + checked + ">";
        html += " " + escapeHtml(lang.name) + " (" + escapeHtml(String(lang.count)) + ")";
        html += "</label>";
      }
      html += "</div>";
    }

    // Topic filters
    if (facets.topics.length > 0) {
      html += '<div class="filter-group filter-group-topics">';
      html += "<h4>Topics</h4>";
      html += '<div class="filter-topic-list">';
      for (const topic of facets.topics.slice(0, 15)) {
        const checked = currentFilters.topics.includes(topic.name) ? " checked" : "";
        html += "<label>";
        html += '<input type="checkbox" data-filter="topic" value="' + escapeAttr(topic.name) + '"' + checked + ">";
        html += " " + escapeHtml(topic.name) + ' <span class="filter-count">(' + escapeHtml(String(topic.count)) + ")</span>";
        html += "</label>";
      }
      html += "</div>";
      html += "</div>";
    }

    // Stars range filter
    if (facets.maxStars > 0) {
      html += '<div class="filter-group">';
      html += "<h4>Min Stars</h4>";
      html += '<input type="range" id="stars-filter" min="0" max="' + escapeAttr(String(facets.maxStars)) + '" value="' + escapeAttr(String(currentFilters.minStars)) + '">';
      html += '<div class="range-labels">';
      html += "<span>0</span>";
      html += '<span id="stars-value">' + escapeHtml(String(currentFilters.minStars)) + "</span>";
      html += "<span>" + escapeHtml(String(facets.maxStars)) + "</span>";
      html += "</div>";
      html += "</div>";
    }

    html += "</div>"; // filter-sidebar
    return html;
  }

  /**
   * Bind event listeners for filter checkboxes and range inputs.
   */
  function bindFilterEvents() {
    // Filter toggle (mobile)
    const toggle = document.getElementById("filter-toggle");
    const sidebar = document.getElementById("filter-sidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", () => {
        filtersOpen = !filtersOpen;
        sidebar.classList.toggle("open", filtersOpen);
        toggle.textContent = filtersOpen ? "Hide Filters" : "Filters";
      });
    }

    // Language checkboxes
    document.querySelectorAll('input[data-filter="language"]').forEach((cb) => {
      cb.addEventListener("change", () => {
        currentFilters.languages = getCheckedValues("language");
        route();
      });
    });

    // Topic checkboxes
    document.querySelectorAll('input[data-filter="topic"]').forEach((cb) => {
      cb.addEventListener("change", () => {
        currentFilters.topics = getCheckedValues("topic");
        route();
      });
    });

    // Sort select
    const sortSelect = document.getElementById("sort-select");
    if (sortSelect) {
      sortSelect.addEventListener("change", () => {
        currentSortMode = sortSelect.value;
        route();
      });
    }

    // Stars range
    const starsRange = document.getElementById("stars-filter");
    const starsValue = document.getElementById("stars-value");
    if (starsRange) {
      starsRange.addEventListener("input", () => {
        currentFilters.minStars = parseInt(starsRange.value, 10);
        if (starsValue) starsValue.textContent = starsRange.value;
      });
      starsRange.addEventListener("change", () => {
        route();
      });
    }
  }

  function getCheckedValues(filterType) {
    const checked = [];
    document.querySelectorAll('input[data-filter="' + filterType + '"]:checked').forEach((cb) => {
      checked.push(cb.value);
    });
    return checked;
  }

  /**
   * Bind click handlers on cluster cards.
   */
  function bindClusterClicks() {
    document.querySelectorAll(".cluster-card").forEach((card) => {
      card.addEventListener("click", () => {
        const name = card.getAttribute("data-cluster");
        window.location.hash = "#/cluster/" + encodeURIComponent(name);
      });
    });
  }

  /**
   * Autocomplete: filter suggestions and render dropdown.
   * Uses safe DOM methods (createElement, textContent) — no innerHTML with user data.
   */
  function renderAutocomplete(inputElement) {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (!dropdown) return;

    let activeIndex = -1;

    function updateDropdown() {
      const text = inputElement.value.trim().toLowerCase();
      dropdown.textContent = "";
      activeIndex = -1;

      if (!text || !suggestions) {
        dropdown.classList.remove("visible");
        return;
      }

      const matches = [];
      const seen = new Set();

      // Collect matches from repos, topics, and queries arrays
      const sources = [
        { items: suggestions.repos || [], type: "repo" },
        { items: suggestions.topics || [], type: "topic" },
        { items: suggestions.queries || [], type: "query" },
      ];

      for (const source of sources) {
        for (const item of source.items) {
          const val = typeof item === "string" ? item : (item.name || item.query || "");
          if (val.toLowerCase().startsWith(text) && !seen.has(val.toLowerCase())) {
            seen.add(val.toLowerCase());
            matches.push({ value: val, type: source.type });
          }
          if (matches.length >= 8) break;
        }
        if (matches.length >= 8) break;
      }

      if (matches.length === 0) {
        dropdown.classList.remove("visible");
        return;
      }

      for (let i = 0; i < matches.length; i++) {
        const item = document.createElement("div");
        item.className = "autocomplete-item";
        item.setAttribute("role", "option");

        const label = document.createElement("span");
        label.textContent = matches[i].value;
        item.appendChild(label);

        const badge = document.createElement("span");
        badge.className = "autocomplete-type";
        badge.textContent = matches[i].type;
        item.appendChild(badge);

        item.addEventListener("mousedown", (e) => {
          e.preventDefault(); // Prevent blur before click fires
          inputElement.value = matches[i].value;
          dropdown.classList.remove("visible");
          clearTimeout(debounceTimer);
          window.location.hash = "#/search?q=" + encodeURIComponent(matches[i].value);
        });

        dropdown.appendChild(item);
      }

      dropdown.classList.add("visible");
    }

    function setActive(items) {
      for (let i = 0; i < items.length; i++) {
        items[i].classList.toggle("active", i === activeIndex);
      }
    }

    inputElement.addEventListener("input", updateDropdown);

    inputElement.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll(".autocomplete-item");
      if (!dropdown.classList.contains("visible") || items.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        setActive(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
        setActive(items);
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        items[activeIndex].dispatchEvent(new MouseEvent("mousedown"));
      } else if (e.key === "Escape") {
        dropdown.classList.remove("visible");
        activeIndex = -1;
      }
    });

    inputElement.addEventListener("blur", () => {
      // Delay to allow mousedown on dropdown items to fire
      setTimeout(() => dropdown.classList.remove("visible"), 150);
    });

    inputElement.addEventListener("focus", () => {
      if (inputElement.value.trim()) updateDropdown();
    });
  }

  /**
   * Handle search input with debounce.
   */
  function handleSearchInput(value) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (value.trim()) {
        window.location.hash = "#/search?q=" + encodeURIComponent(value.trim());
      } else {
        window.location.hash = "#/";
      }
    }, 300);
  }

  /**
   * Compute freshness tier from an ISO date string.
   * Returns { label, className } for badge rendering.
   */
  function getFreshnessBadge(dateStr) {
    if (!dateStr) return null;
    try {
      const updated = new Date(dateStr);
      const now = new Date();
      const diffMs = now - updated;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) return { label: "Updated today", className: "freshness-badge freshness-today" };
      if (diffDays <= 7) return { label: "This week", className: "freshness-badge freshness-week" };
      if (diffDays <= 30) return { label: "This month", className: "freshness-badge freshness-month" };
      return { label: "Stale (>30 days)", className: "freshness-badge freshness-stale" };
    } catch {
      return null;
    }
  }

  /**
   * Format an ISO date string to a readable format.
   */
  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  }

  /**
   * Inject styles for activity timeline, cluster stats, and sort controls.
   * Added via JS because web/css/style.css is owned by another agent.
   */
  function injectActivityStyles() {
    if (document.getElementById("activity-stats-styles")) return;
    const style = document.createElement("style");
    style.id = "activity-stats-styles";
    style.textContent = `
      .recent-activity { display:flex; flex-direction:column; gap:6px; margin-bottom:2rem; }
      .recent-activity-item { display:flex; align-items:center; gap:12px; padding:8px 12px; background:var(--card-bg, #161b22); border:1px solid var(--border, #30363d); border-radius:6px; }
      .recent-activity-name { color:var(--link, #58a6ff); text-decoration:none; font-weight:500; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .recent-activity-name:hover { text-decoration:underline; }
      .recent-activity-date { color:var(--muted, #8b949e); font-size:0.85rem; white-space:nowrap; }
      .clusters-stats-summary { display:flex; gap:1.5rem; justify-content:center; flex-wrap:wrap; margin-bottom:2rem; padding:1rem; background:var(--card-bg, #161b22); border:1px solid var(--border, #30363d); border-radius:8px; }
      .clusters-stats-summary .stat-item { text-align:center; }
      .clusters-stats-summary .stat-number { display:block; font-size:1.1rem; font-weight:600; color:var(--text, #e6edf3); }
      .clusters-stats-summary .stat-label { font-size:0.8rem; color:var(--muted, #8b949e); }
      /* topic-distribution styles moved to style.css */
      .sort-controls { display:flex; align-items:center; gap:8px; margin-bottom:0.75rem; }
      .sort-controls label { font-size:0.85rem; color:var(--muted, #8b949e); }
      .sort-select { background:var(--card-bg, #161b22); color:var(--text, #e6edf3); border:1px solid var(--border, #30363d); border-radius:6px; padding:4px 8px; font-size:0.85rem; cursor:pointer; }
    `;
    document.head.appendChild(style);
  }

  /**
   * Initialize the app.
   */
  function init() {
    injectActivityStyles();
    _updateHeaderUserInfo();
    window.addEventListener("hashchange", route);

    const searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        handleSearchInput(e.target.value);
      });

      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          // Only handle Enter for direct search when autocomplete isn't handling it
          const dropdown = document.getElementById("autocomplete-dropdown");
          const hasActiveItem = dropdown && dropdown.querySelector(".autocomplete-item.active");
          if (!hasActiveItem) {
            clearTimeout(debounceTimer);
            const val = searchInput.value.trim();
            if (val) {
              if (dropdown) dropdown.classList.remove("visible");
              window.location.hash = "#/search?q=" + encodeURIComponent(val);
            }
          }
        }
      });

      renderAutocomplete(searchInput);
    }

    loadData();
  }

  return { init };
})();
