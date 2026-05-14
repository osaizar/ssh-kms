# Deployment

The default deployment path is Docker Compose. It starts Keycloak and SSH KMS,
builds the React frontend, and serves the compiled UI from FastAPI.

## Build

```bash
./build.sh
```

The script delegates to [scripts/build.sh](../scripts/build.sh), which runs
`docker compose build`.

The Dockerfile uses a multi-stage build:

1. `node:22-slim` builds the React app with Vite.
2. `python:3.12-slim` installs the backend dependencies.
3. The compiled `frontend/dist` files are copied into the final image.

The default base images use the public ECR Docker Hub mirror:

```dockerfile
ARG NODE_IMAGE=public.ecr.aws/docker/library/node:22-slim
ARG PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.12-slim
```

Override them if your registry access requires a different mirror:

```bash
docker compose build \
  --build-arg NODE_IMAGE=node:22-slim \
  --build-arg PYTHON_IMAGE=python:3.12-slim
```

## Run

```bash
./run.sh
```

The script delegates to [scripts/run.sh](../scripts/run.sh), validates that the
key configuration file exists, exports `CONFIG_FILE`, and starts Compose.

Default ports:

| Service | URL |
| --- | --- |
| SSH KMS | `http://localhost:5000` |
| Keycloak | `http://localhost:8080` |

## Compose Services

[compose.yaml](../compose.yaml) defines:

- `keycloak`: Keycloak 26.6.1 in development mode.
- `ssh-kms`: the FastAPI backend plus compiled React UI.

Key mounted paths:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `config/ssh-keys.json` | `/config/ssh-keys.json` | Writable SSH key configuration. |
| `keycloak/realm/ssh-kms-realm.json` | `/opt/keycloak/data/import/ssh-kms-realm.json` | Automated realm, client, roles, and users. |
| `keycloak/themes/ssh-kms` | `/opt/keycloak/themes/ssh-kms` | Custom login theme. |

Use a different key file:

```bash
CONFIG_FILE=/secure/path/ssh-keys.json ./run.sh
```

## Keycloak Data

The provided Compose file does not define a persistent Keycloak database volume.
That is useful for development because the realm file is re-imported whenever
the container is recreated.

For a longer-lived deployment:

- add a real database for Keycloak, such as PostgreSQL
- stop using `start-dev`
- configure HTTPS and hostname settings
- rotate the default admin and imported user passwords
- decide how realm changes will be promoted

## Reverse Proxy

For production-style access, put SSH KMS and Keycloak behind a reverse proxy
that provides TLS. Make sure browser-visible OIDC URLs match the public URL.

If the UI is served at `https://kms.example.net`, update:

- `OIDC_ISSUER`
- `OIDC_JWKS_URL`
- `VITE_OIDC_AUTHORITY`
- Keycloak `redirectUris`
- Keycloak `webOrigins`

## Backup

Back up [config/ssh-keys.json](../config/ssh-keys.json). It is the source of
truth for SSH authorization decisions.

Treat that file as sensitive operational data. An attacker with write access to
it can grant SSH access to matching hosts.
