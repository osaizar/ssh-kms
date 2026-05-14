import importlib.util
from pathlib import Path

import pytest


CLIENT_PATH = Path(__file__).resolve().parents[1] / "client" / "get-ssh-keys.py"


def load_client_module():
    """Load the standalone SSH client script as a Python module."""
    spec = importlib.util.spec_from_file_location("get_ssh_keys_client", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        """Return the fake response payload."""
        return self._payload


def test_get_ssh_keys_prints_returned_keys(monkeypatch, capsys):
    """Fetch and print keys returned by the SSH KMS server."""
    module = load_client_module()

    monkeypatch.setattr(module.os, "uname", lambda: ("Linux", "host-a", "", "", ""))
    monkeypatch.setattr(
        module.requests,
        "post",
        lambda url, json: FakeResponse(200, {"ssh-keys": ["ssh-ed25519 AAAA alice"]}),
    )

    with pytest.raises(SystemExit) as exc_info:
        module.get_ssh_keys("alice")

    assert exc_info.value.code == 0
    assert "ssh-ed25519 AAAA alice" in capsys.readouterr().out


def test_get_ssh_keys_exits_nonzero_on_server_error(monkeypatch):
    """Exit with failure when the server does not return HTTP 200."""
    module = load_client_module()

    monkeypatch.setattr(module.os, "uname", lambda: ("Linux", "host-a", "", "", ""))
    monkeypatch.setattr(module.requests, "post", lambda url, json: FakeResponse(500, {}))

    with pytest.raises(SystemExit) as exc_info:
        module.get_ssh_keys("alice")

    assert exc_info.value.code == 1


def test_print_help_outputs_supported_usage(capsys):
    """Print CLI usage for unsupported invocation."""
    module = load_client_module()

    module.print_help()

    assert "--get-key <username>" in capsys.readouterr().out
