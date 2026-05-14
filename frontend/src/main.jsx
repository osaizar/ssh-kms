import React from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  KeyRound,
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

function App() {
  const [keys, setKeys] = React.useState([]);
  const [form, setForm] = React.useState(emptyForm);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");

  const loadKeys = React.useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/keys");
      if (!response.ok) {
        throw new Error(`Key list request failed with HTTP ${response.status}`);
      }

      const data = await response.json();
      setKeys(data.keys ?? []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadKeys();
  }, [loadKeys]);

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
      const response = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload())
      });

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
      const response = await fetch(`/api/keys/${id}`, { method: "DELETE" });
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

        <button className="icon-button ghost" type="button" onClick={loadKeys} title="Refresh keys">
          <RefreshCcw size={18} />
        </button>
      </header>

      <section className="stats-grid" aria-label="Key summary">
        <Stat label="Entries" value={keys.length} icon={<KeyRound size={20} />} tone="ink" />
        <Stat label="Users" value={keys.length} icon={<ShieldCheck size={20} />} tone="green" />
        <Stat label="Exact hosts" value={exactHosts} icon={<Check size={20} />} tone="blue" />
        <Stat label="Regex hosts" value={regexHosts} icon={<ChevronDown size={20} />} tone="amber" />
      </section>

      <div className="workspace">
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

        <section className="panel key-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Configured keys</p>
              <h2>Access rules</h2>
            </div>
          </div>

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
                <KeyCard key={key.id} entry={key} onDelete={removeKey} />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
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

function KeyCard({ entry, onDelete }) {
  const hasExactHost = hasField(entry, "hostname");
  const hostMode = hasExactHost ? "Exact" : "Regex";
  const hostValue = hasExactHost ? entry.hostname : entry.hostname_regex;

  return (
    <article className="key-card">
      <div className="rule-grid">
        <RulePill label="User" value={entry.user} />
        <RulePill label="Host" value={hostValue} />
      </div>
      <code>{entry.ssh_key}</code>
      <button className="icon-button danger" type="button" onClick={() => onDelete(entry.id)} title="Delete key">
        <Trash2 size={18} />
      </button>
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
