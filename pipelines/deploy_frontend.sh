#!/usr/bin/env bash
# deploy_frontend.sh — build the React app and sync it to S3, then
# invalidate CloudFront so the new build is served immediately.
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$INFRA_DIR/rete-frontend"

cd "$FRONTEND_DIR"

echo "Building..."
npm run build

BUCKET=$(cd "$INFRA_DIR" && terraform output -raw frontend_bucket_name)
DISTRIBUTION_ID=$(cd "$INFRA_DIR" && terraform output -raw frontend_distribution_id)

echo "Syncing to s3://${BUCKET}..."
aws s3 sync dist/ "s3://${BUCKET}/" --delete

echo "Invalidating CloudFront (${DISTRIBUTION_ID})..."
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*"

echo "Done. Live at:"
cd "$INFRA_DIR" && terraform output -raw frontend_url