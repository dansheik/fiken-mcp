import sys
import types
from pathlib import Path
import auth
import setup_cli


def test_windows_data_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(auth.sys, 'platform', 'win32')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert auth.session_directory() == tmp_path / 'fiken-mcp'


def test_windows_config_uses_exe(monkeypatch, tmp_path):
    executable = tmp_path / 'fiken-mcp.exe'
    executable.touch()
    monkeypatch.setattr(setup_cli.sys, 'platform', 'win32')
    monkeypatch.setattr(setup_cli.sys, 'executable', str(tmp_path / 'python.exe'))
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-id')
    assert setup_cli.claude_config()['mcpServers']['fiken']['command'] == str(executable)


def test_windows_uses_native_vault(monkeypatch):
    sentinel = object()
    module = types.ModuleType('keyring.backends.Windows')
    module.WinVaultKeyring = lambda: sentinel
    monkeypatch.setitem(sys.modules, 'keyring.backends.Windows', module)
    monkeypatch.setattr(auth.sys, 'platform', 'win32')
    assert auth.keychain() is sentinel


def test_lock_serializes_processes(tmp_path):
    import subprocess
    import portalocker
    lockfile = tmp_path / 'session.lock'
    with portalocker.Lock(str(lockfile), mode='a', timeout=1):
        result = subprocess.run([sys.executable, '-c',
            'import sys, portalocker\n'
            'try:\n'
            '    with portalocker.Lock(sys.argv[1], mode="a", timeout=0.1): pass\n'
            'except portalocker.exceptions.LockException: sys.exit(0)\n'
            'sys.exit(1)', str(lockfile)], capture_output=True, timeout=5)
        assert result.returncode == 0, result.stderr.decode()
    with portalocker.Lock(str(lockfile), mode='a', timeout=1):
        pass
