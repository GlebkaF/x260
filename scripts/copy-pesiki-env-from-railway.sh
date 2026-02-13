#!/bin/bash
# Copy env vars from Railway to /opt/pesiki-bot/.env
# Run from pesiki-bot dir: cd /path/to/pesiki-bot && railway link && railway run printenv
# Or: install Railway CLI, link project, then run this.
#
# Alternative: copy manually from Railway dashboard → Service → Variables → Raw Editor

set -e
ENV_FILE="/opt/pesiki-bot/.env"

if ! command -v railway &>/dev/null; then
  echo "Railway CLI not installed. Install: npm i -g @railway/cli"
  echo "Or copy vars manually from https://railway.app dashboard"
  exit 1
fi

cd "$(dirname "$0")/.."
if [[ -d "pesiki-bot" ]]; then
  cd pesiki-bot
fi

echo "Linking Railway project (select pesiki-bot)..."
railway link 2>/dev/null || true

echo "Exporting variables to $ENV_FILE..."
railway run printenv 2>/dev/null | grep -E '^(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|BOT_TOKEN|CHAT_ID|STEAM_API_KEY|OPENAI_API_KEY|TZ|OPENAI_MODEL)=' > /tmp/railway_env.txt || {
  echo "Failed. Copy vars manually from Railway dashboard."
  exit 1
}
# Map Railway names (BOT_TOKEN, CHAT_ID) to pesiki-bot names
if grep -q '^BOT_TOKEN=' /tmp/railway_env.txt && ! grep -q '^TELEGRAM_BOT_TOKEN=' /tmp/railway_env.txt; then
  sed -i 's/^BOT_TOKEN=/TELEGRAM_BOT_TOKEN=/' /tmp/railway_env.txt
fi
if grep -q '^CHAT_ID=' /tmp/railway_env.txt && ! grep -q '^TELEGRAM_CHAT_ID=' /tmp/railway_env.txt; then
  sed -i 's/^CHAT_ID=/TELEGRAM_CHAT_ID=/' /tmp/railway_env.txt
fi
grep -E '^(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|STEAM_API_KEY|OPENAI_API_KEY|TZ|OPENAI_MODEL)=' /tmp/railway_env.txt > "$ENV_FILE"
rm -f /tmp/railway_env.txt

echo "Done. Check: cat $ENV_FILE"
