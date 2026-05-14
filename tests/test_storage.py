import errno
import json
import os

import pytest

from ssh_kms import storage
from ssh_kms.models import KeyEntry


def test_read_key_json_requires_ids(key_file):
    """Reject config entries that do not have stable IDs."""
    key_file.write_text(json.dumps([
        {"user": "alice", "hostname": "host-a", "ssh-key": "ssh-ed25519 AAAA"},
    ]), encoding="utf-8")

    with pytest.raises(Exception, match="Key file format"):
        storage.read_key_json()


def test_filter_keys_matches_exact_and_regex_hosts(key_file):
    """Filter keys by exact users and exact or regex hostnames."""
    assert [key["ssh-key"] for key in storage.filter_keys("alice", "host-a")] == ["ssh-ed25519 AAAA alice"]
    assert [key["ssh-key"] for key in storage.filter_keys("ops", "lab-01")] == ["ssh-ed25519 BBBB ops"]
    assert storage.filter_keys("ops", "prod-01") == []
    assert storage.filter_keys("root", "host-a") == []


def test_api_key_to_config_key_trims_values_and_generates_id():
    """Convert API input into the persisted JSON format."""
    config_key = storage.api_key_to_config_key(
        KeyEntry(user=" alice ", hostname=" host-a ", ssh_key=" ssh-ed25519 AAAA "),
        existing_ids=set(),
    )

    assert config_key["id"].startswith("key_")
    assert config_key["user"] == "alice"
    assert config_key["hostname"] == "host-a"
    assert config_key["ssh-key"] == "ssh-ed25519 AAAA"


def test_read_key_json_rejects_duplicate_ids(key_file):
    """Reject config files that reuse the same stable ID."""
    key_file.write_text(json.dumps([
        {"id": "key_dup", "user": "alice", "hostname": "host-a", "ssh-key": "ssh-ed25519 AAAA"},
        {"id": "key_dup", "user": "bob", "hostname": "host-b", "ssh-key": "ssh-ed25519 BBBB"},
    ]), encoding="utf-8")

    with pytest.raises(Exception, match="duplicated"):
        storage.read_key_json()


def test_read_key_json_rejects_unknown_fields(key_file):
    """Reject config entries that contain unsupported fields."""
    key_file.write_text(json.dumps([
        {
            "id": "key_alice",
            "user": "alice",
            "hostname": "host-a",
            "ssh-key": "ssh-ed25519 AAAA",
            "unexpected": "value",
        }
    ]), encoding="utf-8")

    with pytest.raises(Exception, match="Key file format"):
        storage.read_key_json()


def test_write_key_json_uses_readable_field_order(key_file):
    """Persist key entries with stable field order."""
    storage.write_key_json([
        {
            "ssh-key": "ssh-ed25519 AAAA",
            "hostname": "host-a",
            "user": "alice",
            "id": "key_alice",
        }
    ])

    persisted_key = json.loads(key_file.read_text(encoding="utf-8"))[0]
    assert list(persisted_key) == ["id", "user", "hostname", "ssh-key"]
    assert persisted_key["id"] == "key_alice"


def test_write_key_json_falls_back_for_busy_bind_mount(key_file, monkeypatch):
    """Rewrite the target file when Docker refuses rename over a file mount."""
    def busy_replace(_source, _target):
        raise OSError(errno.EBUSY, os.strerror(errno.EBUSY))

    monkeypatch.setattr(storage.os, "replace", busy_replace)

    storage.write_key_json([
        {
            "id": "key_bob",
            "user": "bob",
            "hostname": "host-b",
            "ssh-key": "ssh-ed25519 BBBB",
        }
    ])

    persisted = json.loads(key_file.read_text(encoding="utf-8"))
    assert persisted[0]["id"] == "key_bob"
    assert not key_file.with_suffix(".json.tmp").exists()
