# Troubleshooting

Common issues and how to resolve them.

---

## Diagnostic Entry Point

```bash
mindforge doctor
```

Checks your environment, configuration, and potential risks. Run this first when something isn't working.

---

## Common Issues

### Model cannot generate drafts

**Cause**: API key not configured for the model.

**Fix**: Open Web Setup (`mindforge web --open`), go to **Setup** → **Add model**, and add an API key for your provider. Keys are stored in the local secret store only.

### Source import failed

**Cause**: Unsupported file format, missing optional dependency, or file not found.

**Fix**: Check that the source format is supported (see [Sources](sources.md)). For PDF or DOCX, install optional dependencies: `pip install "mindforge[pdf,docx]"`. Verify the file exists at the given path.

### Scanned PDF has no text

**Cause**: The PDF contains only scanned images, not a text layer.

**Fix**: MindForge does not perform OCR. Use a PDF with an embedded text layer, or pre-process scanned documents with OCR software before importing.

### Legacy DOC unsupported

**Cause**: Binary `.doc` files from older Word versions are not supported.

**Fix**: Convert the file to `.docx` or Markdown first, then import the converted file.

### DOCX optional dependency missing

**Cause**: `python-docx` is not installed.

**Fix**: Install the optional dependency: `pip install "mindforge[docx]"` or `pip install python-docx`. Then re-import the file.

### PDF optional dependency missing

**Cause**: `pypdf` is not installed.

**Fix**: Install the optional dependency: `pip install "mindforge[pdf]"` or `pip install pypdf`. Then re-import the file.

### Wiki is empty

**Cause**: No `human_approved` cards exist yet. Wiki generates from approved cards only.

**Fix**: Process sources, review the AI drafts, and explicitly approve them (`mindforge approve <ref> --confirm`). Once approved cards exist, rebuild the Wiki (`mindforge wiki rebuild`).

### Model call failed

**Cause**: Network issue, invalid API key, provider timeout, or rate limiting.

**Fix**: Check your network connection and proxy settings. Verify the API key is valid in Web Setup. For long documents, try splitting into smaller files or increasing `timeout_seconds` in the model configuration. Check `mindforge runs show <run_id>` for the specific error.

### Web port already in use

**Cause**: Another `mindforge web` process is running on the same port.

**Fix**: Stop the existing process, or start on a different port: `mindforge web --port 8766 --open`.

### Where to check local setup without exposing secrets

**Run these safe diagnostic commands:**

```bash
mindforge status       # workspace, vault, and draft status
mindforge doctor       # environment and config diagnostics
mindforge runs list    # processing run history
mindforge runs show <id>  # detailed run status and errors
```

These commands print configuration summaries and run status without exposing API keys, secret store contents, or provider credentials.

---

## Still Stuck?

- Re-run `mindforge doctor` for a fresh diagnostic.
- Check [Sources](sources.md) for format-specific setup.
- Check [Model Setup](model-setup.md) for provider configuration.
- See the [User Guide](user-guide.md) for full workflow details.

Do not paste API keys or secret store contents into chat, issues, or logs.
