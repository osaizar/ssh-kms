# Security

SSH KMS is intentionally small. The security model depends on running it inside
a trusted network, protecting the JSON key file, and using Keycloak roles for
administrative actions.

## Trust Boundaries

There are two different API surfaces:

- `POST /`: SSH lookup endpoint for managed SSH servers.
- `/api/*`: management API used by the browser UI.

The SSH lookup endpoint is not protected by OIDC because it is designed for the
SSH `AuthorizedKeysCommand` client. Restrict it with network controls.

The management API is protected by OIDC when `OIDC_ENABLED=true`.

## Roles

The default realm defines:

| Role | Access |
| --- | --- |
| `viewer` | Can list configured SSH key entries. |
| `key-admin` | Can list, create, and delete SSH key entries. |

The backend also allows `key-admin` to satisfy `viewer` checks.

## Sensitive Files

Protect these files:

| File | Why it matters |
| --- | --- |
| `config/ssh-keys.json` | Source of truth for SSH access. Write access can grant login access. |
| `keycloak/realm/ssh-kms-realm.json` | Defines imported users, passwords, roles, clients, and redirect URIs. |
| `compose.yaml` | Controls authentication, mounted files, and exposed ports. |

Do not commit real SSH public key inventories for production environments into a
public repository.

## Default Credentials

The included realm is for local development. Before using it anywhere else:

- change the Keycloak bootstrap admin password
- remove or rotate the imported `admin` and `viewer` users
- use temporary passwords for first login
- configure real user lifecycle management in Keycloak

## Network Hardening

Recommended controls:

- expose SSH KMS only on private networks or VPNs
- firewall `POST /` so only managed SSH servers can call it
- serve browser access over HTTPS
- serve Keycloak over HTTPS
- keep Keycloak and SSH KMS on an internal Docker network
- avoid publishing Keycloak admin access broadly

## OIDC Hardening

The included browser client is public and uses Authorization Code with PKCE.
That is suitable for the React UI.

For automation:

- create a separate Keycloak client
- use a flow appropriate for your automation
- assign the minimum role needed
- do not reuse the browser public client for machine credentials

## Operational Notes

Key changes are written atomically to the configured JSON file. Create and delete
operations hold an OS file lock so two administrators do not overwrite each
other's changes. Events are printed as structured JSON logs with:

- timestamp
- actor
- action
- stable key entry ID
- target user
- exact hostname or hostname regex

Forward container logs to your normal log collection system if you need audit
retention.

## Limitations

SSH KMS is not a replacement for enterprise identity infrastructure. If you need
large-scale account lifecycle management, host certificates, compliance
reporting, or centralized policy across many teams, use a dedicated SSH access
management system or directory-backed approach.
