# Pesiki-bot: Deploy on push (like Railway)

Push to `GlebkaF/pesiki-bot` → auto-deploy on x260. Uses a **self-hosted GitHub Actions runner** (x260 is in a private network, so cloud runners cannot reach it).

## Architecture

```
[GitHub] ← push → [GitHub Actions] → job dispatched to → [x260 runner] → docker compose up -d --build
```

The runner on x260 connects outbound to GitHub. When you push, GitHub sends the job to the runner; the runner builds and runs the bot locally.

## One-time setup

### 1. Run Ansible playbook (on x260)

```bash
cd /opt/x260/ansible
ansible-playbook -i inventory/hosts.yml playbooks/pesiki-bot.yml
```

This installs Docker, creates `/opt/pesiki-bot`, downloads the runner package.

**Note:** After the playbook, you may need to log out and back in (or run `newgrp docker`) so your user gets the docker group.

### 2. Add GitHub Secrets

Go to **pesiki-bot repo → Settings → Secrets and variables → Actions**. Add repository secrets:

| Secret | Required |
|--------|----------|
| `TELEGRAM_BOT_TOKEN` | yes |
| `TELEGRAM_CHAT_ID` | yes |
| `STEAM_API_KEY` | yes |
| `OPENAI_API_KEY` | yes (for /copium, /analyze) |
| `HTTPS_PROXY` | no (if OpenAI blocked in your region) |
| `NO_PROXY` | no (comma-separated hosts to bypass proxy) |

Secrets are passed directly to the container via env. No `.env` file on disk.

### 3. Register the self-hosted runner

On x260: go to `/opt/github-runner` (created by the playbook). Get the token from **pesiki-bot repo → Settings → Actions → Runners → New self-hosted runner**, then run `./config.sh --url https://github.com/GlebkaF/pesiki-bot --token <TOKEN> --name x260 --labels x260,linux`. Optionally install the service: `./svc.sh install` and `./svc.sh start`.

### 4. Add workflow to pesiki-bot repo

Copy `docs/pesiki-bot-deploy.yml` to the pesiki-bot repo:

```bash
mkdir -p pesiki-bot/.github/workflows
cp /opt/x260/docs/pesiki-bot-deploy.yml pesiki-bot/.github/workflows/deploy.yml
cd pesiki-bot && git add .github/workflows/deploy.yml && git commit -m "Add deploy workflow for x260" && git push
```

Or create `pesiki-bot/.github/workflows/deploy.yml` manually with the content from `docs/pesiki-bot-deploy.yml`.

## After setup

- **Push to `main`** → workflow runs on x260 → bot is rebuilt and restarted via `docker compose up -d --build`.
- **Logs**: `docker logs pesiki-bot -f`
- **Manual restart**: `docker restart pesiki-bot`
- **Manual full redeploy**: `cd /opt/x260/pesiki-bot && docker compose up -d --build`

## Troubleshooting /copium

`/yesterday` uses only OpenDota API. **`/copium`** (and `/analyze`) also call **OpenAI**. If `/copium` fails but `/yesterday` works:

1. **Check env** — secrets in GitHub (Settings → Secrets) or `/opt/pesiki-bot/.env` (written by workflow):
   - `OPENAI_API_KEY` must be set (get from OpenAI or from a proxy service like AITUNNEL/ProxyAPI, see `.env.example`).
   - If the server is in a region where OpenAI is blocked: set `HTTPS_PROXY` (e.g. `HTTPS_PROXY=http://proxy:8080`).
   - Optional: `OPENAI_MODEL` (default is `gpt-5.2`; use `gpt-4o-mini` or `gpt-4o` if your provider doesn’t support gpt-5.2).

2. **See the real error** in container logs:
   ```bash
   docker logs pesiki-bot -f
   ```
   Then trigger `/copium` and look for `[ERROR] Failed to handle /copium command` and the stack trace (e.g. API key invalid, timeout, proxy unreachable).

3. **Restart after changing secrets**: update the secret in GitHub, push to trigger redeploy, or `docker restart pesiki-bot` after manually editing `/opt/pesiki-bot/.env`.

4. **Timeouts from container but sites open fine on the host** — the container’s network is likely the issue (Docker bridge, DNS, or firewall). Check from inside the container:
   ```bash
   docker exec pesiki-bot wget -q -O- --timeout=10 https://api.opendota.com/api/players/92126977/recentMatches | head -c 200
   ```
   If this hangs or fails, the deploy already uses `network_mode: host` in `docker-compose.yml`. Ensure you're on the latest version.

## Files reference

| File | Purpose |
|------|---------|
| `ansible/playbooks/pesiki-bot.yml` | Docker, /opt/pesiki-bot, runner package |
| `docs/pesiki-bot-deploy.yml` | Workflow to copy into pesiki-bot repo |
| `pesiki-bot/docker-compose.yml` | Compose config (in pesiki-bot repo) |
