import pytest
from pydantic import ValidationError

from ssh_kms.models import KeyEntry


def test_key_entry_accepts_exact_hostname():
    """Validate an entry with an exact hostname matcher."""
    entry = KeyEntry(user="alice", hostname="host-a", ssh_key="ssh-ed25519 AAAA")

    assert entry.user == "alice"
    assert entry.hostname == "host-a"


def test_key_entry_requires_one_host_matcher():
    """Reject entries without exactly one host matcher."""
    with pytest.raises(ValidationError, match="Provide exactly one"):
        KeyEntry(user="alice", hostname="host-a", hostname_regex="host-.+", ssh_key="ssh-ed25519 AAAA")

    with pytest.raises(ValidationError, match="Provide exactly one"):
        KeyEntry(user="alice", ssh_key="ssh-ed25519 AAAA")


def test_key_entry_rejects_empty_values():
    """Reject whitespace-only user, host, and key values."""
    with pytest.raises(ValidationError, match="user cannot be empty"):
        KeyEntry(user=" ", hostname="host-a", ssh_key="ssh-ed25519 AAAA")

    with pytest.raises(ValidationError, match="hostname cannot be empty"):
        KeyEntry(user="alice", hostname=" ", ssh_key="ssh-ed25519 AAAA")

    with pytest.raises(ValidationError, match="ssh_key cannot be empty"):
        KeyEntry(user="alice", hostname="host-a", ssh_key=" ")


def test_key_entry_rejects_invalid_hostname_regex():
    """Reject invalid Python regex syntax for hostname_regex."""
    with pytest.raises(ValidationError):
        KeyEntry(user="alice", hostname_regex="[", ssh_key="ssh-ed25519 AAAA")
