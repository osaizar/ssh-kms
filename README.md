<p align="center">
  <img src="img/ssh-kms-icon.png" alt="SSH KMS logo" width="104" height="104">
</p>

<h1 align="center">SSH KMS</h1>

<p align="center">
  Small-network SSH key distribution with a FastAPI backend, React management UI,
  and Keycloak/OIDC authentication.
</p>

SSH KMS lets SSH servers ask one central service which public keys are allowed
for a specific local user on a specific host. It is built for labs, private
networks, classrooms, homelabs, and other environments where a lightweight JSON
configuration is enough.

The management UI edits the same JSON file that the SSH lookup endpoint uses.
Keycloak protects the UI and API with OIDC roles, while the SSH lookup endpoint
stays simple for `AuthorizedKeysCommand` clients inside the trusted network.

## Features

- FastAPI service for SSH key lookups and management endpoints.
- React UI for adding and removing SSH key entries.
- Keycloak OIDC login with `viewer` and `key-admin` roles.
- Custom Keycloak login theme mounted through Docker Compose.
- Exact usernames only, with exact hostname or regex hostname matching.
- JSON-backed configuration, no database required.
- Docker build compiles the frontend and serves it from the backend.
- Helper scripts for building and running the full stack.

## Quick Start

Requirements:

- Docker
- Docker Compose v2, or the legacy `docker-compose` binary

Build and run everything:

```bash
./build.sh
./run.sh
```

Open:

```text
SSH KMS UI: http://localhost:5000
Keycloak:   http://localhost:8080
```

Default imported users:

| Username | Password | Roles |
| --- | --- | --- |
| `admin` | `admin` | `viewer`, `key-admin` |
| `viewer` | `viewer` | `viewer` |

Change these before using the project outside a throwaway local environment.
Automated users live in [keycloak/realm/ssh-kms-realm.json](keycloak/realm/ssh-kms-realm.json).

## How It Works

An SSH server calls the installed client as its `AuthorizedKeysCommand`.
The client sends the requested local username and the server hostname to SSH KMS:

```json
{
  "user": "alice",
  "hostname": "lab-web-01"
}
```

SSH KMS reads [config/ssh-keys.json](config/ssh-keys.json), finds entries where:

- `user` matches exactly
- either `hostname` matches exactly, or `hostname_regex` matches with Python `re.match`

It returns the matching public keys to SSH, and SSH performs the normal key
authentication flow.

Example configuration:

```json
[
  {
    "id": "key_alice_web01",
    "user": "alice",
    "hostname": "lab-web-01",
    "ssh-key": "ssh-ed25519 AAAAC3Nza..."
  },
  {
    "id": "key_ops_lab",
    "user": "ops",
    "hostname_regex": "lab-.+",
    "ssh-key": "ssh-ed25519 AAAAC3Nza..."
  }
]
```

User regexes are intentionally not supported. Hostname regexes are the only
regex matchers.

Each entry must have a stable `id`. The API generates IDs for new entries, and
manual JSON edits must preserve existing IDs or provide a unique ID for new
entries. Deletes use IDs instead of JSON array positions.

## Repository Layout

```text
backend/          Installable FastAPI backend package
client/           SSH AuthorizedKeysCommand client
config/           SSH key JSON configuration
docs/             Operator and developer documentation
frontend/         React management UI built with Vite
img/              Shared visual assets
keycloak/realm/   Imported Keycloak realm, clients, roles, and users
keycloak/themes/  Custom Keycloak login theme
scripts/          Docker Compose helper scripts
```

Root-level `build.sh` and `run.sh` are compatibility wrappers around the scripts
in [scripts](scripts).

## Documentation

| Topic | Document |
| --- | --- |
| Key file format, OIDC settings, and Keycloak users | [docs/configuration.md](docs/configuration.md) |
| HTTP endpoints and curl examples | [docs/api.md](docs/api.md) |
| Docker, Compose, scripts, and deployment notes | [docs/deployment.md](docs/deployment.md) |
| Security model and hardening checklist | [docs/security.md](docs/security.md) |

The UI also includes a JSON export button for quick backups of the current key
configuration.

## Local Development

Create and activate the Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "backend[test]"
```

Run the backend without OIDC:

```bash
python -m ssh_kms
```

Run the backend and client tests:

```bash
pytest
```

The default pytest configuration reports branch coverage for the backend package
and SSH client helper.

Run the frontend dev server:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Build the production frontend:

```bash
npm --prefix frontend run build
```

The Docker build script runs the pytest suite from a backend test image before
building the final Compose image. Docker builds also run the frontend build
automatically and copy `frontend/dist` into the final Python image.

## Install The SSH Client

On each SSH server that should use SSH KMS:

```bash
wget -O get-ssh-keys.py http://<ssh-kms-host>:5000/get_client
sudo python3 get-ssh-keys.py --install
sudo systemctl restart sshd
```

The installer copies the client to `/usr/bin/get-ssh-keys` and configures
`sshd_config` to call it as `AuthorizedKeysCommand`.

## Security Notice

This project is for isolated networks and small deployments. Do not expose SSH
KMS directly to the public internet. Protect [config/ssh-keys.json](config/ssh-keys.json)
carefully: write access to that file is equivalent to the ability to grant SSH
access across the managed hosts.
