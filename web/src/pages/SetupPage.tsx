import { useEffect, useMemo, useState } from "react";
import { getEditableConfig, saveSetupConfig, validateSetupConfig } from "../api/config";
import type { ConfigStatusResponse, SetupConfigPatch, SetupEditableConfigResponse } from "../api/types";
import { ConfigChecklist } from "../components/ConfigChecklist";
import { SourceAddPanel } from "../components/SourceAddPanel";
import { StatusCard } from "../components/StatusCard";

const workflowSteps = ["triage", "distill", "link_suggestion", "review_questions", "action_extraction"];

type ModelForm = {
  type: string;
  base_url: string;
  model: string;
  api_key_env: string;
  api_key_optional: boolean;
  base_url_env: string;
  model_env: string;
};

type SetupForm = {
  vault_root: string;
  create_vault: boolean;
  default_model: string;
  models: Record<string, ModelForm>;
  routing: Record<string, string>;
  routing_is_explicit: boolean;
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
  const modelIds = Object.keys(form?.models ?? {});
  const hasConfiguredModels = modelIds.length > 0;

  function updateModelField(modelId: string, field: keyof ModelForm, value: string | boolean) {
    if (!form) return;
    setForm({
      ...form,
      models: {
        ...form.models,
        [modelId]: {
          ...form.models[modelId],
          [field]: value,
        },
      },
    });
  }

  function updateRouting(step: string, modelId: string) {
    if (!form) return;
    setForm({
      ...form,
      routing_is_explicit: true,
      routing: {
        ...form.routing,
        [step]: modelId,
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
        <StatusCard label="Model config" value={data.provider.opt_in_state === "env_only" ? "Configured" : "Check setup"} status={data.provider.opt_in_state === "env_only" ? "ok" : "warn"} detail="API key status is shown as present/missing only." />
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

          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Configured models</h2>
              <p className="mt-1 text-sm text-muted">Models are user-named endpoints. Model routing decides which workflow step uses which model id.</p>
            </div>
            {editable.llm.legacy_config_detected ? (
              <div className="rounded-md border border-warn bg-amber-50 p-3 text-sm text-ink">
                Legacy LLM config detected. Save to migrate to the new llm.models/default_model/routing format.
              </div>
            ) : null}
            {editable.llm.validation_errors.length ? (
              <div className="rounded-md border border-danger bg-red-50 p-3 text-sm text-ink">
                {editable.llm.validation_errors.join(" ")}
              </div>
            ) : null}
            {hasConfiguredModels ? (
              <div className="space-y-3">
                {modelIds.map((modelId) => {
                  const item = form.models[modelId];
                  const status = editable.llm.configured_models[modelId];
                  return (
                    <article key={modelId} className="rounded-md border border-line p-3">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-xs text-muted">model id</div>
                          <div className="font-semibold text-ink">{modelId}</div>
                        </div>
                        <div className="rounded-md bg-stone-100 px-2 py-1 text-xs text-muted">API key status: {status?.api_key_secret_present && status.api_key_masked_value ? `present (${status.api_key_masked_value})` : status?.api_key_status_label ?? "missing"}</div>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">Type</span>
                          <select className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.type} onChange={(event) => updateModelField(modelId, "type", event.target.value)}>
                            <option value="openai_compatible">openai_compatible</option>
                            <option value="anthropic">anthropic</option>
                            <option value="anthropic_compatible">anthropic_compatible</option>
                          </select>
                        </label>
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">Model</span>
                          <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.model} onChange={(event) => updateModelField(modelId, "model", event.target.value)} />
                        </label>
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">Base URL</span>
                          <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.base_url} onChange={(event) => updateModelField(modelId, "base_url", event.target.value)} />
                          <span className="text-xs text-muted">{sourceText(status?.base_url_source ?? "missing")}</span>
                        </label>
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">API key env name</span>
                          <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.api_key_env} onChange={(event) => updateModelField(modelId, "api_key_env", event.target.value)} />
                          <button className="block text-xs text-primary" onClick={() => copyText(item.api_key_env, "API key env name")} type="button">
                            Copy API key env name
                          </button>
                        </label>
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">Base URL env name</span>
                          <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.base_url_env} onChange={(event) => updateModelField(modelId, "base_url_env", event.target.value)} />
                        </label>
                        <label className="space-y-1 text-sm">
                          <span className="font-medium text-ink">Model env name</span>
                          <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={item.model_env} onChange={(event) => updateModelField(modelId, "model_env", event.target.value)} />
                          <span className="text-xs text-muted">{sourceText(status?.model_source ?? "missing")}</span>
                        </label>
                        <label className="flex items-center gap-2 text-sm text-ink">
                          <input checked={item.api_key_optional} onChange={(event) => updateModelField(modelId, "api_key_optional", event.target.checked)} type="checkbox" />
                          API key optional
                        </label>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium text-ink">No model provider configured</div>
                <div className="mt-1 text-muted">Configure a model to generate AI drafts.</div>
                <div className="mt-1 text-xs text-muted">You can still add and monitor sources, but draft generation requires a configured model.</div>
              </div>
            )}
          </section>

          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Default model</h2>
              <p className="mt-1 text-sm text-muted">Workflow steps without a route use this model id.</p>
            </div>
            <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm disabled:bg-stone-100" disabled={!hasConfiguredModels} value={form.default_model} onChange={(event) => setForm({ ...form, default_model: event.target.value })}>
              {!hasConfiguredModels ? <option value="">No model provider configured</option> : null}
              {modelIds.map((modelId) => (
                <option key={modelId} value={modelId}>{modelId}</option>
              ))}
            </select>
          </section>

          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Model routing</h2>
              <p className="mt-1 text-sm text-muted">Workflow step routing maps each processing step to a configured model id.</p>
            </div>
            {!editable.llm.routing_is_explicit ? (
              <p className="rounded-md border border-line p-3 text-sm text-muted">All workflow steps use default model: {form.default_model || "missing"}</p>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2">
              {workflowSteps.map((step) => (
                <label key={step} className="space-y-1 text-sm">
                  <span className="font-medium text-ink">Workflow step: {step}</span>
                  <select className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100" disabled={!hasConfiguredModels} value={form.routing[step] ?? form.default_model} onChange={(event) => updateRouting(step, event.target.value)}>
                    {modelIds.map((modelId) => (
                      <option key={modelId} value={modelId}>{modelId}</option>
                    ))}
                  </select>
                  {form.routing[step] === form.default_model ? <span className="text-xs text-muted">uses default model</span> : null}
                </label>
              ))}
            </div>
          </section>

          <SourceAddPanel onRefresh={onRefresh} />

          <details className="rounded-md border border-line p-3">
            <summary className="cursor-pointer text-sm font-medium text-ink">Advanced / Technical details</summary>
            <dl className="mt-3 space-y-2 text-sm text-muted">
              <div><dt className="font-medium text-ink">Provider readiness</dt><dd>{editable.llm.readiness.opt_in_state}</dd></div>
              <div><dt className="font-medium text-ink">Technical internal route</dt><dd>{editable.llm.active_provider}</dd></div>
              <div><dt className="font-medium text-ink">Raw config path</dt><dd>{editable.config_path}</dd></div>
              <div><dt className="font-medium text-ink">Token status</dt><dd>{editable.cubox.token_status}</dd></div>
            </dl>
          </details>
          {message ? <p className="text-sm text-primary">{message}</p> : null}
        </section>
      ) : null}
      <ConfigChecklist items={data.checklist} keys={[...data.configured_keys, ...data.missing_keys]} />
    </div>
  );
}

function sourceText(source: "env" | "config_default" | "missing") {
  if (source === "env") return "source = env";
  if (source === "config_default") return "source = config";
  return "source = missing";
}

function formFromEditable(editable: SetupEditableConfigResponse): SetupForm {
  return {
    vault_root: editable.vault.root,
    create_vault: false,
    default_model: editable.llm.default_model ?? "",
    models: Object.fromEntries(
      Object.entries(editable.llm.configured_models).map(([modelId, model]) => [
        modelId,
        {
          type: model.type,
          base_url: model.base_url ?? "",
          model: model.model ?? "",
          api_key_env: model.api_key_env ?? "",
          api_key_optional: model.api_key_optional,
          base_url_env: model.base_url_env ?? "",
          model_env: model.model_env ?? "",
        },
      ]),
    ),
    routing: editable.llm.routing,
    routing_is_explicit: editable.llm.routing_is_explicit,
  };
}

function patchFromForm(form: SetupForm): SetupConfigPatch {
  const modelIds = Object.keys(form.models);
  return {
    vault_root: form.vault_root,
    create_vault: form.create_vault,
    default_model: modelIds.length ? form.default_model : undefined,
    models: modelIds.length ? form.models : undefined,
    routing: form.routing_is_explicit ? compactRouting(form.routing, form.default_model) : undefined,
  };
}

function compactRouting(routing: Record<string, string>, defaultModel: string) {
  return Object.fromEntries(Object.entries(routing).filter(([, modelId]) => modelId && modelId !== defaultModel));
}
