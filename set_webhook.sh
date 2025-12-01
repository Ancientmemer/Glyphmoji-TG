#!/usr/bin/env bash
# Usage: ./set_webhook.sh https://your-app.koyeb.app
if [ -z "$1" ]; then
  echo "Usage: $0 https://your-app.koyeb.app"
  exit 1
fi

APP_URL="$1"
if [ -z "$TG_TOKEN" ]; then
  echo "Export TG_TOKEN in your shell first (export TG_TOKEN=...)"
  exit 1
fi

WEBHOOK_URL="${APP_URL}/${TG_TOKEN}"
echo "Setting webhook to $WEBHOOK_URL"

curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/setWebhook" -F "url=${WEBHOOK_URL}" | jq . || true
