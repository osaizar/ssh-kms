import os
import re
import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

KEY_FILE = "ssh-keys.json"
CLIENT_FILE = "/app/client/get-ssh-keys.py"

KEY_FORMAT = """
[
    {"user" : "", "hostname" : "", "ssh-key" : "..", }, # For exact user or host
    {"user_regex" : "", "hostname_regex" : "", "ssh-key" : "..", } # For regexes to math user or host
]
# The regexes will be matched with python's re.match()
# If both exact and regexes are specified, only the exact user or hostname will be used
"""

PORT = 5000
ADDR = "0.0.0.0"


@asynccontextmanager
async def lifespan(_app):
    read_key_json()
    yield


app = FastAPI(title="SSH KMS", lifespan=lifespan)


def index_body(base_url):
    body = f"""
    <h1>SSH KMS</h1>

    <p>To install the client run:</p>
    <p>$ wget -O get-ssh-keys.py {base_url}get_client && sudo python3 get-ssh-keys.py --install</p>
    """
    return body


@app.get("/get_client", response_class=PlainTextResponse)
async def get_client(request: Request):
    try:
        with open(CLIENT_FILE, "r", encoding="utf-8") as client_file:
            return client_file.read().replace("{URL}", str(request.base_url))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500)


@app.get("/", response_class=HTMLResponse)
@app.get("/{path:path}", response_class=HTMLResponse)
async def index(request: Request, path: str = ""):
    return index_body(str(request.base_url))


@app.post("/")
async def get_keys(request: Request):
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


"""
Helping Functions start:
"""


def filter_keys(user, hostname):
    filtered_keys = []
    keys = read_key_json()


    for k in keys:
        user_match = False
        hostname_match = False

        # 1. User
        if "user" in k:
            user_match = bool(user == k["user"])
        else:
            user_match = bool(re.match(k["user_regex"], user))

        # 2. Hostname:
        if "hostname" in k:
            hostname_match = bool(hostname == k["hostname"])
        else:
            hostname_match = bool(re.match(k["hostname_regex"], hostname))
        
        if user_match and hostname_match:
            filtered_keys.append(k)
        
    return filtered_keys


def read_key_json():
    if not os.path.isfile(KEY_FILE):
        raise Exception(f"Key file {KEY_FILE} does not exist!")
    
    try:
        key_str = open(KEY_FILE, "r").read()
        keys = json.loads(key_str)

        if type(keys) != list:
            raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")

        for k in keys:
            if "ssh-key" not in k:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
            if "user" not in k and "user_regex" not in k:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
            if "hostname" not in k and "hostname_regex" not in k:
                raise Exception(f"Key file format is not correct, use the next format: {KEY_FORMAT}")
        
        return keys  
    except FileNotFoundError as e:
        raise Exception(f"Could not find key file {KEY_FILE}!")
    except PermissionError as e:
        raise Exception(f"Yo do not have permission to read key file {KEY_FILE}!")
    except json.decoder.JSONDecodeError as e:
        raise Exception(f"Key file {KEY_FILE} is not a valid json file!, {e}")
    
    return False


"""
Helping Functions end
"""


if __name__ == '__main__':
    uvicorn.run(app, host=ADDR, port=PORT)
