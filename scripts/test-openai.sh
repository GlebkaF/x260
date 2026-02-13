#!/bin/bash
# Test OpenAI connectivity. Usage: ./scripts/test-openai.sh
# Reads /opt/pesiki-bot/.env

set -e
cd /opt/x260/pesiki-bot
source /opt/pesiki-bot/.env 2>/dev/null || true

echo "=== OpenAI connectivity test ==="
echo "HTTPS_PROXY: ${HTTPS_PROXY:+set}"
echo "OPENAI_BASE_URL: ${OPENAI_BASE_URL:-default (api.openai.com)}"
echo ""

# Test with curl (use -x for proxy)
resp=$(curl -s -w "\n%{http_code}" --connect-timeout 15 \
  $([ -n "$HTTPS_PROXY" ] && echo "-x $HTTPS_PROXY") \
  -X POST "${OPENAI_BASE_URL:-https://api.openai.com}/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":5}')

code=$(echo "$resp" | tail -1)
body=$(echo "$resp" | sed '$d')

if [[ "$code" == "200" ]]; then
  echo "✅ Success (HTTP $code)"
  echo "$body" | head -c 200
else
  echo "❌ Failed (HTTP $code)"
  echo "$body"
fi
