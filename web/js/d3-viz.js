/**
 * D3.js Circle-Packing Visualization for GitHub Portfolio.
 *
 * Renders an interactive circle-packing layout where outer circles represent
 * capability clusters and inner circles represent repositories sized by stars.
 *
 * Depends on: D3 v7 (loaded via CDN), clusters.json, repos.json
 */

// Inject D3 visualization styles (avoids modifying style.css owned by agentC)
(function injectD3Styles() {
  var style = document.createElement("style");
  style.textContent = [
    ".d3-viz-wrapper {",
    "  position: relative;",
    "  width: 100%;",
    "  max-width: 700px;",
    "  margin: 16px auto 24px;",
    "  background: var(--bg-secondary, #161b22);",
    "  border: 1px solid var(--border, #30363d);",
    "  border-radius: var(--radius, 8px);",
    "  padding: 16px;",
    "  overflow: hidden;",
    "}",
    ".d3-circle-pack { display: block; }",
    ".d3-tooltip {",
    "  position: absolute;",
    "  pointer-events: none;",
    "  background: var(--bg-tertiary, #21262d);",
    "  color: var(--text-primary, #e6edf3);",
    "  border: 1px solid var(--border, #30363d);",
    "  border-radius: 6px;",
    "  padding: 8px 12px;",
    "  font-size: 0.8rem;",
    "  line-height: 1.4;",
    "  max-width: 280px;",
    "  z-index: 10;",
    "  transition: opacity 0.15s;",
    "}",
    ".d3-reset-btn {",
    "  position: absolute;",
    "  top: 8px;",
    "  right: 8px;",
    "  z-index: 5;",
    "  background: var(--bg-tertiary, #21262d);",
    "  color: var(--text-secondary, #8b949e);",
    "  border: 1px solid var(--border, #30363d);",
    "  border-radius: 4px;",
    "  padding: 4px 10px;",
    "  font-size: 0.75rem;",
    "  cursor: pointer;",
    "}",
    ".d3-reset-btn:hover {",
    "  color: var(--text-primary, #e6edf3);",
    "  border-color: var(--accent, #58a6ff);",
    "}",
    ".node-label {",
    "  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;",
    "  font-weight: 600;",
    "}",
    "@media (max-width: 600px) {",
    "  .d3-viz-wrapper { padding: 8px; }",
    "}",
  ].join("\n");
  document.head.appendChild(style);
})();

const D3Viz = (() => {
  // Cluster color palette matching the CSS theme
  const CLUSTER_COLORS = [
    "#58a6ff", // accent blue
    "#3fb950", // green
    "#bc8cff", // purple
    "#d29922", // yellow
    "#db6d28", // orange
    "#f778ba", // pink
  ];

  let svg = null;
  let currentFocus = null;
  let view = null;

  /**
   * Build the hierarchical data structure D3 pack layout expects.
   * Root -> clusters -> repos
   */
  function buildHierarchy(clusters, repos) {
    const repoMap = {};
    for (const r of repos) {
      repoMap[r.name] = r;
    }

    const children = clusters.map((cluster, i) => ({
      name: cluster.name,
      clusterIndex: i,
      children: (cluster.repos || []).map((repoName) => {
        const repo = repoMap[repoName] || {};
        return {
          name: repoName,
          description: repo.description || "",
          language: repo.language || "",
          stars: repo.stars || 0,
          value: Math.max(repo.stars || 0, 1), // min size for 0-star repos
          clusterIndex: i,
          isRepo: true,
        };
      }),
    }));

    return { name: "root", children };
  }

  /**
   * Build tooltip content using safe DOM methods (no innerHTML).
   */
  function buildTooltipContent(tooltipEl, d) {
    // Clear previous content safely
    while (tooltipEl.firstChild) {
      tooltipEl.removeChild(tooltipEl.firstChild);
    }

    var strong = document.createElement("strong");
    strong.textContent = d.data.name;
    tooltipEl.appendChild(strong);

    if (d.data.isRepo) {
      if (d.data.description) {
        tooltipEl.appendChild(document.createElement("br"));
        tooltipEl.appendChild(document.createTextNode(d.data.description));
      }
      if (d.data.language) {
        tooltipEl.appendChild(document.createElement("br"));
        var em = document.createElement("em");
        em.textContent = d.data.language;
        tooltipEl.appendChild(em);
      }
      tooltipEl.appendChild(document.createElement("br"));
      tooltipEl.appendChild(document.createTextNode("\u2605 " + d.data.stars));
    } else {
      tooltipEl.appendChild(document.createElement("br"));
      var count = d.children ? d.children.length : 0;
      tooltipEl.appendChild(document.createTextNode(count + " repos"));
    }
  }

  /**
   * Render the circle-packing visualization into the given container element.
   */
  function render(container, clusters, repos) {
    if (typeof d3 === "undefined") return;
    if (!clusters.length) return;

    var wrapper = container.querySelector("#d3-viz-container");
    if (!wrapper) return;

    // Clear previous render
    while (wrapper.firstChild) {
      if (wrapper.firstChild.classList && wrapper.firstChild.classList.contains("d3-reset-btn")) {
        break;
      }
      wrapper.removeChild(wrapper.firstChild);
    }
    // Re-clear fully, then re-add reset button
    wrapper.textContent = "";

    // Add reset button
    var resetBtn = document.createElement("button");
    resetBtn.className = "d3-reset-btn";
    resetBtn.type = "button";
    resetBtn.textContent = "Reset Zoom";
    wrapper.appendChild(resetBtn);

    var width = wrapper.clientWidth || 600;
    var height = Math.min(width, 600);

    var root = d3
      .hierarchy(buildHierarchy(clusters, repos))
      .sum(function (d) { return d.value || 0; })
      .sort(function (a, b) { return (b.value || 0) - (a.value || 0); });

    var pack = d3.pack().size([width, height]).padding(3);

    pack(root);

    currentFocus = root;

    svg = d3
      .select(wrapper)
      .append("svg")
      .attr("viewBox", "0 0 " + width + " " + height)
      .attr("width", "100%")
      .attr("height", height)
      .attr("class", "d3-circle-pack")
      .style("cursor", "pointer")
      .on("click", function () { zoomTo(root, width, height); });

    // Tooltip element (built with DOM, not innerHTML)
    var tooltipEl = document.createElement("div");
    tooltipEl.className = "d3-tooltip";
    tooltipEl.style.opacity = "0";
    wrapper.appendChild(tooltipEl);
    var tooltip = d3.select(tooltipEl);

    // Draw circles
    var node = svg
      .selectAll("circle")
      .data(root.descendants())
      .join("circle")
      .attr("class", function (d) {
        if (d.depth === 0) return "node node-root";
        if (d.depth === 1) return "node node-cluster";
        return "node node-repo";
      })
      .attr("fill", function (d) {
        if (d.depth === 0) return "transparent";
        if (d.depth === 1) {
          var idx = d.data.clusterIndex % CLUSTER_COLORS.length;
          return CLUSTER_COLORS[idx] + "22"; // transparent fill
        }
        var idx2 = d.data.clusterIndex % CLUSTER_COLORS.length;
        return CLUSTER_COLORS[idx2];
      })
      .attr("stroke", function (d) {
        if (d.depth === 0) return "none";
        if (d.depth === 1) {
          var idx = d.data.clusterIndex % CLUSTER_COLORS.length;
          return CLUSTER_COLORS[idx];
        }
        return "none";
      })
      .attr("stroke-width", function (d) { return d.depth === 1 ? 1.5 : 0; })
      .attr("opacity", function (d) {
        if (d.depth === 0) return 0;
        if (d.depth === 2) return 0.85;
        return 1;
      })
      .on("mouseover", function (event, d) {
        if (d.depth === 0) return;
        d3.select(this).attr("opacity", 1).attr("stroke", "#fff").attr("stroke-width", 2);
        buildTooltipContent(tooltipEl, d);
        tooltip.style("opacity", "1");
        positionTooltip(event, tooltip, wrapper);
      })
      .on("mousemove", function (event) {
        positionTooltip(event, tooltip, wrapper);
      })
      .on("mouseout", function (event, d) {
        if (d.depth === 0) return;
        d3.select(this)
          .attr("opacity", d.depth === 2 ? 0.85 : 1)
          .attr("stroke", d.depth === 1 ? CLUSTER_COLORS[d.data.clusterIndex % CLUSTER_COLORS.length] : "none")
          .attr("stroke-width", d.depth === 1 ? 1.5 : 0);
        tooltip.style("opacity", "0");
      })
      .on("click", function (event, d) {
        event.stopPropagation();
        if (d.data.isRepo) {
          window.location.hash = "#/repo/" + encodeURIComponent(d.data.name);
          return;
        }
        if (d.depth === 1) {
          if (currentFocus === d) {
            zoomTo(root, width, height);
          } else {
            zoomTo(d, width, height);
          }
        }
      });

    // Labels for clusters
    var labels = svg
      .selectAll("text")
      .data(root.descendants().filter(function (d) { return d.depth === 1; }))
      .join("text")
      .attr("class", "node-label")
      .attr("text-anchor", "middle")
      .attr("dy", "0.3em")
      .attr("pointer-events", "none")
      .attr("fill", "#e6edf3")
      .attr("font-size", function (d) { return Math.max(d.r / 5, 8) + "px"; })
      .text(function (d) { return truncateLabel(d.data.name, d.r); });

    // Initial positions
    view = [root.x, root.y, root.r * 2];
    zoomToView(node, labels, view, width, height);

    // Reset button click
    resetBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      zoomTo(root, width, height);
    });
  }

  function zoomTo(target, width, height) {
    currentFocus = target;
    var targetView = [target.x, target.y, target.r * 2];

    var nodes = svg.selectAll("circle");
    var labels = svg.selectAll("text");

    svg
      .transition()
      .duration(500)
      .tween("zoom", function () {
        var i = d3.interpolateZoom(view, targetView);
        return function (t) {
          view = i(t);
          zoomToView(nodes, labels, view, width, height);
        };
      });
  }

  function zoomToView(node, labels, v, width, height) {
    var k = width / v[2];
    node
      .attr("cx", function (d) { return (d.x - v[0]) * k + width / 2; })
      .attr("cy", function (d) { return (d.y - v[1]) * k + height / 2; })
      .attr("r", function (d) { return d.r * k; });

    labels
      .attr("x", function (d) { return (d.x - v[0]) * k + width / 2; })
      .attr("y", function (d) { return (d.y - v[1]) * k + height / 2; })
      .attr("font-size", function (d) { return Math.max((d.r * k) / 5, 8) + "px"; })
      .text(function (d) { return truncateLabel(d.data.name, d.r * k); });
  }

  function truncateLabel(name, radius) {
    if (radius < 30) return "";
    var maxChars = Math.floor(radius / 4);
    if (name.length <= maxChars) return name;
    return name.substring(0, maxChars - 1) + "\u2026";
  }

  function positionTooltip(event, tooltip, wrapper) {
    var rect = wrapper.getBoundingClientRect();
    var x = event.clientX - rect.left + 12;
    var y = event.clientY - rect.top - 10;
    tooltip.style("left", x + "px").style("top", y + "px");
  }

  return { render: render };
})();
