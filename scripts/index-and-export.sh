#!/usr/bin/env bash
# index-and-export.sh — Index a GitHub user's repos and export static JSON for the web UI.
#
# Usage:
#   GITHUB_TOKEN=ghp_xxx ./scripts/index-and-export.sh <username>
#
# Requires GITHUB_TOKEN to be set for GitHub API access.
# Produces repos.json, clusters.json, and search-index.json in web/data/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Source .env if it exists (python-dotenv style)
if [ -f "${REPO_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
    set +a
fi
DB_PATH="${REPO_ROOT}/.ghps/index.db"
OUTPUT_DIR="${REPO_ROOT}/web/data"
VENV_DIR="${REPO_ROOT}/.venv"
USERNAME="${1:-}"

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <github-username>"
    echo "Example: GITHUB_TOKEN=ghp_xxx $0 davidbmar"
    exit 1
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required."
    echo "Create a token at https://github.com/settings/tokens"
    exit 1
fi

# Set up venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# Install the package if not already installed
if ! python3 -c "import ghps" 2>/dev/null; then
    echo "Installing ghps package..."
    pip install -e "${REPO_ROOT}" --quiet
fi

# Create database directory
mkdir -p "$(dirname "$DB_PATH")"

# Step 1: Index repos
echo ""
echo "=== Indexing repos for ${USERNAME} ==="
ghps index "$USERNAME" --db "$DB_PATH"

# Step 2: Export static JSON
echo ""
echo "=== Exporting static JSON to ${OUTPUT_DIR} ==="
ghps export --db "$DB_PATH" --output "$OUTPUT_DIR"

# Step 3: Validate JSON output
echo ""
echo "=== Validating output ==="
for FILE in repos.json clusters.json search-index.json; do
    FPATH="${OUTPUT_DIR}/${FILE}"
    if [ ! -f "$FPATH" ]; then
        echo "Error: ${FILE} was not generated"
        exit 1
    fi
    python3 -c "
import json, sys
with open('${FPATH}') as f:
    data = json.load(f)
if not isinstance(data, list):
    print('Error: ${FILE} is not a JSON array', file=sys.stderr)
    sys.exit(1)
if len(data) == 0:
    print('Warning: ${FILE} is empty', file=sys.stderr)
print(f'  ${FILE}: {len(data)} entries — valid')
" || exit 1
done

# Step 4: Print summary
echo ""
echo "=== Summary ==="
REPO_COUNT=$(python3 -c "import json; print(len(json.load(open('${OUTPUT_DIR}/repos.json'))))")
CLUSTER_COUNT=$(python3 -c "import json; print(len(json.load(open('${OUTPUT_DIR}/clusters.json'))))")
echo "${REPO_COUNT} repos indexed, ${CLUSTER_COUNT} clusters generated"
echo "Output files:"
ls -la "${OUTPUT_DIR}"/*.json
