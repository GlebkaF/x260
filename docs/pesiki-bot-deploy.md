# Pesiki-bot: Deploy on push (like Railway)

Push to `GlebkaF/pesiki-bot` → auto-deploy on x260. Uses a **self-hosted GitHub Actions runner** (x260 is in a private network, so cloud runners cannot reach it).

## Architecture

```
[GitHub] ← push → [GitHub Actions] → job dispatched to → [x260 runner] → docker build & run
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

### 2. Create .env (on x260)

Copy from Railway (if you have Railway CLI):
```bash
npm i -g @railway/cli
/opt/x260/scripts/copy-pesiki-env-from-railway.sh
```

Or manually:
```bash
cp /opt/pesiki-bot/.env.example /opt/pesiki-bot/.env
# Edit with your tokens: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc.
# (Copy from Railway dashboard → Service → Variables)
```

### 3. Register the self-hosted runner

```bash
/opt/x260/scripts/setup-github-runner.sh
```

Follow the prompts. Get the token from: **pesiki-bot repo → Settings → Actions → Runners → New self-hosted runner**.

### 4. Add workflow to pesiki-bot repo

Copy `docs/pesiki-bot-deploy.yml` to the pesiki-bot repo:

```bash
# From your local machine (or from x260 if you have the repo cloned)
mkdir -p pesiki-bot/.github/workflows
cp /opt/x260/docs/pesiki-bot-deploy.yml pesiki-bot/.github/workflows/deploy.yml
cd pesiki-bot && git add .github/workflows/deploy.yml && git commit -m "Add deploy workflow for x260" && git push
```

Or create `pesiki-bot/.github/workflows/deploy.yml` manually with the content from `docs/pesiki-bot-deploy.yml`.

## After setup

- **Push to `main`** → workflow runs on x260 → bot is rebuilt and restarted.
- **Logs**: `docker logs pesiki-bot -f`
- **Manual restart**: `docker restart pesiki-bot`

## Troubleshooting /copium

`/yesterday` uses only OpenDota API. **`/copium`** (and `/analyze`) also call **OpenAI**. If `/copium` fails but `/yesterday` works:

1. **Check env on the server** — in `/opt/pesiki-bot/.env`:
   - `OPENAI_API_KEY` must be set (get from OpenAI or from a proxy service like AITUNNEL/ProxyAPI, see `.env.example`).
   - If the server is in a region where OpenAI is blocked: set `HTTPS_PROXY` (e.g. `HTTPS_PROXY=http://proxy:8080`).
   - Optional: `OPENAI_MODEL` (default is `gpt-5.2`; use `gpt-4o-mini` or `gpt-4o` if your provider doesn’t support gpt-5.2).

2. **Test from the server** (sources `/opt/pesiki-bot/.env`):
   ```bash
   /opt/x260/scripts/test-copium.sh
   ```
   This checks OpenDota (direct) and OpenAI (via `HTTPS_PROXY` if set). If both pass, `/copium` should work.

3. **See the real error** in container logs:
   ```bash
   docker logs pesiki-bot -f
   ```
   Then trigger `/copium` and look for `[ERROR] Failed to handle /copium command` and the stack trace (e.g. API key invalid, timeout, proxy unreachable).

4. **Restart after changing .env**:
   ```bash
   docker restart pesiki-bot
   ```

5. **Timeouts from container but sites open fine on the host** — the container’s network is likely the issue (Docker bridge, DNS, or firewall). Check from inside the container:
   ```bash
   docker exec pesiki-bot wget -q -O- --timeout=10 https://api.opendota.com/api/players/92126977/recentMatches | head -c 200
   ```
   If this hangs or fails, run the bot with the host network so it uses the same network as the host:
   ```bash
   docker stop pesiki-bot && docker rm pesiki-bot
   docker run -d --name pesiki-bot --restart unless-stopped --network host \
     --env-file /opt/pesiki-bot/.env -e TZ=Europe/Moscow pesiki-bot
   ```
   (Add `--network host` to the workflow’s `docker run` in the pesiki-bot repo if you keep this fix.)

## Files reference

| File | Purpose |
|------|---------|
| `ansible/playbooks/pesiki-bot.yml` | Docker, /opt/pesiki-bot, runner package |
| `scripts/setup-github-runner.sh` | One-time runner registration |
| `scripts/test-copium.sh` | Test OpenDota + OpenAI (for /copium) from server |
| `docs/pesiki-bot-deploy.yml` | Workflow to copy into pesiki-bot repo |
