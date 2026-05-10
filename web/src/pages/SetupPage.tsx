import { useEffect, useMemo, useState } from "react";
import { getEditableConfig, saveSetupConfig, validateSetupConfig } from "../api/config";
import type { ConfigStatusResponse, SetupConfigPatch, SetupEditableConfigResponse } from "../api/types";
import { SourceAddPanel } from "../components/SourceAddPanel";
import { StatusCard } from "../components/StatusCard";

const supportedTypes = ["openai", "openai_compatible", "anthropic", "anthropic_compatible"] as const;

/** 前端模型表单 —— api_key 仅用于用户输入，永不从后端回填 raw value。 */
type ModelForm = {
  type: string;
  base_url: string;
  model: string;
  api_key_optional: boolean;
  api_key: string;
  api_key_action: "keep" | "clear" | "update";
};

type SetupForm = {
  vault_root: string;
  create_vault: boolean;
  default_model: string;
  models: Record<string, ModelForm>;
  routing: Record<string, string>;
  routing_is_explicit: boolean;
  wiki_mode: string;
  wiki_model: string;
  wiki_auto_rebuild: boolean;
};

/** 新增/编辑模型时的临时编辑状态 */
type EditingModel = {
  modelId: string;
  isNew: boolean;
  form: ModelForm;
};

function emptyModelForm(): ModelForm {
  return {
    type: "openai",
    base_url: "",
    model: "",
    api_key_optional: false,
    api_key: "",
    api_key_action: "keep",
  };
}

export function SetupPage({ data, onRefresh }: { data: ConfigStatusResponse; onRefresh?: () => void }) {
  const [editable, setEditable] = useState<SetupEditableConfigResponse | null>(null);
  const [form, setForm] = useState<SetupForm | null>(null);
  const [savedForm, setSavedForm] = useState<SetupForm | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<EditingModel | null>(null);
  const [promptPreview, setPromptPreview] = useState<{ stage: string; version: string; content: string } | null>(null);

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

  const draftForm = useMemo(() => formWithEditing(form, editing), [form, editing]);
  const dirty = useMemo(() => JSON.stringify(draftForm) !== JSON.stringify(savedForm), [draftForm, savedForm]);
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
          api_key_action: field === "api_key" && value ? "update" as const : form.models[modelId].api_key_action,
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

  function startAdd() {
    setEditing({ modelId: "", isNew: true, form: emptyModelForm() });
  }

  function startEdit(modelId: string) {
    if (!form) return;
    const existing = form.models[modelId];
    setEditing({
      modelId,
      isNew: false,
      form: {
        ...existing,
        api_key: "",
        api_key_action: "keep",
      },
    });
  }

  async function viewPrompt(stage: string, version: string) {
    try {
      const resp = await fetch(`/api/prompts/${stage}?version=${encodeURIComponent(version)}`);
      if (!resp.ok) throw new Error("Prompt not found");
      const data = await resp.json();
      setPromptPreview({ stage: data.stage, version: data.version, content: data.content });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load prompt");
    }
  }

  function cancelEdit() {
    setEditing(null);
  }

  function saveModelEdit() {
    if (!form || !editing) return;
    const { modelId: originalId, isNew, form: editForm } = editing;
    const newId = (isNew ? originalId.trim() : originalId) || originalId;

    if (!newId) {
      setMessage("Model id is required.");
      return;
    }
    if (isNew && modelIds.includes(newId)) {
      setMessage(`Model id ${newId!} already exists.`);
      return;
    }
    if (!editForm.type) {
      setMessage("Type is required.");
      return;
    }
    if (!editForm.model) {
      setMessage("Model name is required.");
      return;
    }

    const nextModels = { ...form.models };

    if (isNew) {
      nextModels[newId!] = { ...editForm };
    } else if (originalId !== newId) {
      // 允许改 id → delete old + add new
      delete nextModels[originalId];
      nextModels[newId!] = { ...editForm };
    } else {
      nextModels[originalId] = { ...editForm };
    }

    setForm({
      ...form,
      models: nextModels,
      ...(isNew && !form.default_model ? { default_model: newId! } : {}),
    });
    setEditing(null);
  }

  function deleteModel(modelId: string) {
    if (!form) return;
    // 前端预检：不允许删除 default_model 或 routing 引用的模型
    if (form.default_model === modelId) {
      setMessage(`Cannot delete model ${modelId!}: it is the default model. Change default model first.`);
      return;
    }
    const routingRefs = Object.entries(form.routing)
      .filter(([, mid]) => mid === modelId)
      .map(([step]) => step);
    if (routingRefs.length) {
      setMessage(`Cannot delete model ${modelId!}: it is referenced by routing steps: ${routingRefs.join(", ")}. Update routing first.`);
      return;
    }
    const next = { ...form.models };
    delete next[modelId];
    setForm({
      ...form,
      models: next,
      ...(form.default_model === modelId ? { default_model: Object.keys(next)[0] ?? "" } : {}),
      routing: Object.fromEntries(
        Object.entries(form.routing).map(([step, mid]) => [step, mid === modelId ? (Object.keys(next)[0] ?? "") : mid])
      ),
    });
  }

  async function validate() {
    const current = draftForm;
    if (!current) return;
    setBusy(true);
    try {
      const response = await validateSetupConfig(patchFromForm(current));
      setMessage(response.ok ? "Validation passed" : response.errors.join(" "));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    const current = draftForm;
    if (!current) return;
    setBusy(true);
    try {
      const response = await saveSetupConfig(patchFromForm(current));
      const next = formFromEditable(response.editable);
      setEditable(response.editable);
      setForm(next);
      setSavedForm(next);
      setEditing(null);
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
    setEditing(null);
    setMessage("Reverted");
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Setup</h1>
        <p className="mt-1 text-sm text-muted">Local configuration editor. API keys are stored securely — secret values are never returned or shown.</p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label="Knowledge vault" value={data.vault.exists ? "Ready" : "Created automatically"} status={data.vault.exists ? "ok" : "info"} detail={data.vault.path} />
        <StatusCard label="Model config" value={data.provider.opt_in_state === "env_only" ? "Configured" : "Check setup"} status={data.provider.opt_in_state === "env_only" ? "ok" : "warn"} detail="API key status is shown as present/missing only." />
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
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || !dirty} onClick={revert} type="button">Revert</button>
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy} onClick={validate} type="button">Validate</button>
              <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !dirty} onClick={save} type="button">Save setup</button>
            </div>
          </div>

          {/* 中文学习型说明：Vault 是 MindForge 的本地知识库根目录。普通用户只需要
          知道 approved cards、wiki、trash 会保存在这里；目录创建属于系统责任，
          不把底层目录创建开关暴露在主 UI。 */}
          <div className="rounded-md border border-line bg-stone-50 p-4">
            <div className="text-sm font-semibold text-ink">Knowledge vault</div>
            <div className="mt-2 break-all rounded-md border border-line bg-white px-3 py-2 text-sm text-ink">{form.vault_root}</div>
            <p className="mt-2 text-xs text-muted">MindForge stores approved cards, wiki, and trash here. Created automatically when needed.</p>
          </div>

          {/* ================================================================ */}
          {/* Configured models 区域 —— 主 UI */}
          {/* ================================================================ */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Configured models</h2>
                <p className="mt-1 text-sm text-muted">Models are named endpoints. Each model defines type, URL, model name, and API key.</p>
              </div>
              <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white" onClick={startAdd} type="button" disabled={editing !== null}>
                + Add model
              </button>
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

            {/* ---- Add/Edit form (inline) ---- */}
            {editing ? (
              <div className="rounded-md border border-line bg-stone-50 p-4">
                <h3 className="mb-3 text-sm font-semibold text-ink">{editing.isNew ? "Add model" : `Edit model: ${editing.modelId}`}</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">Model id {editing.isNew ? "*" : "(read-only)"}</span>
                    <input id="model-id-input" className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.modelId} onChange={(event) => setEditing({ ...editing, modelId: event.target.value })} disabled={!editing.isNew} placeholder="e.g. main, claude, openai" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">Type *</span>
                    <select className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.type} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, type: event.target.value } })}>
                      {supportedTypes.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">Base URL *</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.base_url} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, base_url: event.target.value } })} placeholder="https://api.anthropic.com" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">Model *</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.model} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, model: event.target.value } })} placeholder="claude-3-5-haiku-latest" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">API key</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.api_key} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, api_key: event.target.value, api_key_action: event.target.value ? "update" : "keep" } })} type="password" autoComplete="off" placeholder={editing.isNew ? "Enter API key" : "Leave empty to keep current key"} />
                    <span className="text-xs text-muted">{editing.isNew ? "" : "Leave empty to preserve existing API key."}</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input checked={editing.form.api_key_optional} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, api_key_optional: event.target.checked } })} type="checkbox" />
                    API key optional (local endpoints)
                  </label>
                  {!editing.isNew ? (
                    <div className="flex items-center gap-2">
                      <button className="text-xs text-danger" onClick={() => setEditing({ ...editing, form: { ...editing.form, api_key: "", api_key_action: "clear" } })} type="button">
                        Clear stored key
                      </button>
                      {editing.form.api_key_action === "clear" ? <span className="text-xs font-medium text-danger">Key will be removed on save</span> : null}
                    </div>
                  ) : null}
                </div>
                <div className="mt-4 flex gap-2">
                  <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white" onClick={saveModelEdit} type="button">Save</button>
                  <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={cancelEdit} type="button">Cancel</button>
                </div>
              </div>
            ) : null}

            {/* ---- Model cards ---- */}
            {hasConfiguredModels ? (
              <div className="space-y-3">
                {modelIds.map((modelId) => {
                  const item = form.models[modelId];
                  const status = editable.llm.configured_models[modelId];
                  const keySource = status?.api_key_source ?? "missing";
                  const apiKeyLabel = keySource === "local_secret"
                    ? `configured · ${status?.api_key_masked_value ?? "****"}`
                    : keySource === "env"
                    ? `configured outside Web · ${status?.api_key_status_label ?? ""}`
                    : "missing";
                  return (
                    <article key={modelId} className="rounded-md border border-line p-3">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="font-semibold text-ink">{modelId}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`rounded-md px-2 py-0.5 text-xs ${keySource === "local_secret" || keySource === "env" ? "bg-green-100 text-green-700" : "bg-stone-100 text-muted"}`}>
                            API key: {apiKeyLabel}
                          </span>
                          <button className="rounded border border-line px-2 py-1 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => startEdit(modelId)} type="button">Edit</button>
                          <button className="rounded border border-danger px-2 py-1 text-xs font-medium text-danger hover:bg-red-50" onClick={() => deleteModel(modelId)} type="button">Delete</button>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-muted md:grid-cols-4">
                        <div><span className="text-xs text-muted">type</span><div className="text-ink">{item.type}</div></div>
                        <div><span className="text-xs text-muted">base URL</span><div className="truncate text-ink">{item.base_url || "—"}</div></div>
                        <div><span className="text-xs text-muted">model</span><div className="text-ink">{item.model}</div></div>
                        <div><span className="text-xs text-muted">default</span><div className="text-ink">{modelId === form.default_model ? "Yes" : "No"}</div></div>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium text-ink">No model configured</div>
                <div className="mt-1 text-muted">Add a model to generate AI drafts.</div>
                <div className="mt-1 text-xs text-muted">You can still add and monitor sources, but draft generation requires a configured model.</div>
              </div>
            )}
          </section>

          {/* ================================================================ */}
          {/* Default model */}
          {/* ================================================================ */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Default model</h2>
              <p className="mt-1 text-sm text-muted">Workflow steps without an explicit route use this model.</p>
            </div>
            <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm disabled:bg-stone-100" disabled={!hasConfiguredModels} value={form.default_model} onChange={(event) => setForm({ ...form, default_model: event.target.value })}>
              {!hasConfiguredModels ? <option value="">No model configured</option> : null}
              {modelIds.map((modelId) => {
                return <option key={modelId} value={modelId}>{modelId}</option>;
              })}
            </select>
          </section>

          {/* ================================================================ */}
          {/* Processing workflow */}
          {/* ================================================================ */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Processing workflow</h2>
              <p className="mt-1 text-sm text-muted">MindForge turns sources into draft knowledge cards through a workflow. Each step has a purpose, a prompt, and a model assignment.</p>
            </div>

            {/* Active strategy */}
            {editable.llm.processing_workflow ? (
              <div className="rounded-md border border-line bg-stone-50 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted">Active workflow</div>
                    <div className="font-semibold text-ink">{editable.llm.processing_workflow.active_strategy_label}</div>
                    <div className="mt-1 text-xs text-muted">{editable.llm.processing_workflow.active_strategy_description}</div>
                  </div>
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">{editable.llm.processing_workflow.active_strategy_status}</span>
                </div>
              </div>
            ) : null}

            {/* Workflow steps */}
            <div className="space-y-3">
              {(editable.llm.processing_workflow?.workflow_steps ?? []).map((step) => {
                const current = form.routing[step.id] ?? form.default_model;
                const isCustomModel = form.routing_is_explicit && form.routing[step.id] && form.routing[step.id] !== form.default_model;

                return (
                  <article key={step.id} className="rounded-md border border-line p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-ink">{step.label}</span>
                          <span className="text-xs text-muted">{step.id}</span>
                        </div>
                        <p className="mt-1 text-xs text-muted">{step.purpose}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="rounded-md border border-line bg-white px-2 py-0.5 text-xs text-primary hover:bg-stone-50" onClick={() => viewPrompt(step.id, step.prompt_version)} type="button">View prompt ({step.prompt_version})</button>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <label className="text-xs text-muted">Model</label>
                      <select className="rounded-md border border-line bg-white px-2 py-1 text-sm disabled:bg-stone-100" disabled={!hasConfiguredModels} value={current} onChange={(event) => updateRouting(step.id, event.target.value)}>
                        {modelIds.map((modelId) => {
                          return <option key={modelId} value={modelId}>{modelId}</option>;
                        })}
                      </select>
                      {!isCustomModel ? <span className="text-xs text-muted">(uses default)</span> : null}
                    </div>
                  </article>
                );
              })}
            </div>

            {/* Reset routing */}
            {form.routing_is_explicit ? (
              <button className="text-xs text-muted hover:text-ink" onClick={() => { setForm({ ...form, routing_is_explicit: false, routing: {} }); }} type="button">
                Reset all steps to use default model
              </button>
            ) : null}

            <p className="text-xs text-muted">Workflow steps are fixed in this version. Model assignment is configurable. Click View prompt to see the prompt used by each step.</p>
          </section>

          {/* Prompt preview modal */}
          {promptPreview ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setPromptPreview(null)}>
              <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-md border border-line bg-white p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-ink">Prompt: {promptPreview.stage} @ {promptPreview.version}</h3>
                  <button className="text-sm text-muted hover:text-ink" onClick={() => setPromptPreview(null)} type="button">Close</button>
                </div>
                <p className="text-xs text-muted mb-3">Read-only — this is the prompt currently used by the workflow step.</p>
                <pre className="whitespace-pre-wrap rounded-md border border-line bg-stone-50 p-4 text-sm text-ink max-h-[60vh] overflow-y-auto">{promptPreview.content}</pre>
              </div>
            </div>
          ) : null}

          {/* ================================================================ */}
          {/* Wiki generation */}
          {/* ================================================================ */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Wiki generation</h2>
              <p className="mt-1 text-sm text-muted">Configure how MindForge builds the Main Wiki from human-approved cards. The Wiki is a derived view; source files are not modified.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">Generation mode</span>
                <select className="w-full rounded-md border border-line bg-white px-3 py-2" value={form.wiki_mode} onChange={(event) => setForm({ ...form, wiki_mode: event.target.value })}>
                  <option value="deterministic">Template summary (no model)</option>
                  <option value="llm">LLM synthesis</option>
                </select>
                <span className="text-xs text-muted">{form.wiki_mode === "deterministic"
                  ? "Fast and deterministic — builds a structured Wiki from approved cards without calling a model."
                  : "Uses a configured model to synthesize a more coherent Main Wiki from approved cards."}</span>
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">Model for LLM synthesis</span>
                <select className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100"
                  disabled={!hasConfiguredModels || form.wiki_mode === "deterministic"}
                  value={form.wiki_model || ""}
                  onChange={(event) => setForm({ ...form, wiki_model: event.target.value })}>
                  <option value="">Use default model</option>
                  {modelIds.map((modelId) => <option key={modelId} value={modelId}>{modelId}</option>)}
                </select>
                <span className="text-xs text-muted">
                  {form.wiki_mode === "deterministic"
                    ? "No model is needed for template summary mode."
                    : !hasConfiguredModels
                    ? "Add a model first to use LLM synthesis."
                    : form.wiki_model
                    ? `Will use ${form.wiki_model}.`
                    : "Falls back to default model."}
                </span>
              </label>
              <label className="flex flex-col gap-1 text-sm text-ink">
                <span className="flex items-center gap-2">
                  <input checked={form.wiki_auto_rebuild} onChange={(event) => setForm({ ...form, wiki_auto_rebuild: event.target.checked })} type="checkbox" />
                  <span className="font-medium">Auto update Wiki after approval</span>
                </span>
                <span className="text-xs text-muted ml-6">When enabled, MindForge updates the Main Wiki after each approval using the safe template summary mode. LLM synthesis is never run automatically — trigger it manually from the Wiki page.</span>
              </label>
            </div>
          </section>

          <SourceAddPanel onRefresh={onRefresh} hasModels={hasConfiguredModels} />

          {/* ================================================================ */}
          {/* Diagnostics for advanced users */}
          {/* ================================================================ */}
          <details className="rounded-md border border-line p-3">
            <summary className="cursor-pointer text-sm font-medium text-ink">Diagnostics for advanced users</summary>
            <div className="mt-3 space-y-4">
              <p className="text-xs text-muted">These are read-only diagnostics for advanced users and troubleshooting. They summarize the same user-facing setup state without exposing legacy runtime internals.</p>
              {/* 中文学习型说明：Diagnostics 不是第二套配置入口。这里只展示用户能
              理解的只读状态，避免把测试替身、历史路由或内部配置字段重新暴露为
              普通用户需要操作的产品概念。 */}
              <dl className="space-y-2 text-sm text-muted">
                <div><dt className="font-medium text-ink">Knowledge vault</dt><dd className="break-all">{editable.vault.root}</dd></div>
                <div><dt className="font-medium text-ink">Model configured</dt><dd>{hasConfiguredModels ? "Yes" : "No"}</dd></div>
                <div><dt className="font-medium text-ink">Secret configured</dt><dd>{modelIds.some((modelId) => editable.llm.configured_models[modelId]?.api_key_secret_present) ? "Yes" : "No"}</dd></div>
                <div><dt className="font-medium text-ink">Last validation result</dt><dd>{editable.llm.validation_errors.length ? editable.llm.validation_errors.join(" ") : "Ready"}</dd></div>
              </dl>
            </div>
          </details>

          {message ? <p className="text-sm text-primary">{message}</p> : null}
        </section>
      ) : null}
    </div>
  );
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
          api_key_optional: model.api_key_optional,
          api_key: "",
          api_key_action: "keep" as const,
        },
      ]),
    ),
    routing: editable.llm.routing,
    routing_is_explicit: editable.llm.routing_is_explicit,
    wiki_mode: editable.wiki?.mode ?? "deterministic",
    wiki_model: editable.wiki?.model ?? "",
    wiki_auto_rebuild: editable.wiki?.auto_rebuild_on_approve ?? false,
  };
}

function formWithEditing(form: SetupForm | null, editing: EditingModel | null): SetupForm | null {
  if (!form || !editing) return form;
  const modelId = editing.modelId.trim();
  if (!modelId) return form;
  const models = { ...form.models };
  if (!editing.isNew && modelId !== editing.modelId) {
    delete models[editing.modelId];
  }
  models[modelId] = { ...editing.form };
  return {
    ...form,
    models,
    ...(editing.isNew && !form.default_model ? { default_model: modelId } : {}),
  };
}

function patchFromForm(form: SetupForm): SetupConfigPatch {
  const modelIds = Object.keys(form.models);
  const models: Record<string, Record<string, unknown>> = {};
  for (const modelId of modelIds) {
    const m = form.models[modelId];
    models[modelId] = {
      type: m.type || undefined,
      base_url: m.base_url || undefined,
      model: m.model || undefined,
      api_key_optional: m.api_key_optional || undefined,
      api_key: m.api_key || undefined,
      api_key_action: m.api_key_action || undefined,
    };
  }
  return {
    vault_root: form.vault_root,
    create_vault: form.create_vault,
    default_model: modelIds.length && form.default_model ? form.default_model : undefined,
    models: modelIds.length ? models : undefined,
    routing: form.routing_is_explicit ? compactRouting(form.routing, form.default_model) : undefined,
    wiki_mode: form.wiki_mode || undefined,
    wiki_model: form.wiki_model || undefined,
    wiki_auto_rebuild_on_approve: form.wiki_auto_rebuild,
  };
}

function compactRouting(routing: Record<string, string>, defaultModel: string) {
  return Object.fromEntries(Object.entries(routing).filter(([, modelId]) => modelId && modelId !== defaultModel));
}
