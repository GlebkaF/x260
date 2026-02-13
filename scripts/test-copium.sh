#!/bin/bash
# Test /copium flow: OpenDota (direct) + OpenAI (proxy)
set -e
source /opt/pesiki-bot/.env 2>/dev/null || true

echo "=== 1. OpenDota (direct, no proxy) ==="
resp=$(curl -s -w "\n%{http_code}" --connect-timeout 10 \
  "https://api.opendota.com/api/players/92126977/recentMatches")
code=$(echo "$resp" | tail -1)
if [[ "$code" == "200" ]]; then
  matches=$(echo "$resp" | sed '$d' | grep -o '"match_id"' | wc -l)
  echo "✅ OK (HTTP $code), matches: $matches"
else
  echo "❌ Failed HTTP $code"
  exit 1
fi

echo ""
echo "=== 2. OpenAI (via proxy) ==="
resp=$(curl -s -w "\n%{http_code}" --connect-timeout 20 \
  -x "$HTTPS_PROXY" \
  -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Say hi"}],"max_tokens":5}')
code=$(echo "$resp" | tail -1)
if [[ "$code" == "200" ]]; then
  echo "✅ OK (HTTP $code)"
  echo "$resp" | sed '$d' | grep -o '"content":"[^"]*"' | head -1
else
  echo "❌ Failed HTTP $code"
  echo "$resp" | sed '$d' | head -c 200
  exit 1
fi

echo ""
echo "✅ All checks passed — /copium should work"
