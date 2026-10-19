"""Exercise the installer in temporary directories without touching host services."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'cookieserver/install.sh'
UNIT = ROOT / 'cookieserver/resoserver.service'
pytestmark = pytest.mark.skipif(
    sys.platform != 'linux' or not shutil.which('bash') or not shutil.which('install'),
    reason='The installer requires Linux, Bash and GNU install',
)


@pytest.fixture
def installer(tmp_path):
    """Redirect only fixed filesystem roots/root identity; fake privileged commands.

    GNU install and Bash execute normally inside the temporary tree. systemctl
    and Python preflight are stubs; no service or OS account is changed.
    """
    project = tmp_path / 'project'
    units = tmp_path / 'systemd-units'
    runtime = tmp_path / 'systemd-runtime'
    source = tmp_path / 'installer source'
    bin_dir = tmp_path / 'bin'
    for directory in [project / '.venv/bin', project / 'cookieserver', units, runtime, source, bin_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    calls = tmp_path / 'calls.txt'
    script = source / 'install.sh'
    text = SCRIPT.read_text()
    substitutions = {
        'PROJECT=/opt/CookieSync': f'PROJECT={shlex.quote(str(project))}',
        '/etc/systemd/system': str(units),
        '/run/systemd/system': str(runtime),
        '$EUID': '${TEST_EUID:-0}',
    }
    for old, new in substitutions.items():
        assert old in text, f'Update the installer sandbox mapping for {old}'
        text = text.replace(old, new)
    script.write_text(text)
    template = source / 'resoserver.service'
    template.write_text(UNIT.read_text().replace('/opt/CookieSync', str(project)))
    manager = project / 'cookieserver/manage.py'
    manager.write_text('# Preflight imports are simulated by the fake interpreter.\n')
    config = project / 'cookieserver/server_config.conf'
    config.write_text('[server]\nport = 52314\n')
    python = project / '.venv/bin/python'
    python.write_text('#!/bin/bash\nprintf "python %s\\n" "$*" >> "$CALLS"\nexit "${CHECK_STATUS:-0}"\n')
    python.chmod(0o755)
    systemctl = bin_dir / 'systemctl'
    systemctl.write_text(
        '#!/bin/bash\nprintf "systemctl %s\\n" "$*" >> "$CALLS"\n'
        'if [[ "${SYSTEMCTL_FAIL:-}" == "$1" ]]; then exit 1; fi\nexit 0\n'
    )
    systemctl.chmod(0o755)
    for command in ['useradd', 'groupadd', 'userdel', 'groupdel', 'chown']:
        blocked = bin_dir / command
        blocked.write_text('#!/bin/bash\nprintf "FORBIDDEN %s\\n" "$0" >> "$CALLS"\nexit 99\n')
        blocked.chmod(0o755)

    def run(*args, **env):
        """Run the sandboxed installer with optional simulated failures."""
        return subprocess.run(
            ['bash', str(script), *args], cwd=tmp_path, text=True, capture_output=True, timeout=10,
            env={**os.environ, 'PATH': f'{bin_dir}{os.pathsep}{os.environ.get("PATH", "")}',
                 'CALLS': str(calls), 'TEST_EUID': '0', 'CHECK_STATUS': '0', 'SYSTEMCTL_FAIL': '', **env},
        )

    return {'run': run, 'project': project, 'units': units, 'runtime': runtime,
            'python': python, 'manager': manager, 'config': config, 'template': template, 'calls': calls}


@pytest.mark.parametrize('mode', ['', '--tls', '--no-tls'])
def test_installer_writes_unit_and_preserves_accounts_and_custom_dropins(installer, mode):
    accounts = installer['project'] / 'cookieserver/accounts'
    accounts.mkdir(mode=0o750)
    account = accounts / 'existing.json'
    account.write_text('{"payload": [], "revision": 7}')
    unit = installer['units'] / 'cookiesync.service'
    unit.write_text('previous unit\n')
    overrides = installer['units'] / 'cookiesync.service.d'
    overrides.mkdir()
    custom = overrides / 'custom.conf'
    custom.write_text('[Service]\nEnvironment=KEEP_ME=1\n')
    transport = overrides / 'cookiesync-transport.conf'
    previous = '[Service]\nExecStart=\nExecStart=/existing/python --no-tls\n'
    transport.write_text(previous)
    result = installer['run'](*([mode] if mode else []))
    assert result.returncode == 0, result.stderr
    assert unit.read_bytes() == installer['template'].read_bytes()
    assert 'User=' not in unit.read_text() and 'Group=' not in unit.read_text()
    assert (installer['units'] / 'cookiesync.service.~1~').read_text() == 'previous unit\n'
    assert account.read_text() == '{"payload": [], "revision": 7}'
    assert accounts.stat().st_mode & 0o777 == 0o750
    assert custom.read_text() == '[Service]\nEnvironment=KEEP_ME=1\n'
    if mode:
        extra = ' --no-tls' if mode == '--no-tls' else ''
        assert transport.read_text() == (
            f'[Service]\nExecStart=\nExecStart={installer["python"]} -m cookieserver.manage runserver{extra}\n'
        )
    else:
        assert transport.read_text() == previous
    assert installer['calls'].read_text().splitlines() == [
        'python -m cookieserver.manage --help', 'systemctl daemon-reload',
        'systemctl enable cookiesync.service', 'systemctl restart cookiesync.service',
        'systemctl status cookiesync.service --no-pager',
    ]


def test_installer_creates_missing_accounts_directory(installer):
    result = installer['run']('--no-tls')
    assert result.returncode == 0, result.stderr
    accounts = installer['project'] / 'cookieserver/accounts'
    assert accounts.is_dir()
    assert accounts.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize('missing', ['python', 'manager', 'config', 'template'])
def test_missing_prerequisites_do_not_modify_service(installer, missing):
    installer[missing].unlink()
    result = installer['run']('--no-tls')
    assert result.returncode == 1
    assert not (installer['units'] / 'cookiesync.service').exists()
    assert not installer['calls'].exists()


@pytest.mark.parametrize('condition', ['not-root', 'no-systemd', 'preflight-failed'])
def test_preflight_failures_stop_before_installation(installer, condition):
    env = {}
    if condition == 'not-root':
        env['TEST_EUID'] = '1000'
    elif condition == 'no-systemd':
        installer['runtime'].rmdir()
    else:
        env['CHECK_STATUS'] = '1'
    result = installer['run']('--no-tls', **env)
    assert result.returncode == 1
    assert not (installer['units'] / 'cookiesync.service').exists()
    assert not (installer['project'] / 'cookieserver/accounts').exists()
    if installer['calls'].exists():
        assert 'systemctl' not in installer['calls'].read_text()


@pytest.mark.parametrize('command', ['restart', 'status'])
def test_service_failure_reports_journal_command(installer, command):
    result = installer['run']('--no-tls', SYSTEMCTL_FAIL=command)
    assert result.returncode == 1
    assert 'journalctl -u cookiesync.service' in result.stderr


@pytest.mark.parametrize('args, exit_code', [(['--help'], 0), (['--invalid'], 2), (['--tls', '--no-tls'], 2)])
def test_real_script_help_and_argument_validation_are_read_only(args, exit_code):
    result = subprocess.run(['bash', str(SCRIPT), *args], text=True, capture_output=True, timeout=5)
    assert result.returncode == exit_code
    assert 'Usage:' in result.stdout + result.stderr
