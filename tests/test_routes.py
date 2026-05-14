import asyncio
import json

import pytest
from fastapi import HTTPException

from ssh_kms.models import KeyEntry
from ssh_kms.routes import create_key, delete_key, export_keys, get_client, get_keys, list_keys


class FakeBaseRequest:
    base_url = "http://testserver/"


class FakeJsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        """Return the fake JSON request payload."""
        return self.payload


def test_get_client_embeds_server_url(key_file, client_template):
    """Serve the client template with the request base URL embedded."""
    response = asyncio.run(get_client(FakeBaseRequest()))

    assert 'URL = "http://testserver/"' in response


def test_lookup_endpoint_returns_matching_keys(key_file):
    """Return only SSH keys matching the requested user and hostname."""
    response = asyncio.run(get_keys(FakeJsonRequest({"user": "ops", "hostname": "lab-22"})))

    assert response == {"ssh-keys": ["ssh-ed25519 BBBB ops"]}


def test_lookup_endpoint_rejects_invalid_request(key_file):
    """Reject lookup requests without string user and hostname values."""
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_keys(FakeJsonRequest({"user": "ops"})))

    assert exc_info.value.status_code == 400


def test_management_endpoints_list_create_delete_and_export_keys(key_file):
    """Exercise the JSON management API against an isolated key file."""
    actor = {"preferred_username": "tester"}

    list_response = asyncio.run(list_keys())
    keys = list_response["keys"]
    existing_id = keys[0]["id"]
    assert existing_id == "key_alice"

    created_key = asyncio.run(create_key(
        KeyEntry(user="bob", hostname="host-b", ssh_key="ssh-ed25519 CCCC bob"),
        actor,
    ))
    assert created_key["id"].startswith("key_")
    assert created_key["user"] == "bob"

    export_response = asyncio.run(export_keys())
    assert export_response.media_type == "application/json"
    assert "attachment;" in export_response.headers["content-disposition"]
    assert any(key["id"] == created_key["id"] for key in json.loads(export_response.body))

    deleted_key = asyncio.run(delete_key(existing_id, actor))
    assert deleted_key["id"] == existing_id

    remaining = json.loads(key_file.read_text(encoding="utf-8"))
    assert all(key["id"] != existing_id for key in remaining)


def test_delete_missing_key_returns_404(key_file):
    """Return a 404 when deleting an unknown stable ID."""
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(delete_key("key_missing", {"preferred_username": "tester"}))

    assert exc_info.value.status_code == 404
