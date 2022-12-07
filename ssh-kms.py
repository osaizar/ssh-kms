import os

from flask import Flask, request, jsonify, abort
import re
import json

KEY_FILE = "/config/ssh-keys.json"
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

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    body = f"""
    <h1>SSH KMS</h1>

    <p>To install the client run:</p>
    <p>$ wget -O get-ssh-keys.py {request.url_root}get_client && sudo python3 get-ssh-keys.py --install</p>
    """
    return body


@app.route('/', methods=["POST"])
def get_keys():
    try:
        try:
            data = request.get_json(silent = True) # user, hostname
            if "user" not in data or "hostname" not in data:
                print("Error! 'user' and 'hostname' not included in request")
                abort(400)
        except Exception as e:
            print(e)
            abort(400)

        keys = filter_keys(data["user"], data["hostname"])

        return jsonify({"ssh-keys" : [k["ssh-key"] for k in keys]}), 200
    except Exception as e:
        print(e)
        abort(500)


@app.route('/get_client', methods=["GET"])
def get_client():
    client = open(CLIENT_FILE, "r").read().replace("{URL}", request.url_root)
    return client, 200


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
    read_key_json() # Just to check the file
    app.run(host=ADDR, port=PORT)