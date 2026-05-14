# ssh-kms

Simple ssh key distributing system.

No database needed, no ldap needed. Just you and a JSON user & key list.


## How does it work

### The server
SSH-KMS is a FastAPI web server written in python that serves ssh public keys depending on the user and the server that is asking for it. It also serves a React management UI for editing the JSON key list.

The ssh keys need to be configured in the ssh-keys.json config file, exposed in the container in the /config directory.

This configuration file supports exact user names and exact or regex-based hostnames:

```json
[
    {
        "user" : "bob", 
        "hostname" : "bobs-computer", # Just bobs-computer
        "ssh-key" : "xxx"
    },
    {
        "user" : "alice", 
        "hostname_regex" : "alice-.+", # Matches anything following "alice-" 
        "ssh-key" : "xxx"
    },
    {
        "user" : "carol", 
        "hostname_regex" : ".+", # Matches any host
        "ssh-key" : "xxx"
    }
]
```

This can be used as an ACL for a group of servers or a lab.

### The management UI
Run the backend:

```bash
source .venv/bin/activate
python ssh-kms.py
```

Run the frontend in development:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open the Vite URL and use the console to add or remove key entries. The UI writes to `ssh-keys.json` through the backend API.

For a production-style single process, build the frontend and start FastAPI:

```bash
npm --prefix frontend run build
source .venv/bin/activate
python ssh-kms.py
```

Docker builds compile the React frontend automatically:

```bash
./build.sh
./run.sh
```

The Docker image serves the compiled frontend and API from the FastAPI process on port `5000`.

The backend exposes these management endpoints:

```text
GET    /api/keys
POST   /api/keys
DELETE /api/keys/{id}
```

Entries created through the UI or API always use an exact `user`. Host matching can still use either `hostname` or `hostname_regex`.

The original SSH lookup endpoint is still available at `POST /`.

### The client
The client needs to be installed all the servers that use this authentication method.
You can install the client with this command:

```bash
wget -O get-ssh-keys.py http://{ssh-kms-host}:{port}/get_client && sudo python3 get-ssh-keys.py --install
```

This will download the _get-ssh-keys.py_ client, copy it into /usr/bin and configure the ssh server to use it as an AuthorizedKeysCommand.

## Disclaimers

- This is not the best way to manage the keys of an organization, only for small non production networks. Look into setting up a ldap instead.
- Do not expose the server to the internet, only use it in a isolated network.
- You need to secure the ssh-keys.json file, **if an attacker can get write access to it, your entire network will be compromised**.
