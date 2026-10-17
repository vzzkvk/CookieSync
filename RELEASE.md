# Releasing CookieSync for Chrome and Firefox

**English** | [Русский](RELEASE.ru.md)

## Build the packages

You need Python 3.11+ and Node.js 18+ for tests. From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
make release-extension
```

This runs all server and client tests before packaging. Results in `build/release/`:

- `CookieSync-1.2.2-chrome.zip` — Chrome package;
- `CookieSync-1.2.2-firefox-unsigned.zip` — **unsigned** Firefox package;
- `SHA256SUMS` — checksums for those archives.

Each ZIP contains only extension files and `INSTALL.txt` (English) / `INSTALL.ru.txt` (Russian).
Release builds use the respective `INSTALL_RELEASE.txt` / `INSTALL_RELEASE.ru.txt`
sources. `manifest.json` is at the archive root. The server, accounts, TLS keys,
tests and developer settings are excluded. Own JavaScript sources are not minified
and are available for review. Rebuilding identical sources produces identical ZIPs.

A normal build (`python3 build_extension.py`) keeps the Firefox minimum at 121.
A release build requires Firefox 140+ to support the built-in `authenticationInfo`
data-transmission notice. The Firefox ID remains `cookiesync@extension`.

Version 1.2.0 uses the server command `refresh` with `expected_revision` for a new
sign-in. Update `cookieserver/src` and restart the server first, then update the
extensions and RESO Office tabs. Ordinary `register` and `set` remain compatible
with previous clients.

In 1.2.1, ordinary `set` also requires registration in its target account; standard
extensions already comply. Expired-cookie cleanup preserves the last accepted
revision. These fixes require a server update.

Version 1.2.2 fixes private-context restoration at worker startup, ownership of
repeated `refresh` attempts after reconnect, and disabling with an invalid URL.
The server write helper now withstands repeated task cancellation; update
`cookieserver/src/storage.py` and `cookieserver/src/commands.py` together.

## Current address and permissions

Default address: **`ws://mnas:52314`**. Plain `ws://` support is retained for the
internal network; `wss://` is also supported. Updates preserve user-saved settings.

The current manifest uses `host_permissions: ["*://*/*"]` for configurable cookie
domains and server addresses. The content-script match pattern is `*://*.reso.ru/*`;
`*://.reso.ru` is not a valid pattern. Authentication is checked only on
`office.reso.ru`. The background handler no longer logs WebSocket cookie payloads
to the console.

**Current build status:** these are locally tested release candidates, not already
published or signed add-ons. Store publication/signing requires secure transmission
of user data. Sending session cookies over `ws://` does not meet that requirement.
Before submitting for review, make `wss://` mandatory on both server and client,
including rejecting `ws://` in settings/background logic. Renaming a ZIP to XPI
or CRX does not address this.

## Chrome: permanent installation through the store

1. Register a publisher account in
   the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/).
2. After preparing the secure configuration, upload the Chrome ZIP using **Add new item**.
3. Provide the description, purpose, data-handling details and permissions.
   You can use `extension/icon128.png` as the icon. Take UI screenshots without
   real cookies or accounts.
4. Provide a public privacy policy and a support contact. The data description
   below can serve as a starting point, completed with the actual server operator
   and retention details.
5. For link-based distribution, choose **Unlisted** if available for your account.
   It also requires review.
6. Give reviewers a working test server and testing instructions.
7. After approval, distribute the extension link to users.

A self-packaged CRX does not provide a normal off-store installation on Chrome
for Windows/macOS. Managed devices can use enterprise deployment policies,
configured by the organization's administrator.

## Firefox: signing for direct distribution

1. Sign in to [Mozilla Developer Hub](https://addons.mozilla.org/developers/).
2. Submit a new add-on and select **On your own** / unlisted distribution
   if you do not need a public listing.
3. Upload the Firefox ZIP after preparing the secure configuration.
4. Provide data-transmission information, contacts and testing instructions.
   The release manifest already declares `authenticationInfo`; do not replace it with `none`.
5. After successful review, download the **signed `.xpi`** and distribute it.
   Users can install it through `about:addons` → gear menu → Install Add-on From File
   without debugging mode.

Keep the same `gecko.id` across updates. Mozilla checks its uniqueness on the first
release. If another publisher already uses that ID, choose your own permanent ID
before the first publication.

Automatic updates for an unlisted XPI require a separate HTTPS update manifest
and `gecko.update_url`; none is configured currently. New signed XPIs can be
distributed manually. Publishing on AMO provides updates through AMO.

## Data and permissions: release-description information

Actual client behavior:

- Sends `ASP.NET_SessionId` and `ResoOffice60`, their attributes, and the account
  name to the user-selected server. Other clients of the same account receive
  these cookies from the server.
- Regular/container settings (account name, server URL, cookie domains and enabled
  flag) are stored per cookie store in `storage.local.contextSettings`. Private
  settings remain in RAM through `storage.session` and are removed after the last
  private window closes. Contexts do not inherit each other's accounts and use
  separate WebSocket connections.
- Page contents are not sent. The script checks login-dialog visibility on
  `office.reso.ru` and returns a boolean result.
- `cookies` reads/applies the pair; `storage` saves settings; `alarms` restores
  connections; `scripting` checks authentication in tabs opened before installation.
  Access to `reso.ru` is needed for cookies and the script; access to `mnas`
  is used for connection diagnostics.
- There is no built-in analytics or advertising traffic. The server stores cookies
  in JSON files; accounts currently have no automatic deletion period.

The publisher must complete the public policy with their actual identity,
contacts, storage/deletion terms and server-access details. Do not claim that
data is never transmitted: cookie transmission is the main feature.

Included third-party library: webextension-polyfill 0.12.0, MPL-2.0,
[source](https://github.com/mozilla/webextension-polyfill/tree/0.12.0).
Own extension files are shipped without obfuscation.

## Validate before uploading

For a local Firefox ZIP check, extract it and run Mozilla web-ext:

```bash
python3 -m zipfile -e build/release/CookieSync-1.2.2-firefox-unsigned.zip build/firefox-review
npx --yes web-ext@10.7.0 lint --source-dir build/firefox-review
```

Linting checks the package but does not replace review or signing. The builder
does not access Google/Mozilla accounts or publish packages automatically.

For the next release, increase `version` in `extension/manifest.json`, run tests
and build the packages, then update the existing publisher listing.
