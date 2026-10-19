# CookieSync on Linux (systemd)

**English** | [Русский](LINUX.ru.md)

This guide uses `/opt/CookieSync`, Python 3.11+, and the `cookiesync.service`
system service on a Linux host booted with systemd. The supplied unit leaves
`User` and `Group` unset and therefore runs as root unless a custom drop-in overrides it.

## Preparation

On Ubuntu/Debian, install Git, Python and venv support, then clone the repository:

```bash
sudo apt update
sudo apt install git python3 python3-venv
sudo mkdir -p /opt
sudo git clone https://github.com/the-repo-hub/CookieSync.git /opt/CookieSync
```

`git clone` creates `/opt/CookieSync` and downloads the project into it. These
commands are for a first installation: the destination must be absent or empty.
For an existing deployment, update its checkout instead of cloning over it.
After cloning, create the virtual environment on this machine and install the
server dependencies:

```bash
cd /opt/CookieSync
sudo python3 -m venv .venv
sudo .venv/bin/python -m pip install -r cookieserver/requirements.txt
```

Server settings are in `cookieserver/server_config.conf`. Accounts are created
automatically when extensions register and are saved in `cookieserver/accounts`.
Only one server instance should use a given accounts directory.

## Local-network service without TLS

From the project root:

```bash
sudo bash cookieserver/install.sh --no-tls
```

The installer creates the accounts directory if needed, preserves existing data
and directory permissions, and copies `cookieserver/resoserver.service` to
`/etc/systemd/system/cookiesync.service`, and configures execution through `.venv`.
An existing main unit is preserved as a numbered backup.
The `--no-tls` argument is configured in the drop-in file
`/etc/systemd/system/cookiesync.service.d/cookiesync-transport.conf`.

The extension defaults to `ws://localhost:52314`. `localhost` is the computer
running the browser. For a server on another machine, enter its IP address or
DNS name and check TCP port `52314`, routing and firewall settings.

If a service with another name is already in use, update that service instead
of starting a second instance on the same port.

## Service with TLS

Prepare a PEM certificate and key trusted by the client browsers.
Set absolute paths in the `[server]` section:

```ini
cert = /opt/CookieSync/cookieserver/keys/fullchain.pem
key = /opt/CookieSync/cookieserver/keys/privkey.pem
```

Provision readable certificate/key files before starting the TLS service.
The installer does not generate certificates or keys.

After preparing the certificates:

```bash
sudo bash cookieserver/install.sh --tls
```

Use `wss://<certificate-hostname>:52314` in the extension. Running the installer
without arguments defaults to TLS but preserves existing drop-ins. Use `--tls`
or `--no-tls` to explicitly select the transport. Other user-defined drop-ins
are also taken into account by systemd.

## Installer checks and scope

`install.sh` requires root, a running systemd host, the project at `/opt/CookieSync`,
an executable `.venv/bin/python`, installed server dependencies, a readable
`server_config.conf`, and the adjacent `resoserver.service` template. It checks
imports and config parsing with `python -m cookieserver.manage --help` before
changing service files. This check does not start the server or validate TLS keys.
The final commands restart the service and display its current status; reported
failures include a journal command. Confirm application startup using the journal
and an extension connection.

Read-only checks from the repository root:

```bash
bash -n cookieserver/install.sh
bash cookieserver/install.sh --help
```

With development dependencies installed, run the isolated installer tests:

```bash
.venv/bin/python -m pytest -q tests/test_install.py
```

They execute a copy of the script with temporary filesystem roots and mocked
privileged commands. They do not install a service on the test machine. After
a real installation, check the actual service and its journal as shown below.

## Management and updates

```bash
sudo systemctl status cookiesync.service --no-pager
sudo journalctl -u cookiesync.service -f
sudo systemctl restart cookiesync.service
sudo systemctl stop cookiesync.service
```

After changing code or configuration, restart the service. After changing a unit
or drop-in, run `sudo systemctl daemon-reload` first. Restart the server after
renewing a TLS certificate as well.

Update code with the service stopped, preserving the accounts directory,
configuration and keys. For releases introducing a new protocol command (such as `refresh` in 1.2.0), update the server
before the extensions.

## Manual execution and tests

```bash
make run_server ARGS=--no-tls
# TLS by default:
make run_server
```

Do not run a manual instance alongside the service on the same port.
For development, install `requirements-dev.txt` and run `make test` from the
project root. This runs pytest and the extension's Node tests.
