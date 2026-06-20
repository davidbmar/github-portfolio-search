// CloudFront Function (viewer-request) for davidbmar.com
// ---------------------------------------------------------------------------
// Two responsibilities:
//   1. Project-docs SHORTHAND:  /<slug>/docs[/...]  ->  /projects/<slug>/docs[/...]
//      so `davidbmar.com/riff/docs` reaches the same page as
//      `davidbmar.com/projects/riff/docs`.
//   2. Extensionless URL rewrite: append ".html" (or "/index.html" for a
//      trailing slash) so /projects/<slug>/docs, /docs/html, /docs/md resolve to
//      the flat files the generator writes (docs.html, html.html, md.html, ...).
//
// NOTE: This repo does not own the deployed CF function — it lives in the
// CloudFront distribution (E3RCY6XA80ANRT). This file is the source of truth to
// PASTE into that function. Deploy + test it before relying on the shorthand;
// the rest of the docs feature works today via the existing .html-rewrite.
//
// The RESERVED set prevents the shorthand from shadowing real top-level paths
// (so /data/foo is never rewritten to /projects/data/foo). Keep it in sync with
// the top-level entries under web/.
var RESERVED = {
  projects: 1, data: 1, js: 1, css: 1, assets: 1,
  'index.html': 1, 'embed.html': 1, 'llms.txt': 1, 'robots.txt': 1,
  'sitemap.xml': 1, 'health.json': 1, 'deploy-manifest.json': 1, 'config.json': 1,
};

function handler(event) {
  var req = event.request;
  var uri = req.uri;

  // 1. Shorthand: /<slug>/docs...  ->  /projects/<slug>/docs...
  var m = uri.match(/^\/([^\/]+)\/docs(\/.*|$)/);
  if (m && RESERVED[m[1]] !== 1) {
    uri = '/projects/' + m[1] + '/docs' + (m[2] || '');
  }

  // 2. Extensionless -> .html ; trailing slash -> index.html
  if (uri.endsWith('/')) {
    uri = uri + 'index.html';
  } else if (uri.lastIndexOf('.') <= uri.lastIndexOf('/')) {
    // no file extension in the last path segment
    uri = uri + '.html';
  }

  req.uri = uri;
  return req;
}
