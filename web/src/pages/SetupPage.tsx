import { useEffect, useMemo, useState } from "react";
import { getEditableConfig, saveSetupConfig, validateSetupConfig } from "../api/config";
import type { ConfigStatusResponse, SetupConfigPatch, SetupEditableConfigResponse } from "../api/types";
import { ConfigChecklist } from "../components/ConfigChecklist";
import { StatusCard } from "../components/StatusCard";

type SetupForm = {
  vault_root: string;
  create_vault: boolean;
  active_provider: string;
  providers: Record<string, {
    default_base_url: string;
    default_model: string;
    api_key_env: string;
    base_url_env: string;
    model_env: string;
  }>;
};

export function SetupPage({ data, onRefresh }: { data: ConfigStatusResponse; onRefresh?: () => void }) {
  const [editable, setEditable] = useState<SetupEditableConfigResponse | null>(null);
  const [form, setForm] = useState<SetupForm | null>(null);
  const [savedForm, setSavedForm] = useState<SetupForm | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void loadEditable();
  }, []);

  async function loadEditable() {
    const response = await getEditableConfig();
    const next = formFromEditable(response);
    setEditable(response);
    setForm(next);
    setSavedForm(next);
  }

  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(savedForm), [form, savedForm]);
  const activeProvider = form?.active_provider ? editable?.llm.providers[form.active_provider] : null;
  const providerOptions = editable
    ? editable.llm.available_providers.filter((provider) => editable.llm.providers[provider]?.type !== "fake")
    : [];
  const hasConfiguredProvider = Boolean(activeProvider && activeProvider.type !== "fake");
  const selectedProviderName = hasConfiguredProvider ? form?.active_provider ?? "" : "";

  function updateProviderField(field: keyof SetupForm["providers"][string], value: string) {
    if (!form || !selectedProviderName) return;
    setForm({
      ...form,
      providers: {
        ...form.providers,
        [selectedProviderName]: {
          ...form.providers[selectedProviderName],
          [field]: value,
        },
      },
    });
  }

  async function validate() {
    if (!form) return;
    setBusy(true);
    try {
      const response = await validateSetupConfig(patchFromForm(form));
      setMessage(response.ok ? "Validation passed" : response.errors.join(" "));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!form) return;
    setBusy(true);
    try {
      const response = await saveSetupConfig(patchFromForm(form));
      const next = formFromEditable(response.editable);
      setEditable(response.editable);
      setForm(next);
      setSavedForm(next);
      setMessage("Setup saved");
      onRefresh?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  function revert() {
    setForm(savedForm);
    setMessage("Reverted");
  }

  async function copyText(value: string | null | undefined, label: string) {
    if (!value) return;
    await navigator.clipboard?.writeText(value);
    setMessage(`${label} copied`);
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Setup</h1>
        <p className="mt-1 text-sm text-muted">Local configuration editor. Secret values are never shown or saved here.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Local vault" value={data.vault.exists ? "Ready" : "Missing"} status={data.vault.exists ? "ok" : "warn"} detail={data.vault.path} />
        <StatusCard label="Model provider" value={data.provider.opt_in_state === "env_only" ? "Configured" : "Check setup"} status={data.provider.opt_in_state === "env_only" ? "ok" : "warn"} detail="API key status is shown as present/missing only." />
        <StatusCard label="Config file" value="Loaded" status="ok" detail={data.config_path} />
      </div>
      {form && editable ? (
        <section className="space-y-5 rounded-md border border-line bg-panel p-4 shadow-subtle">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Local workspace</h2>
              <p className="text-sm text-muted">Config saves are limited to non-secret fields. YAML comments may be normalized on save.</p>
            </div>
            <div className="flex gap-2">
              {dirty ? <span className="self-center text-xs font-medium text-warn">Unsaved changes</span> : null}
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !dirty} onClick={revert} type="button">
                Revert
              </button>
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy} onClick={validate} type="button">
                Validate
              </button>
              <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !dirty} onClick={save} type="button">
                Save setup
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-ink">Vault path</span>
              <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={form.vault_root} onChange={(event) => setForm({ ...form, vault_root: event.target.value })} />
            </label>
            <label className="flex items-end gap-2 text-sm text-ink">
              <input checked={form.create_vault} onChange={(event) => setForm({ ...form, create_vault: event.target.checked })} type="checkbox" />
              Create missing vault directories on save
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-ink">Active provider</span>
              <select className="w-full rounded-md border border-line bg-white px-3 py-2" value={selectedProviderName} onChange={(event) => setForm({ ...form, active_provider: event.target.value })}>
                <option disabled value="">No model provider configured</option>
                {providerOptions.map((provider) => (
                  <option key={provider} value={provider}>{provider}</option>
                ))}
              </select>
            </label>
            <div className="rounded-md border border-line p-3 text-sm">
              {hasConfiguredProvider ? (
                <>
                  <div className="font-medium text-ink">Model provider configured</div>
                  <div className="mt-1 text-muted">Only the active provider effective config is shown below.</div>
                </>
              ) : (
                <>
                  <div className="font-medium text-ink">No model provider configured</div>
                  <div className="mt-1 text-muted">Configure a provider to generate AI drafts.</div>
                  <div className="mt-1 text-xs text-muted">You can still add and monitor sources, but draft generation requires a configured provider.</div>
                </>
              )}
            </div>
          </div>

          {activeProvider ? (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">Model</span>
                <input className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredProvider} value={hasConfiguredProvider ? form.providers[selectedProviderName]?.default_model ?? "" : ""} onChange={(event) => updateProviderField("default_model", event.target.value)} />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">Base URL</span>
                <input className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredProvider} value={hasConfiguredProvider ? form.providers[selectedProviderName]?.default_base_url ?? "" : ""} onChange={(event) => updateProviderField("default_base_url", event.target.value)} />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">API key env name</span>
                <input className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredProvider} value={hasConfiguredProvider ? form.providers[selectedProviderName]?.api_key_env ?? "" : ""} onChange={(event) => updateProviderField("api_key_env", event.target.value)} />
                {hasConfiguredProvider ? (
                  <span className="text-xs text-muted">
                    API key value: {activeProvider.api_key_secret_present && activeProvider.api_key_masked_value ? `present (${activeProvider.api_key_masked_value})` : activeProvider.api_key_status_label}
                  </span>
                ) : null}
                <button className="block text-xs text-primary disabled:text-muted" disabled={!hasConfiguredProvider} onClick={() => copyText(form.providers[selectedProviderName]?.api_key_env, "API key env name")} type="button">
                  Copy API key env name
                </button>
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">Base URL / model env names</span>
                <input className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredProvider} value={hasConfiguredProvider ? form.providers[selectedProviderName]?.base_url_env ?? "" : ""} onChange={(event) => updateProviderField("base_url_env", event.target.value)} />
                <input className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredProvider} value={hasConfiguredProvider ? form.providers[selectedProviderName]?.model_env ?? "" : ""} onChange={(event) => updateProviderField("model_env", event.target.value)} />
              </label>
              {hasConfiguredProvider ? (
                <>
                  <div className="rounded-md border border-line p-3 text-sm">
                    <div className="font-medium text-ink">Effective base URL</div>
                    <div className="mt-1 break-all text-muted">{activeProvider.effective_base_url ?? "missing"}</div>
                    <div className="mt-1 text-xs text-muted">env: {activeProvider.base_url_env_status} · {sourceLabel(activeProvider.base_url_source)}</div>
                    {activeProvider.effective_base_url ? (
                      <button className="mt-2 text-xs text-primary" onClick={() => copyText(activeProvider.effective_base_url, "Base URL")} type="button">
                        Copy base URL
                      </button>
                    ) : null}
                  </div>
                  <div className="rounded-md border border-line p-3 text-sm">
                    <div className="font-medium text-ink">Effective model</div>
                    <div className="mt-1 break-all text-muted">{activeProvider.effective_model ?? "missing"}</div>
                    <div className="mt-1 text-xs text-muted">env: {activeProvider.model_env_status} · {sourceLabel(activeProvider.model_source)}</div>
                    {activeProvider.effective_model ? (
                      <button className="mt-2 text-xs text-primary" onClick={() => copyText(activeProvider.effective_model, "Model")} type="button">
                        Copy model
                      </button>
                    ) : null}
                  </div>
                </>
              ) : null}
            </div>
          ) : null}

          <section className="rounded-md border border-line p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-ink">Default watched inbox</h2>
                <p className="mt-1 break-all text-sm font-medium text-ink">{editable.vault.root}/00-Inbox</p>
                <p className="mt-1 max-w-2xl text-sm text-muted">
                  MindForge can process files placed in this inbox. Add more files or folders from Sources.
                </p>
              </div>
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={() => { window.location.hash = "#/sources"; }} type="button">
                Manage sources
              </button>
            </div>
          </section>

          <details className="rounded-md border border-line p-3">
            <summary className="cursor-pointer text-sm font-medium text-ink">Advanced / Technical details</summary>
            <dl className="mt-3 space-y-2 text-sm text-muted">
              <div><dt className="font-medium text-ink">Provider readiness</dt><dd>{editable.llm.readiness.opt_in_state}</dd></div>
              <div><dt className="font-medium text-ink">Technical active provider</dt><dd>{editable.llm.active_provider}</dd></div>
              <div><dt className="font-medium text-ink">Raw config path</dt><dd>{editable.config_path}</dd></div>
              <div><dt className="font-medium text-ink">Token status</dt><dd>{editable.cubox.token_status}</dd></div>
              <div><dt className="font-medium text-ink">Sources & imports</dt><dd>{editable.watch_summary.detail}</dd></div>
            </dl>
          </details>
          {message ? <p className="text-sm text-primary">{message}</p> : null}
        </section>
      ) : null}
      <ConfigChecklist items={data.checklist} keys={[...data.configured_keys, ...data.missing_keys]} />
    </div>
  );
}

function sourceLabel(source: "env" | "config_default" | "missing") {
  if (source === "env") return "source: env";
  if (source === "config_default") return "source: config default";
  return "source: missing";
}

function formFromEditable(editable: SetupEditableConfigResponse): SetupForm {
  return {
    vault_root: editable.vault.root,
    create_vault: false,
    active_provider: editable.llm.active_provider,
    providers: Object.fromEntries(
      Object.entries(editable.llm.providers).map(([name, provider]) => [
        name,
        {
          default_base_url: provider.default_base_url ?? "",
          default_model: provider.default_model ?? "",
          api_key_env: provider.api_key_env ?? "",
          base_url_env: provider.base_url_env ?? "",
          model_env: provider.model_env ?? "",
        },
      ]),
    ),
  };
}

function patchFromForm(form: SetupForm): SetupConfigPatch {
  return {
    vault_root: form.vault_root,
    create_vault: form.create_vault,
    active_provider: form.active_provider,
    providers: form.providers,
  };
}
