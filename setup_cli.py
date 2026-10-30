"""Local setup diagnostics. Never prints credentials or overwrites Claude settings."""
import json
import sys
from pathlib import Path
from auth import client_id, FikenError


def claude_config():
    executable = Path(sys.executable).parent / ('fiken-mcp.exe' if sys.platform == 'win32' else 'fiken-mcp')
    if not executable.is_file():
        raise FikenError('Installer pakken først med python -m pip install .')
    return {'mcpServers': {'fiken': {'command': str(executable), 'args': ['serve'],
                                    'env': {'FIKEN_CLIENT_ID': client_id()}}}}


def doctor():
    if sys.platform not in {'darwin', 'win32'}:
        raise FikenError('Denne piloten krever macOS eller Windows.')
    client_id()
    from client import get
    # Uses the same refresh, keychain and read-only transport as Claude.
    result = get('companies', {'page': 0, 'pageSize': 1})
    count = result['pagination']['result_count']
    return {'status': 'ok', 'oauth_and_api': 'ok', 'accessible_company_count': count,
            'has_accessible_company': bool(result['data']),
            'note': 'Ingen tokens eller foretaksdata vises. Claude-oppsettet må fortsatt prøves i Claude.'}


def print_result(command):
    print(json.dumps(claude_config() if command == 'config' else doctor(), ensure_ascii=False, indent=2))
