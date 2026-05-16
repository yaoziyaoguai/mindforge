# LLM Provider Configuration

Configuring LLM models in MindForge. Web Setup is the recommended path; CLI is for advanced diagnostics.

---

## Current Configuration Format

MindForge uses a three-layer model configuration: `llm.models` / `llm.default_model` / `llm.routing`.

```yaml
llm:
  default_model: main

  models:
    main:
      type: anthropic_compatible
      base_url: https://your-endpoint.example.com/anthropic
      model: your-model-name
      timeout_seconds: 120
      max_retries: 1

  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main

wiki:
  mode: llm
  model: main
  auto_rebuild_on_approve: false
```

### Semantics

| Field | Description |
|-------|-------------|
| `llm.models` | Available model pool — each model id maps to endpoint + protocol + model name |
| `llm.default_model` | Default model for all workflow steps |
| `llm.routing` | Optional per-step model assignment. Missing steps fall back to default_model |
| `timeout_seconds` | Single HTTP request timeout (default: 120s) |
| `max_retries` | Limited retries per call (default: 1) |
| `wiki.model` | Model id for Wiki LLM synthesis |
| `wiki.auto_rebuild_on_approve` | Default false. If enabled, triggers Wiki rebuild on approve |

---

## Web Setup (Recommended)

1. Start `mindforge web`, open Setup page
2. Click **+ Add model**
3. Fill in: Model id, Type, Base URL, Model, API key
4. Save

Web Setup also supports:
- Default model selection
- Per-step model assignment in Processing Workflow
- Wiki generation mode and model configuration

---

## Supported Model Types

| Type | Protocol | Use Case |
|------|----------|----------|
| `anthropic` | Native Anthropic Messages API | Direct Anthropic Claude |
| `anthropic_compatible` | Anthropic-compatible | DashScope, OpenRouter |
| `openai` | OpenAI Chat Completions API | Direct OpenAI |
| `openai_compatible` | OpenAI Chat Completions-compatible | Ollama, LM Studio, DeepSeek |

Local models (Ollama, LM Studio) use `openai_compatible` + `api_key_optional: true`.

---

## API Key Storage

API keys entered via Web Setup are stored in the **local secret store**:

- Path: `.mindforge/secrets.json`
- Covered by `.gitignore` (`.mindforge/` rule)
- API key is **never written to YAML config**
- Web API returns **masked values only** (e.g., `sk-****abcd`)

---

## Provider Types

| type field | Module | Protocol |
|------------|--------|----------|
| `openai` | `llm/openai_compatible.py` | `POST /chat/completions` |
| `openai_compatible` | `llm/openai_compatible.py` | `POST /chat/completions` |
| `anthropic` | `llm/anthropic_compatible.py` | `POST /v1/messages` |
| `anthropic_compatible` | `llm/anthropic_compatible.py` | `POST /v1/messages` |

---

## Processing Workflow

Five-step Knowledge Card Workflow:

| Step | Description |
|------|-------------|
| Triage | Evaluate source value |
| Distill | Extract core knowledge |
| Link Suggestion | Suggest related topics |
| Review Questions | Generate review questions |
| Action Extraction | Extract action items |

Each step can use a different model via routing.

---

## Safety

| Principle | Implementation |
|-----------|---------------|
| API key not in YAML | Web save never writes api_key; raw key in secret store only |
| API key not in Git | `.mindforge/` gitignored |
| API key not in frontend | API returns masked key only |
| Provider never logs key | Error messages exclude raw key |

---

## Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Model can't generate draft | Missing API key | Add key in Web Setup |
| `Provider failure` | Provider construction failed | Check type/base_url/model in Setup |
| `HTTP 401/403` | Wrong/expired API key | Check key on provider platform |

---

## Anti-Patterns

- ❌ Writing API keys in YAML config, commit messages, issues, or chat
- ❌ Branching on `provider_type` in business code
- ❌ Exposing prompt text or LLM response text as error messages
