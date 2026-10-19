# Running CookieSync on Windows

**English** | [Русский](WINDOWS.ru.md)

The server runs directly on Windows using Python. This guide uses PowerShell
and the directory `C:\CookieSync`. If the project is elsewhere, substitute that
path in the commands and startup configuration.

## 1. Preparation

1. Install **Python 3.13 x64** from [python.org](https://www.python.org/downloads/windows/),
   including Python Launcher (`py`). The project specifies Python 3.13.
2. Copy the project or extract its repository archive into `C:\CookieSync`.
   `manage.py` must be at `C:\CookieSync\cookieserver\manage.py`.
3. Open PowerShell and run:

```powershell
Set-Location C:\CookieSync
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\cookieserver\requirements.txt
New-Item -ItemType Directory -Force .\cookieserver\accounts, .\cookieserver\keys
```

When moving the project from Linux, recreate `.venv` on Windows: a Linux virtual
environment cannot be transferred. Activation is unnecessary because the commands
below invoke the virtual environment's `python.exe` directly.

## 2. Configuration

The server always reads **`cookieserver\server_config.conf`**. The same configuration
is used on Linux and Windows; edit it directly:

```powershell
notepad .\cookieserver\server_config.conf
```

Preserve existing settings when editing an established deployment. Save as UTF-8
without a BOM. Windows TLS path examples are provided below.

Main settings:

| Setting                        | Value / purpose                                                        |
|--------------------------------|------------------------------------------------------------------------|
| `host = 0.0.0.0`               | Accept connections on all IPv4 interfaces                              |
| `port = 52314`                 | Server TCP port                                                        |
| `ping_interval = 30`           | Protocol heartbeat interval, seconds                                   |
| `ping_timeout = 10`            | Time to wait for the heartbeat reply, seconds                          |
| `broadcast_timeout = 5`        | Maximum wait for one broadcast recipient, seconds                      |
| `cookie_update_interval = 300` | Minimum interval between different cookie pairs in an account, seconds |
| `max_size = 16384`             | Maximum incoming message size, bytes                                   |
| `log_level = INFO`             | Logging level                                                          |

TLS is enabled by default. Disable it with `--no-tls`, not a configuration setting.
There is no `--config` command-line option. Restart the server after changing the config.

## 3. Accounts are created automatically

Use the same account name in extensions belonging to one group, for example
`office_team`. On the first connection, the extension sends `register` with that
name and the server creates the account. Subsequent clients reuse the account and
receive its cookies. There are no manual account creation or deletion commands.
List accounts with:

```powershell
.\.venv\Scripts\python.exe -m cookieserver.manage list_accounts
```

New names allow 1–64 letters, digits, underscores or hyphens, up to 200 UTF-8 bytes.
Windows device names such as `CON`, `NUL` and `COM1` are forbidden.
Use the same letter case on every client.

Accounts and cookies are stored in `cookieserver\accounts\*.json`. The server
loads them on startup and saves new accounts during registration. The server user
needs write access to that directory, or its parent if the directory must be created.
Existing accounts and cookies survive a restart. Run one server instance per
accounts directory.

## 4. First run on a local network

For a test on a trusted local network, start without a certificate:

```powershell
Set-Location C:\CookieSync
.\.venv\Scripts\python.exe -m cookieserver.manage runserver --no-tls
```

Keep the window open. Logs appear in the console; use `Ctrl+C` to stop the server.
`ws://` sends cookies without encryption. For Internet connections, use TLS as
described in the next section.

Allow inbound connections. Run this command in a separate PowerShell window **as administrator**, for a private local
network:

```powershell
New-NetFirewallRule -DisplayName "CookieSync TCP 52314 LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 52314 -Profile Private -RemoteAddress LocalSubnet
```

This rule applies only to the Private network profile and local-subnet clients.
For a VPN or another subnet, specify its address range and the appropriate network
profile. If you change the port, update the rule too.

Find the server's IPv4 address using `ipconfig`. Configure the extension:

- **Server URL:** `ws://192.168.1.10:52314` — replace the IP with the Windows server's address;
- **Account:** `office_team` — the shared name for this group of clients;
- enable synchronization.

On the server itself, you can use `ws://127.0.0.1:52314`. `0.0.0.0` is a bind
address, not the address clients should connect to.

From a Windows client, check port reachability:

```powershell
Test-NetConnection 192.168.1.10 -Port 52314
```

`TcpTestSucceeded : True` confirms TCP reachability, but does not validate TLS,
the account or the WebSocket protocol. The port does not serve a regular web page.

## 5. Running with TLS (`wss://`)

For a permanent deployment, prepare a DNS name such as `sync.example.com` pointing
to the server and a trusted certificate for that name. On Windows, an ACME client
such as win-acme can obtain the certificate and save it and its private key as **PEM**. Configure the domain validation
method (HTTP-01 or DNS-01) to suit your network.

Copy the full certificate chain and its matching private key to:

```text
C:\CookieSync\cookieserver\keys\fullchain.pem
C:\CookieSync\cookieserver\keys\privkey.pem
```

In the `[server]` section of `cookieserver\server_config.conf`, set:

```ini
cert = C:/CookieSync/cookieserver/keys/fullchain.pem
key = C:/CookieSync/cookieserver/keys/privkey.pem
```

Use absolute paths without quotes. Relative certificate paths are resolved against
the process working directory. A `.pfx` file cannot be used directly. Startup does
not prompt for a key password, so use an unencrypted PEM key with access restricted
to the required users.

Stop the test server and start without `--no-tls`:

```powershell
.\.venv\Scripts\python.exe -m cookieserver.manage runserver
```

Use **`wss://sync.example.com:52314`** in the extension. The URL hostname must match
the certificate. For a self-signed certificate, configure trust on each client,
including its browser; merely having certificate files on the server is insufficient.
The server does not generate certificates itself.

For external connections, allow TCP port `52314` in Windows Firewall for the clients
or VPN and configure router port forwarding if the server is behind NAT. Also update
any cloud firewall. Configure automatic certificate renewal in the ACME client and
restart CookieSync after renewal: the running server does not reload certificates.

The current server has no separate client password or token; the account name
selects the account. For remote deployment, restrict network access to clients or
a VPN. TLS encrypts the connection but does not add client authentication.

## 6. Automatic startup with Windows Task Scheduler

After a successful manual test, open `taskschd.msc` and choose **Create Task**:

1. **General:** name it `CookieSync`; select a user with access to the project,
   certificates and write permission for `cookieserver\accounts`.
   Select Run whether user is logged on or not. Supply the Windows account
   password if prompted.
2. **Triggers:** At startup.
3. **Actions → Start a program:**
    - program: `C:\CookieSync\.venv\Scripts\python.exe`;
    - TLS arguments: `-u -m cookieserver.manage runserver`;
    - for the tested non-TLS setup: `-u -m cookieserver.manage runserver --no-tls`;
    - working directory (Start in): `C:\CookieSync`.
4. **Conditions:** if appropriate, disable the restriction to AC power.
   The computer must not sleep while serving clients.
5. **Settings:** disable the maximum task duration; enable restart on failure (for example, after 1 minute, up to 999
   attempts). If the task is already
   running, select Do not start a new instance.

Stop the manual instance, start the scheduled task, and test extension connectivity.
Running (`0x41301`) is a normal status: the server is a long-running process.
Task Scheduler does not save Python console logs automatically. For diagnostics,
stop the task and run the same command manually in PowerShell.

## 7. Maintenance and common errors

- **`No module named cookieserver`:** run from `C:\CookieSync` using
  `-m cookieserver.manage`, not the direct path to `manage.py`.
- **`No module named websockets`:** install `cookieserver\requirements.txt`
  using the same `.venv\Scripts\python.exe` that runs the server.
- **`FileNotFoundError` with TLS:** check the PEM file paths. For a local test,
  explicitly use `--no-tls`.
- **`WinError 10048`:** the port is occupied; the scheduled task may already be running.
- **Cannot connect:** check IP/DNS, firewall, port availability, and match
  `ws://` with `--no-tls` or `wss://` with TLS.
- **Account registration error:** check the name, write permissions for
  `cookieserver\accounts`, and server logs. If `register` still returns an
  account-not-found error, update the server to support automatic account creation.
- **Client does not upload cookies:** open `office.reso.ru` and sign in;
  the extension checks authentication through an open tab.
- **A new pair is not accepted immediately:** `cookie_update_interval = 300`
  sets a five-minute interval between different pairs in an account.

For backups, stop the server and copy `cookieserver\accounts`, the active config
and TLS keys to a protected location. Stop the scheduled task before updates,
update code and dependencies, then start it again. When moving to another computer,
create a new virtual environment and check the certificate paths.
