import asyncio

import pytest
from fastapi import HTTPException

from ssh_kms.auth import current_username, require_role, token_client_is_allowed, token_roles
from ssh_kms.config import OIDC_ADMIN_ROLE, OIDC_CLIENT_ID, OIDC_VIEWER_ROLE


def test_token_roles_combines_realm_and_client_roles():
    """Read roles from both realm_access and resource_access claims."""
    roles = token_roles({
        "realm_access": {"roles": ["viewer"]},
        "resource_access": {OIDC_CLIENT_ID: {"roles": ["key-admin"]}},
    })

    assert roles == {"viewer", "key-admin"}


def test_token_client_is_allowed_by_audience_or_authorized_party():
    """Accept tokens addressed to the configured frontend client."""
    assert token_client_is_allowed({"aud": [OIDC_CLIENT_ID]})
    assert token_client_is_allowed({"azp": OIDC_CLIENT_ID})
    assert not token_client_is_allowed({"aud": ["other-client"], "azp": "other-client"})


def test_require_role_allows_admin_for_viewer():
    """Allow key-admin users to satisfy viewer-only endpoints."""
    checker = require_role(OIDC_VIEWER_ROLE)
    user = {"realm_access": {"roles": [OIDC_ADMIN_ROLE]}}

    assert asyncio.run(checker(user=user)) == user


def test_require_role_rejects_missing_role():
    """Reject authenticated users that do not have the required role."""
    checker = require_role(OIDC_ADMIN_ROLE)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(checker(user={"realm_access": {"roles": [OIDC_VIEWER_ROLE]}}))

    assert exc_info.value.status_code == 403


def test_current_username_prefers_human_readable_claims():
    """Choose a stable display name from common OIDC claims."""
    assert current_username({"preferred_username": "alice", "sub": "123"}) == "alice"
    assert current_username({"email": "alice@example.test", "sub": "123"}) == "alice@example.test"
    assert current_username({"sub": "123"}) == "123"
    assert current_username(None) == "unknown"
