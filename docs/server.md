# x260 Server

## Overview

- **Role**: Home server (x260)
- **SSH**: `gleb@192.168.0.118`
- **OS**: Ubuntu Server (bare install)

## Purpose of this repo

- Single place to define how x260 is configured and what runs on it.
- All changes go through this repo: playbooks, configs, scripts.
- New services and automation are added here first, then applied via Ansible or scripts.

## Recommended next steps

1. **SSH key**: Copy your public key to the server so you can use key-based auth.
2. **Run base playbook**: `ansible-playbook -i inventory/hosts.yml playbooks/base.yml`.
3. **Add playbooks** for any services you want (Docker, backups, monitoring, etc.).
