# CookieSync

**English** | [Русский](README.ru.md)

CookieSync synchronizes a pair of RESO Office cookies between browser clients
through a Python WebSocket server. Clients using the same account name on the
same server share stored cookies; different accounts and browser cookie stores
allow independent sessions.

```text
Browser A ↔ CookieServer ↔ Browser B
```

The extension version in the [manifest](extension/manifest.json) is **1.2.2**.
This README describes the current sources, including subsequent asynchronous-operation
fixes. Rebuild packages from the current code to distribute those fixes: the version
number alone does not distinguish these builds. Open issues are listed under
[Known limitations](#known-limitations).

## Documentation

| Document                                    | English                             | Русский                                |
|---------------------------------------------|-------------------------------------|----------------------------------------|
| Linux server and systemd                    | [EN](cookieserver/LINUX.md)         | [RU](cookieserver/LINUX.ru.md)         |
| Windows server and automatic startup        | [EN](cookieserver/WINDOWS.md)       | [RU](cookieserver/WINDOWS.ru.md)       |
| Local extension installation                | [EN](extension/INSTALL.txt)         | [RU](extension/INSTALL.ru.txt)         |
| Published or signed extension installation  | [EN](extension/INSTALL_RELEASE.txt) | [RU](extension/INSTALL_RELEASE.ru.txt) |
| Building, signing and distributing releases | [EN](RELEASE.md)                    | [RU](RELEASE.ru.md)                    |

English is the primary documentation language: unsuffixed files such as `README.md`
and `INSTALL.txt` contain English; Russian translations use `.ru.md` / `.ru.txt`.
Documentation is maintained in EN/RU pairs. When changing commands, requirements,
behavior or known limitations, update both versions of the corresponding document.
Extension archives include installation instructions in both languages.

## Requirements

| Component                | Requirements                                                                                                    |
|--------------------------|-----------------------------------------------------------------------------------------------------------------|
| Server                   | Python 3.11+; `.python-version` specifies Python 3.13                                                           |
| Server dependencies      | [cookieserver/requirements.txt](cookieserver/requirements.txt), `websockets==16.1`                              |
| Chrome / Chromium / Edge | Version 121 or later                                                                                            |
| Firefox, normal build    | Version 121 or later; temporary installation of an unsigned package                                             |
| Firefox, release build   | Version 140 or later; permanent installation requires Mozilla signing                                           |
| Development and tests    | Node.js 18+, [requirements-dev.txt](requirements-dev.txt), `openssl` for TLS tests; `make` for Makefile targets |

## Server quick start

Run all commands from the repository root. Linux example:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r cookieserver/requirements.txt
.venv/bin/python -m cookieserver.manage runserver --no-tls
```

With the current configuration, the server listens on `0.0.0.0:52314`. Set
`ws://<server-address>:52314` in the extension; on the same machine you can use
`ws://localhost:52314`. `localhost` refers to the computer running the browser;
for a server on another machine, enter its IP address or DNS name.

For Windows, follow the [dedicated guide](cookieserver/WINDOWS.md).
Both platforms use the same `cookieserver/server_config.conf`.
The Linux installer targets `/opt/CookieSync` and creates `cookiesync.service`;
environment setup and `--tls` / `--no-tls` modes are described in [LINUX.md](cookieserver/LINUX.md).

### TLS and configuration

The server reads the `[server]` section of
[cookieserver/server_config.conf](cookieserver/server_config.conf).
Restart it after changing settings.

| Setting                  | Current config value | Purpose                                                   |
|--------------------------|----------------------|-----------------------------------------------------------|
| `host`                   | `0.0.0.0`            | Bind address                                              |
| `port`                   | `52314`              | TCP port                                                  |
| `ping_interval`          | `30`                 | WebSocket protocol ping interval, seconds                 |
| `ping_timeout`           | `10`                 | Time to wait for pong, seconds                            |
| `broadcast_timeout`      | `5`                  | Send timeout for one broadcast recipient, seconds         |
| `cookie_update_interval` | `300`                | Interval between different accepted cookie pairs, seconds |
| `max_size`               | `16384`              | Maximum incoming message size, bytes                      |
| `encoding`               | `utf-8`              | Account-file encoding                                     |
| `log_level`              | `info`               | Logging level                                             |

**TLS is enabled by default.** Starting without `--no-tls` requires a PEM certificate
and key. Set paths with `cert` / `key` in the config or `--cert` / `--key` flags.
Defaults are `cookieserver/keys/cert.pem` and `cookieserver/keys/key.pem`.
Relative paths are resolved against the process working directory.

```bash
.venv/bin/python -m cookieserver.manage runserver --cert /path/to/fullchain.pem --key /path/to/privkey.pem
```

Use `ws://` without TLS and `wss://` with TLS. For `wss://`, browsers must trust the
certificate and the URL hostname must match it. `ws://` transmits cookies without
encryption. The protocol has no separate client password or token: network
configuration controls access to the server, and the account name selects the
synchronization group.

### Accounts and data

An account is automatically created on its first `register` and persisted before
registration succeeds. An existing account retains its cookies, revision and
cooldown. Each account has a JSON file in `cookieserver/accounts/`.

- New names allow 1–64 letters, digits, underscores or hyphens, up to 200 UTF-8 bytes.
- Windows device names (`CON`, `NUL`, `COM1` and similar) are forbidden.
- Clients in one group must use the same name and letter case.
- The Account field selects a CookieSync group, not a RESO user login.
- One accounts directory must be served by one server instance.
- Closing a browser does not delete a server account. Accounts have no automatic
  deletion period; expired-cookie cleanup preserves the account and its revision.

List account names without modifying files:

```bash
.venv/bin/python -m cookieserver.manage list_accounts
.venv/bin/python -m cookieserver.manage --help
```

The CLI has no manual account creation or deletion commands. Before moving or
backing up the server, stop it and save the accounts directory, configuration and TLS keys.

## Extension installation and setup

For local installation, use the normal archives described in the build section:

- **Chrome / Chromium / Edge:** extract `CookieSync-1.2.2-chromium.zip`, enable
  Developer mode on the extensions page, and choose Load unpacked.
- **Firefox:** extract `CookieSync-1.2.2-firefox.zip` and load `manifest.json`
  through `about:debugging#/runtime/this-firefox`. A temporary add-on is removed
  after a browser restart. Permanent installation requires a signed XPI or AMO.

For a published version, use the Chrome Web Store or AMO link, or the signed XPI
provided by the publisher. A local release build does not publish or sign the
extension; see [RELEASE.md](RELEASE.md).

After installation:

1. Open the desired tab and the CookieSync toolbar popup.
2. Set your group's account and server address. The default is `ws://localhost:52314`.
3. Grant access to RESO sites, open `office.reso.ru`, and sign in.
4. Enable synchronization and check the status. You can close the popup: background
   code manages the connection and cookies.

The current UI labels are Russian: Account is `Аккаунт`, Server is `Сервер`,
and Enable is `Включить`. The extension currently supports RESO Office only;
cookie domains are fixed to `reso.ru` and its subdomains, with no domain input.

Saved account and connection settings take precedence over defaults. Disable synchronization in the selected
context before editing its fields. Disabling remains available with an invalid URL
or empty account; the toggle reflects the state confirmed by the background process.

Online (`Онлайн`) means successful registration with CookieServer. It does not
confirm that the RESO session is valid or every cookie write is complete: read
the accompanying detail and any error messages.

Pair diagnostics describe the last cookie read in the indicated store and domains.
Missing names, ambiguous selections and expiration problems are reported separately.
Once a valid pair is read, the status immediately changes to Cookies read; sending
to server (`Пара cookies прочитана; отправка на сервер`), before the server replies.
Changing one cookie does not require changing the other simultaneously. Background
rejection diagnostics exclude cookie values. Successfully applying a server pair
also clears an obsolete local-read warning.

### Regular, private and container contexts

Each browser *cookie store* is a separate client with its own settings, WebSocket,
UUID requests, revision, queues and timers. The popup selects the context from
the active tab.

| Context                     | Settings storage                              | Lifetime                          |
|-----------------------------|-----------------------------------------------|-----------------------------------|
| Regular / Firefox container | `storage.local.contextSettings`               | Persists across browser restarts  |
| Private / incognito         | RAM, through `storage.session` when available | Until the last private tab closes |

For independent sessions, set `account_A` in a regular window and `account_B`
in a private window, enabling each separately. First allow the extension to run
in incognito/InPrivate or Firefox private windows. Contexts using the same server
and account intentionally join the same server group.

Several private windows in one profile usually share one cookie store. After the
last private tab closes, a new private session starts with an empty account and
synchronization disabled. Use separate profiles or Firefox containers for
additional independent contexts.

## How synchronization works

### Cookie pair and authentication check

Only **`ASP.NET_SessionId`** and **`ResoOffice60`** for `reso.ru` and its subdomains are
synchronized. A complete, unambiguous pair is required. Domains match exactly
or at a subdomain boundary: `sub.reso.ru` matches `reso.ru`, but `evilreso.ru` does not.
Values and cookie attributes are transferred, including `path`, `secure`, `httpOnly`,
`sameSite`, `hostOnly` and `expirationDate` when present. Local `storeId` is not
included in the server payload.

Before uploading, the client checks authentication in tabs of **the same cookie store**.
The document must no longer be `loading`, and the login dialog
`#clbkAuth_ASPxPopupControl1_loginTitle2` on `office.reso.ru` must be absent or hidden.
This is a DOM heuristic, not a RESO API session check. Legacy `cookieDomain` /
`cookieDomains` settings cannot override the fixed RESO domain. There is a known race when a tab
closes; see [Known limitations](#known-limitations).

### Registration and ordinary updates

1. Enabling a context opens a long-lived WebSocket and sends `register`.
2. If the account is empty, the client attempts to upload its current local pair
   after checking authentication. If the server has a pair, its state is applied
   subject to revision, expiration and any active reauthentication attempt.
3. Local cookie changes use a **1500 ms** debounce. Expected events caused by
   applying server cookies are suppressed to prevent echo loops.
4. Ordinary `set` honors `cookie_update_interval`. A changed pair advances the
   revision and restarts the interval; an identical pair is accepted without a
   write or extension of the interval. A rejected update returns the current server pair.
5. A changed pair is broadcast to other registered clients of the account.
   The sender receives a separate reply to its request.

The client drains the cookie-application queue before reading a local pair.
If the server revision or application queue changes during that read, the snapshot
is discarded, including when `cookie_update_interval = 0`. If either cookie expires,
the entire pair becomes unusable. The server checks it on load and during
`register` / `set` / `refresh`, clearing cookies and cooldown while retaining the
revision. The client rechecks expiration before queued writes and retries.

### Signing in again and recovery

When the login dialog appears, the client pins the known server revision.
When it disappears, a fresh pair is sent with `refresh`, even if cookies changed
before the DOM transition.

- The server compares `expected_revision` under the account lock. Only a match
  bypasses cooldown; adding the field to ordinary `set` does not bypass it.
- The old pair is held back during reauthentication. A newer server revision wins;
  a stale attempt is not automatically rebased onto it.
- The known revision and login observations are stored in `storage.session`
  without cookie values. Restoration checks settings and surviving HTTP and HTTPS
  tabs on `office.reso.ru`.
- Runtime notifications and DOM query replies share a per-context queue.
  Received observations are processed before each cookie write.
- If saving metadata for a completed login fails, the deferred `refresh` retries
  persistence on keepalive or a duplicate observation. Upload resumes after a
  successful save with the original revision. Settings changes, tab departure or
  a winning server revision retire obsolete actions.
- Metadata for the latest **32** timed-out `refresh` requests on the current
  connection is retained for late replies. A reply can complete only its own
  attempt, including an identical pair that does not advance the revision.

Reconnect is scheduled after **5 seconds**. An alarm with a **0.5-minute** period
wakes the background context to restore connections and retry unfinished login-state
persistence. The server's protocol ping runs independently; there is no application
`ping` command.

Critical server operations are serialized under `account.lock`, and file writes
run outside the event loop. Even repeated request cancellation does not release
the lock before the write finishes. Broadcast failure or timeout aborts the
recipient's transport without waiting for a closing handshake under the account lock.

## WebSocket protocol

Messages are JSON in text frames. Every request has a `uuid`, and the reply echoes
that exact value. A server push uses `command: "set"` and does not require a UUID.
`result: true` means the request was processed; `accepted: false` on an update
means it was rejected because of cooldown or a revision conflict.

| Command    | Purpose                                                                                                   |
|------------|-----------------------------------------------------------------------------------------------------------|
| `register` | Get or create the account, register the connection, return cookies, revision and `retry_after`            |
| `set`      | Update a complete pair while honoring the interval; requires registration in the account                  |
| `refresh`  | Conditionally replace the pair after login; requires registration and an integer `expected_revision >= 0` |

Example reauthentication request:

```json
{
  "command": "refresh",
  "account": "office_team",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "expected_revision": 12,
  "payload": [
    {
      "name": "ASP.NET_SessionId",
      "value": "new-session",
      "domain": ".reso.ru",
      "path": "/"
    },
    {
      "name": "ResoOffice60",
      "value": "new-office",
      "domain": ".reso.ru",
      "path": "/"
    }
  ]
}
```

The reply includes `result`, `message`, the same `uuid`, `payload`, `accepted`,
`revision` and `retry_after` in seconds. A conflict returns the current account data.

## Building the extension

The [builder](build_extension.py) uses Python's standard library and reads the
version from `extension/manifest.json`, not the root `VERSION` file. It generates
browser-specific manifests. Archives contain extension files and instructions,
excluding the server, accounts, TLS keys and tests. ZIPs are reproducible for
identical sources; `SHA256SUMS` is written alongside them.

### Local build

```bash
python3 build_extension.py
# Equivalent Makefile target:
make build-extension
```

Results in `build/`:

- `CookieSync-1.2.2-chromium.zip` — unpacked installation in Chrome / Chromium / Edge;
- `CookieSync-1.2.2-firefox.zip` — temporary installation in Firefox 121+;
- `SHA256SUMS`.

### Release candidates

After installing test dependencies:

```bash
make release-extension
```

This runs tests and creates the following in `build/release/`:

- `CookieSync-1.2.2-chrome.zip`;
- `CookieSync-1.2.2-firefox-unsigned.zip` — Firefox 140+, declares `authenticationInfo` transmission;
- `SHA256SUMS`.

Running `python3 build_extension.py --release` directly only packages the extension;
it does not run tests. `--output <directory>` changes the base output directory.
Every ZIP contains `INSTALL.txt` (English) and `INSTALL.ru.txt` (Russian). Release builds use
[INSTALL_RELEASE.txt](extension/INSTALL_RELEASE.txt) and
[INSTALL_RELEASE.ru.txt](extension/INSTALL_RELEASE.ru.txt) under those same archive names.
Signing, publication, secure data-transmission configuration and updates are covered
in [RELEASE.md](RELEASE.md).

## Development and checks

Install development dependencies into the existing virtual environment:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
make test
```

`make test` runs pytest for the server and builder, then Node's built-in test runner
for the extension. TLS tests require `openssl`. Individual checks:

```bash
make test-server
make test-extension
# Without make, from the project root:
.venv/bin/python -m pytest -q cookieserver/tests tests
node --test
```

The Makefile automatically uses `.venv/bin/python` when available. To override it,
use `make test PYTHON=/path/to/python`. Start the server manually with
`make run_server ARGS=--no-tls`; without `ARGS`, TLS is enabled.

For sources at commit `dd840a5`, **119 Python and 167 JavaScript tests** passed.
Client race tests use a VM with controlled browser APIs. Memory-release checks also
run Node/V8 with forced garbage collection. Passing tests do not cover every real
browser scenario; confirmed open issues are listed below.

## Known limitations

The audit of `dd840a5` confirmed the following **unfixed** issues:

1. **Stale authentication confirmation after a tab closes.** If the last RESO Office
   tab that confirmed login closes or navigates to another site while cookies are
   being read, ordinary `set` can still be sent using its previous confirmation.
   Revision and cookie-queue checks do not eliminate this race.
2. **Ordinary `set` lost after a metadata persistence error.** If authentication
   checking first observes a new document and saving it to `storage.session` fails,
   the current upload can be lost. Storage recovery clears the error but does not
   automatically resume ordinary `set`. The fixed `refresh` retry after completing
   a new login is a different scenario.

Both cases were reproduced in Node/VM. They concern `isAuthenticated()`,
`syncCookies()` and observation persistence in `sync-context.js`.

## Updating

1. Stop the server, preserve accounts, configuration and keys, and update code and dependencies.
2. Start it with the previous TLS mode and verify connectivity.
3. Build and install the extension from current sources, reload open `office.reso.ru`
   tabs, and check each context's settings.

Update the server first: older versions without `refresh` do not support revision-based
reauthentication. For the next release, increase the manifest version as described
in the [release guide](RELEASE.md).

When upgrading from **1.0.4**, close all private windows first to clear the old
shared session. Legacy flat settings migrate only into the regular cookie store;
configure the private account again.

## Project layout

```text
cookieserver/manage.py          Server CLI
cookieserver/src/               Protocol, commands, WebSocket server and storage
cookieserver/tests/             Server integration tests and async client
extension/background.js        Cookie-store context and browser-event manager
extension/sync-context.js       Per-context connection, revisions, queues and reauthentication
extension/authentication.js     RESO Office login-dialog observation
extension/logic.js              Browser-independent helpers
extension/popup.js              Settings and status UI
extension/tests/                Extension Node tests
build_extension.py             Reproducible browser packaging
tests/test_build_extension.py   Package contents and reproducibility checks
```

## License

This project is proprietary; use requires permission from the copyright holder.
See [LICENSE](LICENSE). The included `webextension-polyfill` version 0.12.0 is
distributed under MPL-2.0; details are in [RELEASE.md](RELEASE.md).
