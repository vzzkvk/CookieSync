# CookieSync on Linux (systemd)

**English** | [Русский](LINUX.ru.md)

This guide uses `/opt/CookieSync`, Python 3.11+, and the `cookiesync.service`
system service. Copy the project into that directory before installation.

## Preparation

On Ubuntu/Debian, install Python and venv support:

```bash
sudo apt update
sudo apt install python3 python3-venv
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

The installer creates the `cookiesync` system user, assigns ownership of the
accounts directory, copies `cookieserver/resoserver.service` to
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

Ensure the `cookiesync` user can read these files and traverse their parent
directories. If the user does not exist yet, create it before setting permissions:

```bash
sudo useradd --system --user-group --home-dir /opt/CookieSync --no-create-home --shell /usr/sbin/nologin cookiesync
```

After preparing the certificates:

```bash
sudo bash cookieserver/install.sh --tls
```

Use `wss://<certificate-hostname>:52314` in the extension. Running the installer
without arguments defaults to TLS but preserves existing drop-ins. Use `--tls`
or `--no-tls` to explicitly select the transport. Other user-defined drop-ins
are also taken into account by systemd.

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
