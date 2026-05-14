# API Reference

SSH KMS exposes one unauthenticated SSH lookup API for managed servers and a
separate authenticated management API for the web UI.

## SSH Lookup

### `POST /`

Returns public keys that match the requested exact user and hostname.

Request:

```json
{
  "user": "alice",
  "hostname": "lab-web-01"
}
```

Response:

```json
{
  "ssh-keys": [
    "ssh-ed25519 AAAAC3Nza..."
  ]
}
```

Curl example:

```bash
curl -sS http://localhost:5000/ \
  -H 'Content-Type: application/json' \
  -d '{"user":"alice","hostname":"lab-web-01"}'
```

This endpoint is intentionally simple because it is called by the SSH
`AuthorizedKeysCommand` client. Restrict access to it at the network layer.

## Client Download

### `GET /get_client`

Returns the Python SSH client with the current SSH KMS base URL embedded.

Install from a managed SSH server:

```bash
wget -O get-ssh-keys.py http://<ssh-kms-host>:5000/get_client
sudo python3 get-ssh-keys.py --install
sudo systemctl restart sshd
```

## Authentication Status

### `GET /api/auth/me`

Returns the current user's display name and roles.

Requires any valid OIDC access token when `OIDC_ENABLED=true`.

Response:

```json
{
  "username": "admin",
  "roles": [
    "key-admin",
    "viewer"
  ]
}
```

Curl example:

```bash
curl -sS http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## List Keys

### `GET /api/keys`

Lists every configured key entry.

Required role:

- `viewer`
- or `key-admin`, which also satisfies viewer access

Response:

```json
{
  "keys": [
    {
      "id": 0,
      "user": "alice",
      "hostname": "lab-web-01",
      "ssh_key": "ssh-ed25519 AAAAC3Nza..."
    }
  ]
}
```

Curl example:

```bash
curl -sS http://localhost:5000/api/keys \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## Create Key

### `POST /api/keys`

Appends one validated key entry to the JSON configuration file.

Required role:

- `key-admin`

Request with exact hostname:

```json
{
  "user": "alice",
  "hostname": "lab-web-01",
  "ssh_key": "ssh-ed25519 AAAAC3Nza..."
}
```

Request with hostname regex:

```json
{
  "user": "ops",
  "hostname_regex": "lab-.+",
  "ssh_key": "ssh-ed25519 AAAAC3Nza..."
}
```

Curl example:

```bash
curl -sS http://localhost:5000/api/keys \
  -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"user":"alice","hostname":"lab-web-01","ssh_key":"ssh-ed25519 AAAAC3Nza..."}'
```

Validation rules:

- `user` must be non-empty and exact.
- `ssh_key` must be non-empty.
- exactly one of `hostname` or `hostname_regex` must be present.
- `hostname_regex` must compile as a Python regex.
- unknown fields are rejected.

## Delete Key

### `DELETE /api/keys/{id}`

Deletes a key by its current array index from the JSON file.

Required role:

- `key-admin`

Curl example:

```bash
curl -sS http://localhost:5000/api/keys/0 \
  -X DELETE \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

Because IDs are JSON array indexes, always refresh the key list before deleting
when multiple administrators may be editing the file.

## OIDC Access Tokens

The included `ssh-kms-ui` client is a browser public client using Authorization
Code with PKCE. For browser use, the React UI handles token acquisition.

For non-browser automation against `/api/*`, create a separate Keycloak client
suited to that automation flow, assign the needed roles, and send its access
token as a Bearer token.
