import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response

from .audit import audit_key_change
from .auth import current_username, require_authenticated, require_role, token_roles
from .config import CLIENT_FILE, FRONTEND_DIST, OIDC_ADMIN_ROLE, OIDC_VIEWER_ROLE
from .models import KeyEntry
from .storage import (
    api_key_to_config_key,
    filter_keys,
    key_file_lock,
    read_key_json,
    read_key_json_unlocked,
    serialize_key,
    write_key_json_unlocked,
)


router = APIRouter()


@router.get("/get_client", response_class=PlainTextResponse)
async def get_client(request: Request):
    """Serve the SSH AuthorizedKeysCommand client with the server URL embedded."""
    try:
        with open(CLIENT_FILE, "r", encoding="utf-8") as client_file:
            return client_file.read().replace("{URL}", str(request.base_url))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.post("/")
async def get_keys(request: Request):
    """Return SSH public keys that match the requested user and hostname."""
    try:
        data = await request.json()
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("user"), str)
            or not isinstance(data.get("hostname"), str)
        ):
            print("Error! 'user' and 'hostname' string values not included in request")
            raise HTTPException(status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400)

    try:
        keys = filter_keys(data["user"], data["hostname"])
        return {"ssh-keys": [key["ssh-key"] for key in keys]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.get("/api/keys")
async def list_keys(_user=Depends(require_role(OIDC_VIEWER_ROLE))):
    """List all configured key entries for the management UI."""
    try:
        keys = read_key_json()
        return {"keys": [serialize_key(key) for key in keys]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.get("/api/keys/export")
async def export_keys(_user=Depends(require_role(OIDC_VIEWER_ROLE))):
    """Export the current SSH key configuration as a downloadable JSON file."""
    try:
        keys = read_key_json()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"ssh-kms-keys-{timestamp}.json"
        content = json.dumps(keys, indent=4)

        return Response(
            content=f"{content}\n",
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.post("/api/keys", status_code=status.HTTP_201_CREATED)
async def create_key(key: KeyEntry, current_user=Depends(require_role(OIDC_ADMIN_ROLE))):
    """Append a validated key entry to the JSON configuration file."""
    try:
        with key_file_lock(exclusive=True):
            keys = read_key_json_unlocked()
            existing_ids = {entry["id"] for entry in keys}
            keys.append(api_key_to_config_key(key, existing_ids))
            write_key_json_unlocked(keys)

        audit_key_change("create", current_user, keys[-1])
        return serialize_key(keys[-1])
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.delete("/api/keys/{key_id}")
async def delete_key(key_id: str, current_user=Depends(require_role(OIDC_ADMIN_ROLE))):
    """Delete a key entry by its stable ID."""
    try:
        with key_file_lock(exclusive=True):
            keys = read_key_json_unlocked()
            delete_index = next((index for index, key in enumerate(keys) if key["id"] == key_id), None)

            if delete_index is None:
                raise HTTPException(status_code=404, detail="Key entry not found")

            deleted_key = keys.pop(delete_index)
            write_key_json_unlocked(keys)

        audit_key_change("delete", current_user, deleted_key)
        return serialize_key(deleted_key)
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@router.get("/api/auth/me")
async def get_current_user(current_user=Depends(require_authenticated)):
    """Return the authenticated user's identity and roles."""
    return {
        "username": current_username(current_user),
        "roles": sorted(token_roles(current_user)),
    }


@router.get("/", response_class=HTMLResponse)
@router.get("/{path:path}", response_class=HTMLResponse)
async def index(request: Request, path: str = ""):
    """Serve the React frontend or a minimal fallback installation page."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    base_url = str(request.base_url)
    return f"""
    <h1>SSH KMS</h1>

    <p>Build the frontend with <code>npm --prefix frontend run build</code>.</p>
    <p>To install the client run:</p>
    <p>$ wget -O get-ssh-keys.py {base_url}get_client && sudo python3 get-ssh-keys.py --install</p>
    """
