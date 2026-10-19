#!/bin/bash
# Install the prepared /opt/CookieSync deployment as a systemd service.
# This script does not clone the project, create a venv, install Python packages,
# or generate TLS keys. Complete the preparation steps in LINUX.md first.
set -euo pipefail

usage() {
    printf 'Usage: sudo bash cookieserver/install.sh [--tls|--no-tls]\n'
    printf 'Project location: /opt/CookieSync (prepare .venv and server_config.conf first).\n'
    printf 'Without an option, the unit defaults to TLS and existing drop-ins are preserved.\n'
    printf 'Requires a Linux host running systemd. The supplied unit runs as root.\n'
}

# Parse arguments before checking privileges so --help also works without sudo.
if [[ $# -gt 1 ]]; then usage >&2; exit 2; fi
TRANSPORT="${1:-}"
case "$TRANSPORT" in
    --help|-h) usage; exit 0 ;;
    ""|--tls|--no-tls) ;;
    *) usage >&2; exit 2 ;;
esac

if [[ $EUID -ne 0 ]]; then
    printf 'Run this installer as root (sudo).\n' >&2
    exit 1
fi

# Validate prerequisites before changing any service files or restarting a service.
for tool in systemctl install dirname readlink; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required command is missing: %s\n' "$tool" >&2
        exit 1
    fi
done
if [[ ! -d /run/systemd/system ]]; then
    printf 'This installer requires a Linux host booted with systemd.\n' >&2
    exit 1
fi

PROJECT=/opt/CookieSync
SCRIPT_DIR="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
SERVICE_NAME=cookiesync.service
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
PYTHON="$PROJECT/.venv/bin/python"
if [[ ! -x "$PYTHON" || ! -f "$PROJECT/cookieserver/manage.py" ]]; then
    printf 'Clone the repository into %s, create .venv and install cookieserver/requirements.txt first.\n' "$PROJECT" >&2
    exit 1
fi
if [[ ! -r "$PROJECT/cookieserver/server_config.conf" || ! -r "$SCRIPT_DIR/resoserver.service" ]]; then
    printf 'The server configuration or service template is missing or unreadable.\n' >&2
    exit 1
fi
# Import the actual deployment, not the current shell's working directory.
# --help validates imports/config parsing without starting a listener or loading accounts.
if ! (cd "$PROJECT" && PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m cookieserver.manage --help >/dev/null); then
    printf 'Server preflight failed. Check .venv dependencies and server_config.conf.\n' >&2
    exit 1
fi

# The unit leaves User/Group unset (system-service default: root). No account
# creation or recursive ownership changes are needed. Preserve existing data/modes.
if [[ ! -d "$PROJECT/cookieserver/accounts" ]]; then
    install -d -m 700 "$PROJECT/cookieserver/accounts"
fi
install -d -m 755 "$(dirname -- "$SERVICE_FILE")"
# Keep a numbered backup when replacing an existing main unit.
install --backup=numbered -m 644 "$SCRIPT_DIR/resoserver.service" "$SERVICE_FILE"

# Change only our transport drop-in when a mode is explicitly requested.
# Without a flag, preserve the existing mode; other administrator drop-ins remain.
if [[ -n "$TRANSPORT" ]]; then
    OVERRIDE_DIR="/etc/systemd/system/$SERVICE_NAME.d"
    install -d -m 755 "$OVERRIDE_DIR"
    EXTRA_ARGS=""
    if [[ "$TRANSPORT" == --no-tls ]]; then EXTRA_ARGS=" --no-tls"; fi
    printf '[Service]\nExecStart=\nExecStart=%s -m cookieserver.manage runserver%s\n' \
        "$PYTHON" "$EXTRA_ARGS" > "$OVERRIDE_DIR/cookiesync-transport.conf"
fi

# Reload definitions, enable startup on boot, and restart to apply the new unit.
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
if ! systemctl restart "$SERVICE_NAME"; then
    printf 'Service restart failed. Inspect: journalctl -u %s -n 50 --no-pager\n' "$SERVICE_NAME" >&2
    exit 1
fi
if ! systemctl status "$SERVICE_NAME" --no-pager; then
    printf 'Service is not healthy. Inspect: journalctl -u %s -n 50 --no-pager\n' "$SERVICE_NAME" >&2
    exit 1
fi
