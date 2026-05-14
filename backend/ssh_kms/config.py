import os
import re
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
PROJECT_DIR = Path(os.environ.get("SSH_KMS_PROJECT_DIR", str(BACKEND_DIR.parent))).resolve()

KEY_FILE = os.environ.get("SSH_KMS_KEY_FILE", str(PROJECT_DIR / "config/ssh-keys.json"))
CLIENT_FILE = os.environ.get("SSH_KMS_CLIENT_FILE", str(PROJECT_DIR / "client/get-ssh-keys.py"))
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

OIDC_ENABLED = os.environ.get("OIDC_ENABLED", "false").lower() in ("1", "true", "yes")
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "http://localhost:8080/realms/ssh-kms")
OIDC_JWKS_URL = os.environ.get("OIDC_JWKS_URL", f"{OIDC_ISSUER}/protocol/openid-connect/certs")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "ssh-kms-ui")
OIDC_VIEWER_ROLE = os.environ.get("OIDC_VIEWER_ROLE", "viewer")
OIDC_ADMIN_ROLE = os.environ.get("OIDC_ADMIN_ROLE", "key-admin")
OIDC_ALGORITHMS = [
    algorithm.strip()
    for algorithm in os.environ.get("OIDC_ALGORITHMS", "RS256").split(",")
    if algorithm.strip()
]

KEY_FORMAT = """
[
    {"id" : "key_...", "user" : "", "hostname" : "", "ssh-key" : "..", }, # For exact user and exact host
    {"id" : "key_...", "user" : "", "hostname_regex" : "", "ssh-key" : "..", } # For exact user and regex host
]
# The id is generated automatically by the API for UI-created entries and is required in JSON
# The hostname regexes will be matched with python's re.match()
# Exactly one of hostname or hostname_regex must be specified
"""
KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,64}$")

PORT = 5000
ADDR = "0.0.0.0"
