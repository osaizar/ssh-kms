import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import (
    OIDC_ADMIN_ROLE,
    OIDC_ALGORITHMS,
    OIDC_CLIENT_ID,
    OIDC_ENABLED,
    OIDC_ISSUER,
    OIDC_JWKS_URL,
    OIDC_VIEWER_ROLE,
)


bearer_scheme = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient(OIDC_JWKS_URL) if OIDC_ENABLED else None


def unauthorized(detail="Authentication required"):
    """Raise a standards-compatible Bearer authentication error."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def token_roles(payload):
    """Extract realm and client roles from a decoded Keycloak access token."""
    roles = set(payload.get("realm_access", {}).get("roles", []))
    resource_access = payload.get("resource_access", {})

    if OIDC_CLIENT_ID in resource_access:
        roles.update(resource_access[OIDC_CLIENT_ID].get("roles", []))

    return roles


def token_client_is_allowed(payload):
    """Check that the token was issued for or by the configured frontend client."""
    if not OIDC_CLIENT_ID:
        return True

    audience = payload.get("aud", [])
    if isinstance(audience, str):
        audience = [audience]

    return OIDC_CLIENT_ID in audience or payload.get("azp") == OIDC_CLIENT_ID


def decode_access_token(token):
    """Validate a Keycloak access token and return its decoded claims."""
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=OIDC_ALGORITHMS,
            issuer=OIDC_ISSUER,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as e:
        print(e)
        unauthorized("Invalid access token")

    if not token_client_is_allowed(payload):
        unauthorized("Token client is not allowed")

    return payload


def current_username(user):
    """Return the best display identifier from a validated user token."""
    if not isinstance(user, dict):
        return "unknown"

    return user.get("preferred_username") or user.get("email") or user.get("sub") or "unknown"


async def require_authenticated(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Return the current user claims after validating OIDC authentication."""
    if not OIDC_ENABLED:
        return {
            "preferred_username": "local-dev",
            "realm_access": {"roles": [OIDC_VIEWER_ROLE, OIDC_ADMIN_ROLE]},
        }

    if credentials is None or credentials.scheme.lower() != "bearer":
        unauthorized()

    return decode_access_token(credentials.credentials)


def require_role(role):
    """Build a FastAPI dependency that requires a Keycloak role."""
    async def role_checker(user=Depends(require_authenticated)):
        """Validate that the authenticated user has the required role."""
        roles = token_roles(user)
        role_allowed = role in roles
        viewer_allowed = role == OIDC_VIEWER_ROLE and OIDC_ADMIN_ROLE in roles

        if not role_allowed and not viewer_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

        return user

    return role_checker
