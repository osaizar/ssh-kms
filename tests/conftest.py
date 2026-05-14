import json
import sys
from pathlib import Path

import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    """Create a temporary SSH key config and point storage at it."""
    path = tmp_path / "ssh-keys.json"
    path.write_text(json.dumps([
        {
            "id": "key_alice",
            "user": "alice",
            "hostname": "host-a",
            "ssh-key": "ssh-ed25519 AAAA alice",
        },
        {
            "id": "key_ops",
            "user": "ops",
            "hostname_regex": "lab-.+",
            "ssh-key": "ssh-ed25519 BBBB ops",
        },
    ]), encoding="utf-8")

    from ssh_kms import storage

    monkeypatch.setattr(storage, "KEY_FILE", str(path))
    return path


@pytest.fixture
def client_template(tmp_path, monkeypatch):
    """Create a temporary client template used by the /get_client route."""
    path = tmp_path / "get-ssh-keys.py"
    path.write_text('URL = "{URL}"\n', encoding="utf-8")

    from ssh_kms import routes

    monkeypatch.setattr(routes, "CLIENT_FILE", str(path))
    return path
