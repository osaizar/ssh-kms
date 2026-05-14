import React from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  KeyRound,
  LogIn,
  LogOut,
  Plus,
  RefreshCcw,
  ShieldCheck,
  Trash2
} from "lucide-react";
import "./styles.css";

const emptyForm = {
  userValue: "",
  hostnameMode: "hostname",
  hostnameValue: "",
  sshKey: ""
};

const oidcEnabled = import.meta.env.VITE_OIDC_ENABLED === "true";
const oidcAuthority = import.meta.env.VITE_OIDC_AUTHORITY || "http://localhost:8080/realms/ssh-kms";
const oidcClientId = import.meta.env.VITE_OIDC_CLIENT_ID || "ssh-kms-ui";
const tokenStorageKey = "ssh-kms:oidc-token";
const viewerRole = "viewer";
const adminRole = "key-admin";

function App() {
  const [keys, setKeys] = React.useState([]);
  const [form, setForm] = React.useState(emptyForm);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [auth, setAuth] = React.useState({
    ready: !oidcEnabled,
    tokenSet: null,
    user: null,
    error: ""
  });

  const canView = !oidcEnabled || hasRole(auth.user, viewerRole) || hasRole(auth.user, adminRole);
  const canAdmin = !oidcEnabled || hasRole(auth.user, adminRole);

  React.useEffect(() => {
    initializeAuth(setAuth);
  }, []);

  const loadKeys = React.useCallback(async () => {
    if (oidcEnabled && (!auth.ready || !auth.tokenSet || !canView)) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await apiFetch("/api/keys", {}, auth, setAuth);
      if (!response.ok) {
        throw new Error(await readError(response, "Key list request failed"));
      }

      const data = await response.json();
      setKeys(data.keys ?? []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [auth, canView]);

  React.useEffect(() => {
    if (auth.ready) {
      loadKeys();
    }
  }, [auth.ready, loadKeys]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function buildPayload() {
    return {
      user: form.userValue.trim(),
      [form.hostnameMode]: form.hostnameValue.trim(),
      ssh_key: form.sshKey.trim()
    };
  }

  async function createKey(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");

    try {
      const response = await apiFetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload())
      }, auth, setAuth);

      if (!response.ok) {
        throw new Error(await readError(response, "Create request failed"));
      }

      setForm(emptyForm);
      setNotice("Key entry added");
      await loadKeys();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeKey(id) {
    setError("");
    setNotice("");

    try {
      const response = await apiFetch(`/api/keys/${id}`, { method: "DELETE" }, auth, setAuth);
      if (!response.ok) {
        throw new Error(await readError(response, "Delete request failed"));
      }

      setNotice("Key entry removed");
      await loadKeys();
    } catch (err) {
      setError(err.message);
    }
  }

  const exactHosts = keys.filter((key) => hasField(key, "hostname")).length;
  const regexHosts = keys.length - exactHosts;

  if (oidcEnabled && !auth.ready) {
    return <AuthScreen title="Connecting to Keycloak" detail="Preparing secure session" />;
  }

  if (oidcEnabled && !auth.tokenSet) {
    return (
      <AuthScreen
        title="SSH KMS"
        detail={auth.error || "Sign in with Keycloak to manage SSH keys"}
        action={<button className="primary-button" type="button" onClick={startLogin}><LogIn size={18} />Sign in</button>}
      />
    );
  }

  if (!canView) {
    return (
      <AuthScreen
        title="Access denied"
        detail="Your Keycloak account does not have the viewer role."
        action={<button className="primary-button" type="button" onClick={() => logout(auth.tokenSet)}><LogOut size={18} />Sign out</button>}
      />
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img src="/img/ssh-kms-icon.png" alt="" className="brand-mark" />
          <div>
            <p className="eyebrow">SSH KMS</p>
            <h1>Key Access Console</h1>
          </div>
        </div>

        <div className="topbar-actions">
          {oidcEnabled && <UserBadge user={auth.user} tokenSet={auth.tokenSet} />}
          <button className="icon-button ghost" type="button" onClick={loadKeys} title="Refresh keys">
            <RefreshCcw size={18} />
          </button>
        </div>
      </header>

      <section className="stats-grid" aria-label="Key summary">
        <Stat label="Entries" value={keys.length} icon={<KeyRound size={20} />} tone="ink" />
        <Stat label="Users" value={keys.length} icon={<ShieldCheck size={20} />} tone="green" />
        <Stat label="Exact hosts" value={exactHosts} icon={<Check size={20} />} tone="blue" />
        <Stat label="Regex hosts" value={regexHosts} icon={<ChevronDown size={20} />} tone="amber" />
      </section>

      <div className="workspace">
        {canAdmin && (
          <form className="panel form-panel" onSubmit={createKey}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">New entry</p>
                <h2>Add SSH key</h2>
              </div>
              <button className="primary-button" type="submit" disabled={saving}>
                <Plus size={18} />
                {saving ? "Adding" : "Add"}
              </button>
            </div>

            <label className="field">
              <span>User</span>
              <input
                value={form.userValue}
                onChange={(event) => updateField("userValue", event.target.value)}
                placeholder="alice"
                required
              />
            </label>

            <FieldGroup
              label="Host match"
              mode={form.hostnameMode}
              value={form.hostnameValue}
              exactValue="hostname"
              regexValue="hostname_regex"
              placeholder={form.hostnameMode === "hostname" ? "workstation-01" : "workstation-.+"}
              onModeChange={(value) => updateField("hostnameMode", value)}
              onValueChange={(value) => updateField("hostnameValue", value)}
            />

            <label className="field">
              <span>Public key</span>
              <textarea
                value={form.sshKey}
                onChange={(event) => updateField("sshKey", event.target.value)}
                placeholder="ssh-ed25519 AAAA..."
                required
              />
            </label>
          </form>
        )}

        <section className="panel key-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Configured keys</p>
              <h2>Access rules</h2>
            </div>
          </div>

          {!canAdmin && (
            <div className="alert success">
              <ShieldCheck size={18} />
              <span>Viewer access</span>
            </div>
          )}

          {error && (
            <div className="alert error">
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          {notice && !error && (
            <div className="alert success">
              <Check size={18} />
              <span>{notice}</span>
            </div>
          )}

          {loading ? (
            <div className="empty-state">Loading keys</div>
          ) : keys.length === 0 ? (
            <div className="empty-state">No key entries</div>
          ) : (
            <div className="key-list">
              {keys.map((key) => (
                <KeyCard key={key.id} entry={key} onDelete={removeKey} canDelete={canAdmin} />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function AuthScreen({ title, detail, action }) {
  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <img src="/img/ssh-kms-icon.png" alt="" className="brand-mark" />
        <p className="eyebrow">Protected console</p>
        <h1>{title}</h1>
        <p>{detail}</p>
        {action}
      </div>
    </main>
  );
}

function UserBadge({ user, tokenSet }) {
  return (
    <div className="user-badge">
      <span>{displayName(user)}</span>
      <button className="icon-button ghost" type="button" onClick={() => logout(tokenSet)} title="Sign out">
        <LogOut size={18} />
      </button>
    </div>
  );
}

function Stat({ label, value, icon, tone }) {
  return (
    <article className={`stat-card ${tone}`}>
      <div className="stat-icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function FieldGroup({
  label,
  mode,
  value,
  exactValue,
  regexValue,
  placeholder,
  onModeChange,
  onValueChange
}) {
  return (
    <div className="field-stack">
      <span className="field-label">{label}</span>
      <div className="segmented">
        <button
          type="button"
          className={mode === exactValue ? "active" : ""}
          onClick={() => onModeChange(exactValue)}
        >
          Exact
        </button>
        <button
          type="button"
          className={mode === regexValue ? "active" : ""}
          onClick={() => onModeChange(regexValue)}
        >
          Regex
        </button>
      </div>
      <input
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        placeholder={placeholder}
        required
      />
    </div>
  );
}

function KeyCard({ entry, onDelete, canDelete }) {
  const hasExactHost = hasField(entry, "hostname");
  const hostValue = hasExactHost ? entry.hostname : entry.hostname_regex;

  return (
    <article className="key-card">
      <div className="rule-grid">
        <RulePill label="User" value={entry.user} />
        <RulePill label="Host" value={hostValue} />
      </div>
      <code>{entry.ssh_key}</code>
      {canDelete && (
        <button className="icon-button danger" type="button" onClick={() => onDelete(entry.id)} title="Delete key">
          <Trash2 size={18} />
        </button>
      )}
    </article>
  );
}

function RulePill({ label, value }) {
  return (
    <div className="rule-pill">
      <span>{label}</span>
      <em>{value}</em>
    </div>
  );
}

function hasField(entry, field) {
  return Object.prototype.hasOwnProperty.call(entry, field);
}

async function apiFetch(path, options, auth, setAuth) {
  const headers = new Headers(options.headers || {});

  if (oidcEnabled) {
    const accessToken = await getAccessToken(auth, setAuth);
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(path, { ...options, headers });
}

async function initializeAuth(setAuth) {
  if (!oidcEnabled) {
    setAuth({ ready: true, tokenSet: null, user: null, error: "" });
    return;
  }

  try {
    const params = new URLSearchParams(window.location.search);
    let tokenSet = null;

    if (params.has("code")) {
      tokenSet = await completeLogin(params);
      window.history.replaceState({}, document.title, window.location.origin + window.location.pathname);
    } else {
      tokenSet = loadTokenSet();
    }

    if (tokenSet && tokenNeedsRefresh(tokenSet) && tokenSet.refresh_token) {
      tokenSet = await refreshToken(tokenSet.refresh_token);
    }

    if (!tokenSet || tokenExpired(tokenSet)) {
      clearTokenSet();
      setAuth({ ready: true, tokenSet: null, user: null, error: "" });
      return;
    }

    setAuth({ ready: true, tokenSet, user: decodeJwt(tokenSet.access_token), error: "" });
  } catch (err) {
    clearTokenSet();
    setAuth({ ready: true, tokenSet: null, user: null, error: err.message });
  }
}

async function startLogin() {
  const state = randomString();
  const verifier = randomString();
  const challenge = await pkceChallenge(verifier);
  const redirectUri = window.location.origin + window.location.pathname;

  sessionStorage.setItem("ssh-kms:oidc-state", state);
  sessionStorage.setItem("ssh-kms:oidc-verifier", verifier);
  sessionStorage.setItem("ssh-kms:oidc-redirect-uri", redirectUri);

  const authUrl = new URL(`${oidcAuthority}/protocol/openid-connect/auth`);
  authUrl.searchParams.set("client_id", oidcClientId);
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", "openid profile email");
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("code_challenge", challenge);
  authUrl.searchParams.set("code_challenge_method", "S256");
  window.location.assign(authUrl.toString());
}

async function completeLogin(params) {
  const expectedState = sessionStorage.getItem("ssh-kms:oidc-state");
  const verifier = sessionStorage.getItem("ssh-kms:oidc-verifier");
  const redirectUri = sessionStorage.getItem("ssh-kms:oidc-redirect-uri");

  if (!expectedState || params.get("state") !== expectedState || !verifier || !redirectUri) {
    throw new Error("Invalid OIDC login response");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: oidcClientId,
    redirect_uri: redirectUri,
    code: params.get("code"),
    code_verifier: verifier
  });

  const response = await fetch(`${oidcAuthority}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });

  if (!response.ok) {
    throw new Error("OIDC token exchange failed");
  }

  sessionStorage.removeItem("ssh-kms:oidc-state");
  sessionStorage.removeItem("ssh-kms:oidc-verifier");
  sessionStorage.removeItem("ssh-kms:oidc-redirect-uri");

  return saveTokenSet(await response.json());
}

async function getAccessToken(auth, setAuth) {
  if (!auth.tokenSet) {
    throw new Error("Not signed in");
  }

  if (!tokenNeedsRefresh(auth.tokenSet)) {
    return auth.tokenSet.access_token;
  }

  if (!auth.tokenSet.refresh_token) {
    clearTokenSet();
    setAuth({ ready: true, tokenSet: null, user: null, error: "Session expired" });
    throw new Error("Session expired");
  }

  const tokenSet = await refreshToken(auth.tokenSet.refresh_token);
  setAuth({ ready: true, tokenSet, user: decodeJwt(tokenSet.access_token), error: "" });
  return tokenSet.access_token;
}

async function refreshToken(refreshTokenValue) {
  const response = await fetch(`${oidcAuthority}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      client_id: oidcClientId,
      refresh_token: refreshTokenValue
    })
  });

  if (!response.ok) {
    throw new Error("OIDC token refresh failed");
  }

  return saveTokenSet(await response.json());
}

function logout(tokenSet) {
  clearTokenSet();

  if (!oidcEnabled) {
    return;
  }

  const logoutUrl = new URL(`${oidcAuthority}/protocol/openid-connect/logout`);
  logoutUrl.searchParams.set("client_id", oidcClientId);
  logoutUrl.searchParams.set("post_logout_redirect_uri", window.location.origin + "/");
  if (tokenSet?.id_token) {
    logoutUrl.searchParams.set("id_token_hint", tokenSet.id_token);
  }
  window.location.assign(logoutUrl.toString());
}

function saveTokenSet(tokenSet) {
  const saved = {
    ...tokenSet,
    expires_at: Math.floor(Date.now() / 1000) + Number(tokenSet.expires_in || 0)
  };
  localStorage.setItem(tokenStorageKey, JSON.stringify(saved));
  return saved;
}

function loadTokenSet() {
  const raw = localStorage.getItem(tokenStorageKey);
  return raw ? JSON.parse(raw) : null;
}

function clearTokenSet() {
  localStorage.removeItem(tokenStorageKey);
}

function tokenExpired(tokenSet) {
  return !tokenSet?.access_token || Number(tokenSet.expires_at || 0) <= Math.floor(Date.now() / 1000);
}

function tokenNeedsRefresh(tokenSet) {
  return !tokenSet?.access_token || Number(tokenSet.expires_at || 0) - 30 <= Math.floor(Date.now() / 1000);
}

function decodeJwt(token) {
  return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
}

function displayName(user) {
  return user?.preferred_username || user?.email || user?.sub || "signed in";
}

function hasRole(user, role) {
  return user?.realm_access?.roles?.includes(role) || false;
}

function randomString() {
  return base64UrlEncode(crypto.getRandomValues(new Uint8Array(32)));
}

async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

function base64UrlEncode(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function readError(response, fallback) {
  const body = await response.json().catch(() => null);
  if (typeof body?.detail === "string") {
    return body.detail;
  }

  if (Array.isArray(body?.detail)) {
    return body.detail.map((item) => item.msg).filter(Boolean).join("; ");
  }

  return `${fallback} with HTTP ${response.status}`;
}

createRoot(document.getElementById("root")).render(<App />);
