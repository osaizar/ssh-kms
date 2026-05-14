import os
import re
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = os.environ.get("SSH_KMS_KEY_FILE", str(BASE_DIR / "ssh-keys.json"))
CLIENT_FILE = os.environ.get("SSH_KMS_CLIENT_FILE", str(BASE_DIR / "client/get-ssh-keys.py"))
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

KEY_FORMAT = """
[
    {"user" : "", "hostname" : "", "ssh-key" : "..", }, # For exact user and exact host
    {"user" : "", "hostname_regex" : "", "ssh-key" : "..", } # For exact user and regex host
]
# The hostname regexes will be matched with python's re.match()
# Exactly one of hostname or hostname_regex must be specified
"""

PORT = 5000
ADDR = "0.0.0.0"


class KeyEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user: str = Field(min_length=1)
    hostname: Optional[str] = None
    hostname_regex: Optional[str] = None
    ssh_key: str = Field(alias="ssh-key", min_length=1)

    @model_validator(mode="after")
    def validate_matchers(self):
        """Validate exact user matching and exactly one host matcher."""
        hostname_matchers = [self.hostname, self.hostname_regex]

        if not self.user.strip():
            raise ValueError("user cannot be empty")
        if not self.ssh_key.strip():
            raise ValueError("ssh_key cannot be empty")
        for field_name in ("hostname", "hostname_regex"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
        if sum(value is not None for value in hostname_matchers) != 1:
            raise ValueError("Provide exactly one of hostname or hostname_regex")
        if self.hostname_regex is not None:
            re.compile(self.hostname_regex.strip())

        return self


@asynccontextmanager
async def lifespan(_app):
    """Validate the configured key file before accepting requests."""
    read_key_json()
    yield


app = FastAPI(title="SSH KMS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

if (BASE_DIR / "img").is_dir():
    app.mount("/img", StaticFiles(directory=BASE_DIR / "img"), name="img")


def serialize_key(index, key):
    """Return a key entry formatted for API responses with a stable index ID."""
    return {"id": index, **config_key_to_api_key(key)}


def config_key_to_api_key(key):
    """Convert one JSON config key entry into the API field naming format."""
    api_key = dict(key)
    api_key["ssh_key"] = api_key.pop("ssh-key")
    return api_key


def api_key_to_config_key(key):
    """Convert a validated API key entry into the on-disk JSON format."""
    config_key = key.model_dump(exclude_none=True, by_alias=True)
    config_key["user"] = config_key["user"].strip()
    if "hostname" in config_key:
        config_key["hostname"] = config_key["hostname"].strip()
    if "hostname_regex" in config_key:
        config_key["hostname_regex"] = config_key["hostname_regex"].strip()
    config_key["ssh-key"] = config_key.pop("ssh-key").strip()
    return config_key


@app.get("/get_client", response_class=PlainTextResponse)
async def get_client(request: Request):
    """Serve the SSH AuthorizedKeysCommand client with the server URL embedded."""
    try:
        with open(CLIENT_FILE, "r", encoding="utf-8") as client_file:
            return client_file.read().replace("{URL}", str(request.base_url))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.post("/")
async def get_keys(request: Request):
    """Return SSH public keys that match the requested user and hostname."""
    try:
        data = await request.json()  # user, hostname
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
        return {"ssh-keys" : [k["ssh-key"] for k in keys]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.get("/api/keys")
async def list_keys():
    """List all configured key entries for the management UI."""
    try:
        keys = read_key_json()
        return {"keys": [serialize_key(index, key) for index, key in enumerate(keys)]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.post("/api/keys", status_code=status.HTTP_201_CREATED)
async def create_key(key: KeyEntry):
    """Append a validated key entry to the JSON configuration file."""
    try:
        keys = read_key_json()
        keys.append(api_key_to_config_key(key))
        write_key_json(keys)
        return serialize_key(len(keys) - 1, keys[-1])
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: int):
    """Delete a key entry by its current JSON array index."""
    try:
        keys = read_key_json()
        if key_id < 0 or key_id >= len(keys):
            raise HTTPException(status_code=404, detail="Key entry not found")

        deleted_key = keys.pop(key_id)
        write_key_json(keys)
        return serialize_key(key_id, deleted_key)
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.get("/", response_class=HTMLResponse)
@app.get("/{path:path}", response_class=HTMLResponse)
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


"""
Helping Functions start:
"""


def filter_keys(user, hostname):
    """Filter configured keys by exact user and exact or regex hostname."""
    filtered_keys = []
    keys = read_key_json()


    for k in keys:
        hostname_match = False

        # 1. User
        user_match = bool(user == k["user"])

        # 2. Hostname:
        if "hostname" in k:
            hostname_match = bool(hostname == k["hostname"])
        else:
            hostname_match = bool(re.match(k["hostname_regex"], hostname))
        
        if user_match and hostname_match:
            filtered_keys.append(k)
        
    return filtered_keys


def read_key_json():
    """Read and validate the SSH key JSON configuration file."""
    if not os.path.isfile(KEY_FILE):
        raise Exception(f"Key file {KEY_FILE} does not exist!")
    
    try:
        key_str = open(KEY_FILE, "r", encoding="utf-8").read()
        keys = json.loads(key_str)

        if type(keys) != list:
            raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")

        allowed_key_fields = {"user", "hostname", "hostname_regex", "ssh-key"}

        for k in keys:
            if set(k) - allowed_key_fields:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
            if "ssh-key" not in k:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
            if "user" not in k:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
            if ("hostname" in k) == ("hostname_regex" in k):
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
        
        return keys  
    except FileNotFoundError as e:
        raise Exception(f"Could not find key file {KEY_FILE}!")
    except PermissionError as e:
        raise Exception(f"Yo do not have permission to read key file {KEY_FILE}!")
    except json.decoder.JSONDecodeError as e:
        raise Exception(f"Key file {KEY_FILE} is not a valid json file!, {e}")
    
    return False


def write_key_json(keys):
    """Persist key entries to the JSON configuration file atomically."""
    key_file = Path(KEY_FILE)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = key_file.with_suffix(f"{key_file.suffix}.tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=4)
        f.write("\n")

    os.replace(temp_file, key_file)


"""
Helping Functions end
"""


if __name__ == '__main__':
    uvicorn.run(app, host=ADDR, port=PORT)
