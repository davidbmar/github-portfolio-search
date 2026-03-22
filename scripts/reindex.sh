#!/usr/bin/env bash
# reindex.sh — Index GitHub repos, export static JSON, and deploy to S3/CloudFront.
#
# Usage:
#   GITHUB_TOKEN=ghp_xxx ./scripts/reindex.sh
#
# Idempotent — safe to run multiple times.
# Reads GITHUB_TOKEN from env (or .env file in repo root).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Source .env if it exists
if [ -f "${REPO_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
    set +a
fi

USERNAME="${GHPS_USERNAME:-davidbmar}"
DB_PATH="${REPO_ROOT}/ghps.db"
OUTPUT_DIR="${REPO_ROOT}/web/data"
VENV_DIR="${REPO_ROOT}/.venv"

# --- Preflight checks ---

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required."
    echo "Create a token at https://github.com/settings/tokens"
    exit 1
fi

# --- Virtual environment setup ---

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

if ! python3 -c "import ghps" 2>/dev/null; then
    echo "Installing ghps package..."
    pip install -e "${REPO_ROOT}" --quiet
fi

# --- Step 1: Index ---

echo ""
echo "=== Step 1: Indexing repos for ${USERNAME} ==="
ghps index "$USERNAME" --db "$DB_PATH"

REPO_COUNT=$(python3 -c "
import sqlite3, sys
db = sqlite3.connect('${DB_PATH}')
print(db.execute('SELECT COUNT(*) FROM repos').fetchone()[0])
")
echo "  Repos indexed: ${REPO_COUNT}"

# --- Step 2: Export ---

echo ""
echo "=== Step 2: Exporting static JSON to ${OUTPUT_DIR} ==="
mkdir -p "$OUTPUT_DIR"
ghps export --db "$DB_PATH" --output "$OUTPUT_DIR"

FILES_EXPORTED=0
for f in "${OUTPUT_DIR}"/*.json; do
    [ -f "$f" ] && FILES_EXPORTED=$((FILES_EXPORTED + 1))
done
echo "  Files exported: ${FILES_EXPORTED}"

# --- Step 3: Deploy ---

echo ""
echo "=== Step 3: Deploying to S3/CloudFront ==="

DEPLOY_STATUS="skipped"

if command -v aws &>/dev/null; then
    S3_BUCKET="s3://davidbmar-com/"
    CF_DISTRIBUTION="E3RCY6XA80ANRT"

    aws s3 sync "${REPO_ROOT}/web/" "$S3_BUCKET" --delete --exclude "*.pyc"
    aws cloudfront create-invalidation --distribution-id "$CF_DISTRIBUTION" --paths "/*" > /dev/null
    DEPLOY_STATUS="success"
    echo "  Deployed to https://davidbmar.com"
else
    echo "  AWS CLI not found — skipping deploy"
    DEPLOY_STATUS="skipped (no aws cli)"
fi

# --- Summary ---

echo ""
echo "=== Summary ==="
echo "  Repos indexed:  ${REPO_COUNT}"
echo "  Files exported: ${FILES_EXPORTED}"
echo "  Deploy status:  ${DEPLOY_STATUS}"
