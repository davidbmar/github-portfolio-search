/**
 * Main application for GitHub Portfolio Search.
 * Handles data loading, hash routing, rendering, and user interaction.
 *
 * Security: All dynamic content is escaped via escapeHtml() / escapeAttr()
 * before DOM insertion. escapeHtml uses createTextNode which is XSS-safe.
 */

const App = (() => {
  // State
  let repos = [];
  let clusters = [];
  let currentFilters = { languages: [], topics: [], minStars: 0 };
  let facets = { languages: [], topics: [], maxStars: 0 };
  let filtersOpen = false;
  let debounceTimer = null;

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
    } catch (err) {
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

    // Footer
    html += '<footer class="site-footer">';
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
    for (const cluster of clusters) {
      if ((cluster.repos || []).includes(repo.name)) {
        return (cluster.repos || [])
          .filter((n) => n !== repo.name)
          .slice(0, maxCount || 3)
          .map((name) => repos.find((r) => r.name === name))
          .filter(Boolean);
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
    const results = SearchEngine.search(filtered, query);
    const maxScore = results.length > 0 ? results[0].score : 1;

    // Safe: all dynamic values below pass through escapeHtml/escapeAttr
    let html = '<div class="content-layout">';

    // Filter sidebar
    html += renderFilterSidebar();

    // Results area
    html += '<div class="results-area">';
    html += '<button class="filter-toggle" id="filter-toggle">Filters</button>';

    html += '<div class="section-header">';
    if (query) {
      html += '<h3>Results for &ldquo;' + escapeHtml(query) + '&rdquo;</h3>';
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
        html += '<div class="related-repos-section">';
        html += '<div class="section-header"><h3>Related Repositories</h3>';
        html += '<span class="count">from same cluster</span></div>';
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
   * Render clusters listing page.
   */
  function renderClustersPage(container) {
    let html = '<div class="section-header">';
    html += "<h3>All Clusters</h3>";
    html += '<span class="count">' + escapeHtml(String(clusters.length)) + " clusters</span>";
    html += "</div>";

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
    tierInfo.textContent = "Public tier \u2014 browse clusters and search descriptions. Request full access for code snippets.";
    page.appendChild(tierInfo);

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

      if (repo.url) {
        html += '<a href="' + escapeAttr(repo.url) + '" class="repo-name" target="_blank" rel="noopener">' + escapeHtml(repo.name) + "</a>";
      } else {
        html += '<span class="repo-name">' + escapeHtml(repo.name) + "</span>";
      }

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

      // Meta row
      html += '<div class="repo-meta">';

      if (repo.language) {
        html += '<span class="language-badge">';
        html += '<span class="language-dot" style="background:' + escapeAttr(langColor) + '"></span>';
        html += escapeHtml(repo.language);
        html += "</span>";
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
      html += '<div class="filter-group">';
      html += "<h4>Topics</h4>";
      for (const topic of facets.topics.slice(0, 10)) {
        const checked = currentFilters.topics.includes(topic.name) ? " checked" : "";
        html += "<label>";
        html += '<input type="checkbox" data-filter="topic" value="' + escapeAttr(topic.name) + '"' + checked + ">";
        html += " " + escapeHtml(topic.name) + " (" + escapeHtml(String(topic.count)) + ")";
        html += "</label>";
      }
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
   * Initialize the app.
   */
  function init() {
    window.addEventListener("hashchange", route);

    const searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        handleSearchInput(e.target.value);
      });

      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          clearTimeout(debounceTimer);
          const val = searchInput.value.trim();
          if (val) {
            window.location.hash = "#/search?q=" + encodeURIComponent(val);
          }
        }
      });
    }

    loadData();
  }

  return { init };
})();

// Start the app when DOM is ready
document.addEventListener("DOMContentLoaded", App.init);
