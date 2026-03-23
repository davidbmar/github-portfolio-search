#!/usr/bin/env bash
# deploy.sh — Deploy the web UI to davidbmar.com via S3/CloudFront
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

S3_BUCKET="s3://davidbmar-com/"
CF_DISTRIBUTION="E3RCY6XA80ANRT"

# 1. Check for web/ directory
if [ ! -d "web/" ]; then
    echo "Error: web/ directory not found." >&2
    exit 1
fi

# 2. If export module exists, run data export
if [ -f "src/ghps/export.py" ]; then
    echo "Running ghps export..."
    if [ -x ".venv/bin/ghps" ]; then
        .venv/bin/ghps export || echo "WARNING: ghps export failed — deploying with existing data"
    elif command -v ghps &>/dev/null; then
        ghps export || echo "WARNING: ghps export failed — deploying with existing data"
    else
        echo "WARNING: ghps not found — deploying with existing data"
    fi
fi

# 3. Validate data files before deploying
validate_json() {
    local file="$1"
    local min_entries="$2"
    local label="$3"

    if [ ! -f "$file" ]; then
        echo "Error: ${label} not found at ${file}" >&2
        return 1
    fi

    local size
    size=$(wc -c < "$file" | tr -d ' ')
    if [ "$size" -lt 10 ]; then
        echo "Error: ${label} is empty or too small (${size} bytes)" >&2
        return 1
    fi

    if ! python3 -c "import json, sys; data=json.load(open('${file}')); assert isinstance(data, list) and len(data) >= ${min_entries}, f'Expected ${min_entries}+ entries, got {len(data)}'" 2>/dev/null; then
        echo "Error: ${label} is not valid JSON or has fewer than ${min_entries} entries" >&2
        return 1
    fi

    echo "${label}: OK ($(python3 -c "import json; print(len(json.load(open('${file}'))))")  entries)"
}

echo "Validating data files..."
validate_json "web/data/repos.json" 1 "repos.json" || exit 1
validate_json "web/data/clusters.json" 1 "clusters.json" || exit 1

# 4. Generate deploy metadata
COMMIT=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEPLOYED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPO_COUNT=$(python3 -c "import json; print(len(json.load(open('web/data/repos.json'))))")
CLUSTER_COUNT=$(python3 -c "import json; print(len(json.load(open('web/data/clusters.json'))))")
FILE_COUNT=$(find web/ -type f | wc -l | tr -d ' ')

echo "Generating deploy-manifest.json..."
python3 -c "
import json
manifest = {
    'project': 'github-portfolio-search',
    'commit': '${COMMIT}',
    'branch': '${BRANCH}',
    'deployedAt': '${DEPLOYED_AT}',
    'repoCount': ${REPO_COUNT},
    'clusterCount': ${CLUSTER_COUNT},
    'fileCount': ${FILE_COUNT}
}
with open('web/deploy-manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
    f.write('\n')
"

echo "Generating health.json..."
python3 -c "
import json
health = {
    'status': 'ok',
    'commit': '${COMMIT}',
    'last_deploy': '${DEPLOYED_AT}',
    'repos': ${REPO_COUNT}
}
with open('web/health.json', 'w') as f:
    json.dump(health, f, indent=2)
    f.write('\n')
"

# 5. Sync to S3
echo "Syncing web/ to ${S3_BUCKET}..."
aws s3 sync web/ "$S3_BUCKET" --delete --exclude "*.pyc"

# 6. Invalidate CloudFront cache
echo "Invalidating CloudFront distribution ${CF_DISTRIBUTION}..."
aws cloudfront create-invalidation --distribution-id "$CF_DISTRIBUTION" --paths "/*"

# 7. Append to local deploy log
mkdir -p .sprint/history
python3 -c "
import json
entry = {
    'project': 'github-portfolio-search',
    'commit': '${COMMIT}',
    'branch': '${BRANCH}',
    'deployedAt': '${DEPLOYED_AT}',
    'repoCount': ${REPO_COUNT},
    'clusterCount': ${CLUSTER_COUNT},
    'fileCount': ${FILE_COUNT}
}
with open('.sprint/history/deploy-log.jsonl', 'a') as f:
    f.write(json.dumps(entry) + '\n')
"

# 8. Done
echo "Deployed commit ${COMMIT} (${REPO_COUNT} repos, ${CLUSTER_COUNT} clusters) to https://davidbmar.com"
