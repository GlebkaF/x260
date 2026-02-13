# x260 — Home Server Control Center

This repo is the single source of truth for the **x260** home server: config, playbooks, scripts. Workflow: open it in Cursor via **SSH** (connect to the server), edit and run everything from the server. No need to run Ansible or scripts from your local machine.

## Workflow: Cursor over SSH

1. In Cursor: **Remote-SSH** → connect to `gleb@192.168.0.118`.
2. On the server: clone this repo (or pull), edit, run playbooks/scripts there.
3. Push/pull from GitHub from the server when you want to sync or backup.

So the “control center” lives in this repo; you operate it **from the server** via Cursor.

## Server

| Item | Value |
|------|--------|
| Host | x260 |
| SSH  | `gleb@192.168.0.118` |
| OS   | Ubuntu Server |

On this server the repo is at **`/opt/x260`** (git clone there; not in home dir).

## Repo layout

```
.
├── README.md
├── LICENSE
├── ansible/             # Inventory, playbooks (run on server)
├── scripts/             # Helper scripts (run on server)
└── docs/                # Notes, runbooks
```

## On the server (after clone)

From `/opt/x260`:

- **Ansible** (optional): install once if you use playbooks (`sudo apt install -y ansible`), then run e.g. `cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/base.yml` for base setup.
- **Scripts**: run from `/opt/x260/scripts` as needed.

## Security (public repo)

This repo is meant to be **public**. Never commit:

- SSH keys, API keys, passwords
- `.env` with real secrets, `vault-password`, `*.pem`

Use `.env` or Ansible Vault only on the server; keep them out of the repo (`.gitignore` already excludes them).

**IP 192.168.0.118** — private (RFC 1918), not routable from the internet; safe to keep in the repo. To avoid exposing it at all, put `X260_HOST` and `X260_USER` in `.env` (see `.env.example`) and use scripts that read from env.

## License

MIT — see [LICENSE](LICENSE).
