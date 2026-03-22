#!/usr/bin/env bash
# deploy.sh — Build and deploy the web UI to S3/CloudFront at davidbmar.com
# Idempotent: safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
S3_BUCKET="s3://davidbmar-com"
CLOUDFRONT_DISTRIBUTION="E3RCY6XA80ANRT"
BUILD_DIR="${SCRIPT_DIR}/_build"

echo "=== Deploy: github-portfolio-search web UI ==="
echo "Bucket:       ${S3_BUCKET}"
echo "Distribution: ${CLOUDFRONT_DISTRIBUTION}"
echo ""

# ── 1. Generate fresh data via ghps export ──────────────────────────
echo ">> Step 1: Generating fresh data..."
if command -v ghps &>/dev/null; then
    ghps export --output-dir "${SCRIPT_DIR}/web/data" || {
        echo "   WARNING: 'ghps export' failed — deploying with existing data"
    }
else
    echo "   WARNING: 'ghps' CLI not found — deploying with existing data"
fi

# ── 2. Prepare build directory ──────────────────────────────────────
echo ">> Step 2: Preparing build directory..."
mkdir -p "${BUILD_DIR}"
# Copy web/ contents (html, css, js, data)
cp -R "${SCRIPT_DIR}/web/"* "${BUILD_DIR}/"

# Update health.json with deploy timestamp
cat > "${BUILD_DIR}/health.json" <<HEALTH_EOF
{
  "version": "4.0.0",
  "status": "ok",
  "last_deploy": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
HEALTH_EOF

echo "   Build directory ready: ${BUILD_DIR}"

# ── 3. Upload to S3 ────────────────────────────────────────────────
echo ">> Step 3: Uploading to S3..."
aws s3 sync "${BUILD_DIR}" "${S3_BUCKET}" \
    --delete \
    --exclude ".gitkeep" \
    --cache-control "max-age=300"
echo "   Upload complete."

# ── 4. Invalidate CloudFront cache ─────────────────────────────────
echo ">> Step 4: Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "${CLOUDFRONT_DISTRIBUTION}" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)
echo "   Invalidation created: ${INVALIDATION_ID}"

# ── 5. Done ─────────────────────────────────────────────────────────
echo ""
echo "=== Deploy complete ==="
echo "Live URL: https://davidbmar.com"
echo "Health:   https://davidbmar.com/health.json"
