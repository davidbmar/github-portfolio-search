/**
 * ExportManager — export search results as Markdown or JSON, trigger downloads.
 * Works in static mode (no API server required).
 */
var ExportManager = (function () {
  'use strict';

  /**
   * Export search results as a Markdown string.
   * @param {Array} results - Array of repo objects with name, language, stars, description, url, topics.
   * @param {string} query - The search query used.
   * @returns {string} Markdown-formatted string.
   */
  function exportAsMarkdown(results, query) {
    var lines = [];
    lines.push('# Search Results: "' + (query || '') + '"');
    lines.push('');

    if (!results || results.length === 0) {
      lines.push('_No results found._');
      return lines.join('\n');
    }

    results.forEach(function (repo) {
      lines.push('## ' + (repo.name || 'Untitled'));
      lines.push('- **Language:** ' + (repo.language || 'N/A'));
      lines.push('- **Stars:** ' + (typeof repo.stars === 'number' ? repo.stars : 0));
      lines.push('- **Description:** ' + (repo.description || 'No description'));
      lines.push('- **GitHub:** ' + (repo.url || ''));
      if (repo.topics && repo.topics.length > 0) {
        lines.push('- **Topics:** ' + repo.topics.join(', '));
      }
      lines.push('');
      lines.push('---');
      lines.push('');
    });

    return lines.join('\n');
  }

  /**
   * Export search results as a JSON string.
   * @param {Array} results - Array of repo objects.
   * @param {string} query - The search query used.
   * @returns {string} JSON-formatted string.
   */
  function exportAsJSON(results, query) {
    var payload = {
      query: query || '',
      exported_at: new Date().toISOString(),
      count: results ? results.length : 0,
      repos: (results || []).map(function (repo) {
        return {
          name: repo.name || '',
          language: repo.language || null,
          stars: typeof repo.stars === 'number' ? repo.stars : 0,
          description: repo.description || '',
          url: repo.url || '',
          topics: repo.topics || []
        };
      })
    };
    return JSON.stringify(payload, null, 2);
  }

  /**
   * Trigger a file download in the browser.
   * @param {string} content - File content.
   * @param {string} filename - Suggested filename.
   * @param {string} mimeType - MIME type (e.g. "text/markdown", "application/json").
   */
  function downloadFile(content, filename, mimeType) {
    var blob = new Blob([content], { type: mimeType || 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return {
    exportAsMarkdown: exportAsMarkdown,
    exportAsJSON: exportAsJSON,
    downloadFile: downloadFile
  };
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ExportManager;
}
