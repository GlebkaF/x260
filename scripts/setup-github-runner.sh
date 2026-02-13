#!/bin/bash
# One-time setup: register GitHub Actions self-hosted runner for pesiki-bot.
# Run from x260: ./scripts/setup-github-runner.sh
#
# Prerequisites: ansible playbook pesiki-bot.yml has been run (Docker + runner dir).

set -e

RUNNER_DIR="/opt/github-runner"
REPO_URL="https://github.com/GlebkaF/pesiki-bot"

if [[ ! -f "$RUNNER_DIR/config.sh" ]]; then
  echo "Runner not extracted. Run: cd /opt/x260/ansible && ansible-playbook -i inventory/hosts.yml playbooks/pesiki-bot.yml"
  exit 1
fi

cd "$RUNNER_DIR"

if [[ -f ".runner" ]]; then
  echo "Runner already configured. To reconfigure: rm .runner .credentials .credentials_rsaparams"
  echo "Starting service..."
  sudo ./svc.sh start 2>/dev/null || ./run.sh
  exit 0
fi

if [[ -z "$GITHUB_RUNNER_TOKEN" ]]; then
  echo "Get a token from: $REPO_URL → Settings → Actions → Runners → New self-hosted runner"
  echo "Paste the token (or press Enter to run config interactively):"
  read -r TOKEN
else
  TOKEN="$GITHUB_RUNNER_TOKEN"
fi

if [[ -n "$TOKEN" ]]; then
  ./config.sh --url "$REPO_URL" --token "$TOKEN" --name x260 --labels x260,linux
else
  ./config.sh --url "$REPO_URL" --name x260 --labels x260,linux
fi

if [[ -n "$GITHUB_RUNNER_TOKEN" ]] || [[ "$INSTALL_SVC" == "1" ]]; then
  INSTALL=y
else
  echo "Install as systemd service? (y/n)"
  read -r INSTALL
fi
if [[ "$INSTALL" == "y" ]]; then
  sudo ./svc.sh install
  sudo ./svc.sh start
  echo "Runner service started. Check: sudo ./svc.sh status"
else
  echo "Run manually: cd $RUNNER_DIR && ./run.sh"
fi
