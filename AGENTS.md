# AGENTS.md — x260 server runbook for AI agents

Important context for working on the **x260** home server. Update this file when you add services, change paths, or learn something that future agents (or humans) need.

---

## Server basics

| Item | Value |
|------|--------|
| Host | x260 |
| SSH | `gleb@192.168.0.118` |
| OS | Ubuntu Server |
| Repo (this one) | `/opt/x260` — single source of truth for config, playbooks, scripts |

**Workflow:** Connect via Cursor Remote-SSH to the server; edit and run everything from `/opt/x260`. Ansible and scripts are run on the server.

**Monitoring:** http://192.168.0.118:61208 (overview: CPU, RAM, disk, load). One-time: `cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/monitoring.yml`.

---

## Repo layout

- `ansible/` — inventory, playbooks (base, pesiki-bot, monitoring, etc.)
- `scripts/` — helper scripts (e.g. overview server for monitoring)
- `docs/` — runbooks and notes (e.g. pesiki-bot deploy)

Never commit secrets (API keys, `.env`, vault passwords). IP above is private (RFC 1918).

---

## Pesiki-bot (Telegram Dota 2 bot)

### Paths and roles

| Path | Purpose |
|------|--------|
| `/opt/pesiki-bot` | **Env and runner state on the server.** Contains `.env` (and `.env.example`). Not the app source. |
| `/opt/x260/pesiki-bot` | **Clone of the app repo** (GlebkaF/pesiki-bot). Code, `.github/workflows`, etc. Used to push and to copy workflow/docs from x260. |

So: “pesiki-bot repo” = app code at `/opt/x260/pesiki-bot`; “pesiki-bot on server” = env at `/opt/pesiki-bot`, container runs from image built by CI.

### Deploy flow

1. Push to `main` of **GlebkaF/pesiki-bot** (from `/opt/x260/pesiki-bot` or any clone).
2. GitHub Actions dispatches the job to the **self-hosted runner on x260** (x260 is in a private network; cloud runners cannot reach it).
3. Runner: `docker build -t pesiki-bot .` then stop/rm old container and `docker run` with `--env-file /opt/pesiki-bot/.env`, `--network host`, `TZ=Europe/Moscow`.

Workflow template in this repo: `docs/pesiki-bot-deploy.yml` (copy into pesiki-bot repo as `.github/workflows/deploy.yml` if setting up from scratch).

### Env (on server)

- **Required:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`; for /copium and /analyze: `OPENAI_API_KEY`.
- **Proxy:** If OpenAI/OpenDota are unreachable from the host, set `HTTPS_PROXY` (e.g. `http://proxy:8080`). When set, **proxied** requests (OpenAI, OpenDota, heroes, items) go through the proxy. **Steam (LFG)** always uses **direct** fetch (no proxy) to avoid proxy 502; see `pesiki-bot/src/proxy.ts` (`getProxiedFetch` vs `getDirectFetch`).
- **Optional:** `OPENAI_MODEL` (default `gpt-5.2`), `OPENAI_BASE_URL` (for proxy APIs).

Create `.env`: copy vars from Railway dashboard (or elsewhere), or `cp /opt/pesiki-bot/.env.example /opt/pesiki-bot/.env` and edit.

### Commands (on x260)

```bash
# Logs
docker logs pesiki-bot -f

# Restart (e.g. after .env change)
docker restart pesiki-bot

# Manual full redeploy (same as workflow does)
docker stop pesiki-bot 2>/dev/null; docker rm pesiki-bot 2>/dev/null
docker run -d --name pesiki-bot --restart unless-stopped --network host \
  --env-file /opt/pesiki-bot/.env -e TZ=Europe/Moscow pesiki-bot
```

### Troubleshooting /copium (and /analyze)

- **/yesterday** uses only OpenDota. **/copium** and **/analyze** use OpenDota + OpenAI (and heroes/items APIs). If /copium fails:
  1. **Env:** Check `OPENAI_API_KEY` and, if needed, `HTTPS_PROXY` in `/opt/pesiki-bot/.env`.
  2. **Real error:** `docker logs pesiki-bot -f`, then trigger /copium; look for `[ERROR] Failed to handle /copium command` and stack trace.
  3. **Container network:** If host can reach APIs but container times out, the deploy already uses `--network host`. If it didn’t, run the container with `--network host` (see “Manual full redeploy” above).
  4. After any `.env` change: `docker restart pesiki-bot`.

### Troubleshooting LFG (Steam)

- Steam (LFG) uses **direct** fetch (no proxy). If the host cannot reach api.steampowered.com directly, you’d need to change `steam.ts` to use `getProxiedFetch()` instead of `getDirectFetch()`. The bot retries Steam requests up to 3 times on 502/network errors.

### One-time setup (if not done)

- **Infra:** `cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/pesiki-bot.yml` (Docker, `/opt/pesiki-bot`, runner package).
- **Runner:** One-off: in GlebkaF/pesiki-bot → Settings → Actions → Runners add self-hosted runner, then on x260 run the runner config from `/opt/github-runner` (created by pesiki-bot.yml).
- **Workflow:** Ensure pesiki-bot repo has `.github/workflows/deploy.yml` (content from `docs/pesiki-bot-deploy.yml`).

---

## Ansible (quick ref)

- Inventory: `ansible/inventory/hosts.yml`.
- Run playbook: `cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/<name>.yml`.
- Examples: `base.yml`, `pesiki-bot.yml`, `monitoring.yml`.

---

## Reference

- **Pesiki-bot deploy doc:** `docs/pesiki-bot-deploy.md`
- **Server overview:** `docs/server.md`
- **README:** `README.md`

When you add a new service or fix a recurring issue, add a short section or bullet here so the next agent (or you) has it in one place.
