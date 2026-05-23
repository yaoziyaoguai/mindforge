import { useEffect, useMemo, useState } from "react";
import { getEditableConfig, saveSetupConfig, validateSetupConfig } from "../api/config";
import type { ConfigStatusResponse, SetupConfigPatch, SetupEditableConfigResponse } from "../api/types";
import { SourceAddPanel } from "../components/SourceAddPanel";
import { StatusCard } from "../components/StatusCard";
import { useLocale } from "../lib/i18n";
import { strategyNameLabel, strategyStatusLabel, workflowStepLabel } from "../lib/utils";

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
  wiki_model: string;
  wiki_auto_rebuild: boolean;
};

/** 新增/编辑模型时的临时编辑状态 */
type EditingModel = {
  modelId: string;
  isNew: boolean;
  form: ModelForm;
};

/** Setup 渐进披露步骤 —— 将配置表单分为 3 个逻辑步骤，降低首次配置的认知负担。
 *  只改变 UI 组织方式，不改变 provider config model、API 语义或保存逻辑。 */
type SetupStep = "models" | "sources" | "review";

function getStepLabels(t: (key: string) => string): Record<SetupStep, { label: string; description: string }> {
  return {
    models: { label: t("setup.step.models"), description: t("setup.step.models_desc") },
    sources: { label: t("setup.step.sources"), description: t("setup.step.sources_desc") },
    review: { label: t("setup.step.review"), description: t("setup.step.review_desc") },
  };
}

const STEP_ORDER: SetupStep[] = ["models", "sources", "review"];

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
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditingModel | null>(null);
  const [step, setStep] = useState<SetupStep>("models");
  const [promptPreview, setPromptPreview] = useState<{ stage: string; version: string; content: string } | null>(null);
  const { locale, t } = useLocale();
  const STEP_LABELS = getStepLabels(t);

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
      setMessage(t("setup.validation.model_id_required"));
      return;
    }
    if (isNew && modelIds.includes(newId)) {
      setMessage(t("setup.validation.model_id_exists").replace("{id}", newId!));
      return;
    }
    if (!editForm.type) {
      setMessage(t("setup.validation.type_required"));
      return;
    }
    if (!editForm.model) {
      setMessage(t("setup.validation.model_name_required"));
      return;
    }

    const nextModels = { ...form.models };

    if (isNew) {
      nextModels[newId!] = { ...editForm };
    } else if (originalId !== newId) {
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
    if (form.default_model === modelId) {
      setMessage(t("setup.validation.cannot_delete_default").replace("{id}", modelId!));
      return;
    }
    const routingRefs = Object.entries(form.routing)
      .filter(([, mid]) => mid === modelId)
      .map(([step]) => step);
    if (routingRefs.length) {
      setMessage(t("setup.validation.cannot_delete_routed").replace("{id}", modelId!).replace("{steps}", routingRefs.join(", ")));
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
      setMessage(response.ok ? t("setup.validation_passed") : response.errors.join(" "));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    const current = draftForm;
    if (!current) return;
    setSaving(true);
    setSaveError(null);
    try {
      const response = await saveSetupConfig(patchFromForm(current));
      const next = formFromEditable(response.editable);
      setEditable(response.editable);
      setForm(next);
      setSavedForm(next);
      setEditing(null);
      setMessage(t("setup.saved"));
      onRefresh?.();
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Save failed";
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  }

  function revert() {
    setForm(savedForm);
    setEditing(null);
    setMessage(t("setup.reverted"));
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">{t("setup.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("setup.subtitle")}</p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard label={t("setup.knowledge_vault")} value={data.vault.exists ? t("setup.status_ready") : t("setup.vault_auto_created")} status={data.vault.exists ? "ok" : "info"} detail={data.vault.path} />
        <StatusCard label={t("setup.model_config_status")} value={data.provider.model_setup === "ready" ? t("setup.model_configured") : t("setup.model_check_setup")} status={data.provider.model_setup === "ready" ? "ok" : "warn"} detail="API key status is shown as present/missing only." />
      </div>

      {form && editable ? (
        <section className="space-y-5 rounded-md border border-line bg-panel p-4 shadow-subtle">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">{t("setup.local_workspace")}</h2>
              <p className="text-sm text-muted">{t("setup.local_workspace_desc")}</p>
            </div>
            <div className="flex gap-2">
              {dirty ? <span className="self-center text-xs font-medium text-warn">{t("setup.unsaved")}</span> : null}
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || saving || !dirty} onClick={revert} type="button">{t("setup.revert")}</button>
              <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy || saving} onClick={validate} type="button">{t("setup.validate")}</button>
              <button
                className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50 inline-flex items-center gap-2"
                disabled={saving || !dirty}
                onClick={save}
                type="button"
              >
                {saving ? (
                  <>
                    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    {t("setup.saving")}
                  </>
                ) : (
                  t("setup.save")
                )}
              </button>
            </div>
          </div>

          {saveError ? (
            <div className="rounded-md border border-danger bg-red-50 p-3 text-sm text-ink">
              <div className="flex items-start gap-2">
                <span className="mt-0.5 font-medium text-danger">{t("setup.save_failed")}</span>
                <span className="flex-1">{saveError}</span>
                <button className="text-xs text-muted hover:text-ink" onClick={() => setSaveError(null)} type="button">{t("shared.close")}</button>
              </div>
            </div>
          ) : null}

          {/* 步骤指示器 */}
          <div className="flex gap-2 rounded-md border border-line bg-stone-50 p-3">
            {STEP_ORDER.map((s, index) => {
              const isCurrent = s === step;
              const isPast = STEP_ORDER.indexOf(step) > index;
              return (
                <button
                  key={s}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isCurrent ? "bg-primary text-white" : isPast ? "bg-green-50 text-safe border border-green-200" : "bg-white text-muted border border-line"
                  }`}
                  onClick={() => setStep(s)}
                  type="button"
                >
                  <div className="text-xs opacity-70">{t("setup.step_number")} {index + 1}</div>
                  <div>{STEP_LABELS[s].label}</div>
                </button>
              );
            })}
          </div>

          {step === "sources" && (
          <div className="rounded-md border border-line bg-stone-50 p-4">
            <div className="text-sm font-semibold text-ink">{t("setup.knowledge_vault")}</div>
            <div className="mt-2 break-all rounded-md border border-line bg-white px-3 py-2 text-sm text-ink">{form.vault_root}</div>
            <p className="mt-2 text-xs text-muted">{t("setup.knowledge_vault_desc")}</p>
          </div>
          )}

          {/* 步骤 1：连接模型 */}
          {step === "models" && (<>
          <section className="space-y-4 rounded-md border border-line p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">{t("setup.configured_models")}</h2>
                <p className="mt-1 text-sm text-muted">{t("setup.configured_models_desc")}</p>
              </div>
              <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white" onClick={startAdd} type="button" disabled={editing !== null}>
                {t("setup.add_model")}
              </button>
            </div>

            {editable.llm.legacy_config_detected ? (
              <div className="rounded-md border border-warn bg-amber-50 p-3 text-sm text-ink">
                {t("setup.legacy_detected")}
              </div>
            ) : null}

            {editable.llm.validation_errors.length ? (
              <div className="rounded-md border border-danger bg-red-50 p-3 text-sm text-ink">
                {editable.llm.validation_errors.join(" ")}
              </div>
            ) : null}

            {/* Add/Edit form */}
            {editing ? (
              <div className="rounded-md border border-line bg-stone-50 p-4">
                <h3 className="mb-3 text-sm font-semibold text-ink">{editing.isNew ? t("setup.add_model_title") : `${t("setup.edit_model")}${editing.modelId}`}</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">{t("setup.model_id")} {editing.isNew ? "*" : t("setup.model_id_readonly")}</span>
                    <input id="model-id-input" className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.modelId} onChange={(event) => setEditing({ ...editing, modelId: event.target.value })} disabled={!editing.isNew} placeholder="e.g. main, claude, openai" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">{t("setup.model_type")} *</span>
                    <select className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.type} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, type: event.target.value } })}>
                      {supportedTypes.map((tp) => <option key={tp} value={tp}>{tp}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">{t("setup.model_base_url")} *</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.base_url} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, base_url: event.target.value } })} placeholder="https://api.anthropic.com" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">{t("setup.model_name")} *</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.model} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, model: event.target.value } })} placeholder="claude-3-5-haiku-latest" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-ink">{t("setup.model_api_key")}</span>
                    <input className="w-full rounded-md border border-line bg-white px-3 py-2" value={editing.form.api_key} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, api_key: event.target.value, api_key_action: event.target.value ? "update" : "keep" } })} type="password" autoComplete="off" placeholder={editing.isNew ? t("setup.model_api_key_placeholder_new") : t("setup.model_api_key_placeholder_edit")} />
                    <span className="text-xs text-muted">{editing.isNew ? "" : t("setup.model_api_key_hint_edit")}</span>
                  </label>
                  {!editing.isNew ? (
                    <div className="flex items-center gap-2">
                      <button className="text-xs text-danger" onClick={() => setEditing({ ...editing, form: { ...editing.form, api_key: "", api_key_action: "clear" } })} type="button">
                        {t("setup.model_clear_key")}
                      </button>
                      {editing.form.api_key_action === "clear" ? <span className="text-xs font-medium text-danger">{t("setup.model_key_will_clear")}</span> : null}
                    </div>
                  ) : null}
                </div>
                <details className="mt-4 rounded-md border border-line p-2">
                  <summary className="cursor-pointer text-xs font-medium text-muted">{t("setup.model_advanced")}</summary>
                  <label className="mt-2 flex items-center gap-2 text-sm text-ink">
                    <input checked={editing.form.api_key_optional} onChange={(event) => setEditing({ ...editing, form: { ...editing.form, api_key_optional: event.target.checked } })} type="checkbox" />
                    {t("setup.model_api_key_optional")}
                  </label>
                  <p className="mt-1 text-xs text-muted">{t("setup.model_api_key_optional_hint")}</p>
                </details>
                <div className="mt-4 flex gap-2">
                  <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white" onClick={saveModelEdit} type="button">{t("setup.model_save")}</button>
                  <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink" onClick={cancelEdit} type="button">{t("setup.model_cancel")}</button>
                </div>
              </div>
            ) : null}

            {/* Model cards */}
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
                    : keySource === "demo"
                    ? "missing"
                    : "missing";
                  const currentlyEditing = editing && !editing.isNew && editing.modelId === modelId;
                  return (
                    <article key={modelId} className={`rounded-md border p-3 ${currentlyEditing ? "border-primary bg-blue-50" : "border-line"}`}>
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="font-semibold text-ink">{modelId}</div>
                          {currentlyEditing ? (
                            <span className="rounded-md bg-primary px-2 py-0.5 text-xs font-medium text-white">{t("setup.model_editing")}</span>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`rounded-md px-2 py-0.5 text-xs ${keySource === "local_secret" || keySource === "env" ? "bg-green-100 text-green-700" : "bg-stone-100 text-muted"}`}>
                            {t("setup.model_api_key")}: {apiKeyLabel}
                          </span>
                          {currentlyEditing ? (
                            <span className="text-xs text-muted">{t("setup.model_editing_label")}</span>
                          ) : (
                            <>
                              <button className="rounded border border-line px-2 py-1 text-xs font-medium text-ink hover:bg-stone-100" onClick={() => startEdit(modelId)} type="button">{t("setup.model_edit")}</button>
                              <button className="rounded border border-danger px-2 py-1 text-xs font-medium text-danger hover:bg-red-50" onClick={() => deleteModel(modelId)} type="button">{t("setup.model_delete")}</button>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-muted md:grid-cols-4">
                        <div><span className="text-xs text-muted">{t("setup.model_type")}</span><div className="text-ink">{item.type}</div></div>
                        <div><span className="text-xs text-muted">{t("setup.model_base_url")}</span><div className="truncate text-ink">{item.base_url || "—"}</div></div>
                        <div><span className="text-xs text-muted">{t("setup.model_name")}</span><div className="text-ink">{item.model}</div></div>
                        <div><span className="text-xs text-muted">{t("setup.model_is_default")}</span><div className="text-ink">{modelId === form.default_model ? t("shared.yes") : t("shared.no")}</div></div>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-md border border-line p-3 text-sm">
                <div className="font-medium text-ink">{t("setup.no_models")}</div>
                <div className="mt-1 text-muted">{t("setup.no_models_desc")}</div>
                <div className="mt-1 text-xs text-muted">{t("setup.no_models_hint")}</div>
              </div>
            )}
          </section>

          {/* Default model */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">{t("setup.default_model")}</h2>
              <p className="mt-1 text-sm text-muted">{t("setup.default_model_desc")}</p>
            </div>
            <select className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm disabled:bg-stone-100" disabled={!hasConfiguredModels} value={form.default_model} onChange={(event) => setForm({ ...form, default_model: event.target.value })}>
              {!hasConfiguredModels ? <option value="">{t("setup.no_model_configured")}</option> : null}
              {modelIds.map((modelId) => {
                return <option key={modelId} value={modelId}>{modelId}</option>;
              })}
            </select>
          </section>

          {/* Processing workflow */}
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">{t("setup.processing_workflow")}</h2>
              <p className="mt-1 text-sm text-muted">{t("setup.processing_workflow_desc")}</p>
            </div>

            {editable.llm.processing_workflow ? (
              <div className="rounded-md border border-line bg-stone-50 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted">{t("setup.workflow_active")}</div>
                    <div className="font-semibold text-ink">{strategyNameLabel(editable.llm.processing_workflow.active_strategy_label, locale)}</div>
                    <div className="mt-1 text-xs text-muted">{editable.llm.processing_workflow.active_strategy_description}</div>
                  </div>
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">{strategyStatusLabel(editable.llm.processing_workflow.active_strategy_status, locale)}</span>
                </div>
              </div>
            ) : null}

            <div className="space-y-3">
              {(editable.llm.processing_workflow?.workflow_steps ?? []).map((step) => {
                const current = form.routing[step.id] ?? form.default_model;
                const isCustomModel = form.routing_is_explicit && form.routing[step.id] && form.routing[step.id] !== form.default_model;

                return (
                  <article key={step.id} className="rounded-md border border-line p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-ink">{workflowStepLabel(step.id, locale)}</span>
                          <span className="text-xs text-muted">{step.id}</span>
                        </div>
                        <p className="mt-1 text-xs text-muted">{step.purpose}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="rounded-md border border-line bg-white px-2 py-0.5 text-xs text-primary hover:bg-stone-50" onClick={() => viewPrompt(step.id, step.prompt_version)} type="button">{t("setup.workflow_view_prompt")} ({step.prompt_version})</button>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <label className="text-xs text-muted">{t("setup.model_name")}</label>
                      <select className="rounded-md border border-line bg-white px-2 py-1 text-sm disabled:bg-stone-100" disabled={!hasConfiguredModels} value={current} onChange={(event) => updateRouting(step.id, event.target.value)}>
                        {modelIds.map((modelId) => {
                          return <option key={modelId} value={modelId}>{modelId}</option>;
                        })}
                      </select>
                      {!isCustomModel ? <span className="text-xs text-muted">{t("setup.workflow_uses_default")}</span> : null}
                    </div>
                  </article>
                );
              })}
            </div>

            {form.routing_is_explicit ? (
              <button className="text-xs text-muted hover:text-ink" onClick={() => { setForm({ ...form, routing_is_explicit: false, routing: {} }); }} type="button">
                {t("setup.workflow_reset")}
              </button>
            ) : null}

            <p className="text-xs text-muted">{t("setup.workflow_fixed_note")}</p>
          </section>
          </>)}

          {/* Prompt preview modal */}
          {promptPreview ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setPromptPreview(null)}>
              <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-md border border-line bg-white p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-ink">{t("setup.prompt_preview_title")}: {promptPreview.stage} @ {promptPreview.version}</h3>
                  <button className="text-sm text-muted hover:text-ink" onClick={() => setPromptPreview(null)} type="button">{t("setup.prompt_close")}</button>
                </div>
                <p className="text-xs text-muted mb-3">{t("setup.prompt_readonly")}</p>
                <pre className="whitespace-pre-wrap rounded-md border border-line bg-stone-50 p-4 text-sm text-ink max-h-[60vh] overflow-y-auto">{promptPreview.content}</pre>
              </div>
            </div>
          ) : null}

          {/* 步骤 2：选择知识源 */}
          {step === "sources" && (<>
          <section className="space-y-4 rounded-md border border-line p-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">{t("setup.wiki_generation")}</h2>
              <p className="mt-1 text-sm text-muted">{t("setup.wiki_generation_desc")}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-ink">{t("setup.model_wiki_synthesis")}</span>
                <select className="w-full rounded-md border border-line bg-white px-3 py-2 disabled:bg-stone-100"
                  disabled={!hasConfiguredModels}
                  value={form.wiki_model || ""}
                  onChange={(event) => setForm({ ...form, wiki_model: event.target.value })}>
                  <option value="">{t("setup.wiki_use_default")}</option>
                  {modelIds.map((modelId) => <option key={modelId} value={modelId}>{modelId}</option>)}
                </select>
                <span className="text-xs text-muted">
                  {!hasConfiguredModels
                    ? t("setup.wiki_no_model_hint")
                    : form.wiki_model
                    ? t("setup.wiki_will_use_model").replace("{modelId}", form.wiki_model)
                    : t("setup.model_wiki_fallback")}
                </span>
              </label>
              <label className="flex flex-col gap-1 text-sm text-ink">
                <span className="flex items-center gap-2">
                  <input checked={form.wiki_auto_rebuild} onChange={(event) => setForm({ ...form, wiki_auto_rebuild: event.target.checked })} type="checkbox" />
                  <span className="font-medium">{t("setup.model_wiki_auto")}</span>
                </span>
                <span className="text-xs text-muted ml-6">{t("setup.model_wiki_auto_desc")}</span>
              </label>
            </div>
          </section>

          <SourceAddPanel onRefresh={onRefresh} hasModels={hasConfiguredModels} />
          </>)}

          {/* 步骤 3：检查配置 */}
          {step === "review" && (
          <details className="rounded-md border border-line p-3">
            <summary className="cursor-pointer text-sm font-medium text-ink">{t("setup.diagnostics")}</summary>
            <div className="mt-3 space-y-4">
              <p className="text-xs text-muted">{t("setup.diagnostics_desc")}</p>
              <dl className="space-y-2 text-sm text-muted">
                <div><dt className="font-medium text-ink">{t("setup.knowledge_vault")}</dt><dd className="break-all">{editable.vault.root}</dd></div>
                <div><dt className="font-medium text-ink">{t("setup.diag_model_configured")}</dt><dd>{hasConfiguredModels ? t("shared.yes") : t("shared.no")}</dd></div>
                <div><dt className="font-medium text-ink">{t("setup.diag_secret_configured")}</dt><dd>{modelIds.some((modelId) => editable.llm.configured_models[modelId]?.api_key_secret_present) ? t("shared.yes") : t("shared.no")}</dd></div>
                <div><dt className="font-medium text-ink">{t("setup.diag_last_validation")}</dt><dd>{editable.llm.validation_errors.length ? editable.llm.validation_errors.join(" ") : t("setup.status_ready")}</dd></div>
              </dl>
            </div>
          </details>
          )}

          {/* 步骤导航按钮 */}
          <div className="flex items-center justify-between gap-3">
            <div>
              {STEP_ORDER.indexOf(step) > 0 ? (
                <button
                  className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-stone-100"
                  onClick={() => setStep(STEP_ORDER[STEP_ORDER.indexOf(step) - 1])}
                  type="button"
                >
                  {t("setup.prev_step")}
                </button>
              ) : null}
            </div>
            <div className="text-xs text-muted">
              {t("setup.step_number")} {STEP_ORDER.indexOf(step) + 1} / {STEP_ORDER.length}
            </div>
            <div>
              {STEP_ORDER.indexOf(step) < STEP_ORDER.length - 1 ? (
                <button
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white"
                  onClick={() => setStep(STEP_ORDER[STEP_ORDER.indexOf(step) + 1])}
                  type="button"
                >
                  {t("setup.next_step")}
                </button>
              ) : (
                <span className="text-xs text-muted">{t("setup.save_reminder")}</span>
              )}
            </div>
          </div>

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
    wiki_model: form.wiki_model || undefined,
    wiki_auto_rebuild_on_approve: form.wiki_auto_rebuild,
  };
}

function compactRouting(routing: Record<string, string>, defaultModel: string) {
  return Object.fromEntries(Object.entries(routing).filter(([, modelId]) => modelId && modelId !== defaultModel));
}
