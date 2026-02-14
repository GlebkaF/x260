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

**SSH:** Password login is disabled; only key-based auth. Ubuntu’s cloud-init drops `50-cloud-init.conf` with `PasswordAuthentication yes`, so we deploy `00-ssh-key-only.conf` (sshd uses first value). Managed by `base.yml` → `ansible/playbooks/files/00-ssh-key-only.conf`.

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
3. Runner: `docker compose up -d --build` with env from **GitHub Secrets** (passed directly to container). `network_mode: host`, `TZ=Europe/Moscow`.

Workflow template in this repo: `docs/pesiki-bot-deploy.yml` (copy into pesiki-bot repo as `.github/workflows/deploy.yml` if setting up from scratch).

### Env (GitHub Secrets)

Secrets live in **GitHub → Settings → Secrets and variables → Actions**. Required: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `STEAM_API_KEY`, `OPENAI_API_KEY`. Optional: `HTTPS_PROXY`, `NO_PROXY`. Passed directly to the container, no `.env` file.

- **Proxy:** If OpenAI/OpenDota are unreachable, set `HTTPS_PROXY`. **Steam (LFG)** uses direct fetch (no proxy); see `pesiki-bot/src/proxy.ts`.
- **Optional:** `OPENAI_MODEL`, `OPENAI_BASE_URL` (add to workflow if needed).

### Commands (on x260)

```bash
# Logs
docker logs pesiki-bot -f

# Restart (e.g. after .env change)
docker restart pesiki-bot

# Manual full redeploy (export vars first, or push to trigger CI)
cd /opt/x260/pesiki-bot && docker compose up -d --build
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

## Caddy (reverse proxy, HTTPS)

- **Playbook:** `playbooks/caddy.yml`
- **Config:** `ansible/playbooks/templates/Caddyfile.j2` (template), deployed to `/opt/caddy/Caddyfile`
- **Subdomains:** In `inventory/group_vars/x260_servers.yml` set `caddy_domain` (e.g. `nxrig.com`) and `caddy_sites`:
  - `subdomain: null` — static files from `/usr/share/caddy`
  - `subdomain: 9000` — reverse_proxy to `localhost:9000`
- **DNS:** Add A record for each subdomain (e.g. `x260`, `portainer`) → server's public IP (5.130.109.156). Or wildcard `*` → IP (requires DNS-01 for Let's Encrypt, more complex).
- **Let's Encrypt:** Set `caddy_email`. Ports 80 and 443 must be reachable from the internet.
- **IP-only (self-signed):** Leave `caddy_domain` empty; Caddy uses `tls internal`.

---

## Ansible (quick ref)

- Inventory: `ansible/inventory/hosts.yml`.
- Run playbook: `cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/<name>.yml`.
- Examples: `base.yml`, `pesiki-bot.yml`, `caddy.yml`, `monitoring.yml`.

---

## Reference

- **Pesiki-bot deploy doc:** `docs/pesiki-bot-deploy.md`
- **Server overview:** `docs/server.md`
- **README:** `README.md`

When you add a new service or fix a recurring issue, add a short section or bullet here so the next agent (or you) has it in one place.
