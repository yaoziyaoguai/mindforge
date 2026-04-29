# Obsidian Dogfooding Checklist

## Safety

- [ ] I used a disposable, non-sensitive vault copy.
- [ ] I did not read or create a real `.env`.
- [ ] I did not call a real LLM.
- [ ] I did not write formal Obsidian notes.
- [ ] I did not enable telemetry upload.

## Flow

- [ ] `mindforge obsidian doctor --vault <copy>` made the vault boundary clear.
- [ ] `mindforge obsidian scan --vault <copy> --limit 20` found expected notes.
- [ ] `mindforge obsidian links --vault <copy>` produced readable link output.
- [ ] `mindforge obsidian stage --vault <copy> --source <note.md> --dry-run` explained the proposed candidate.
- [ ] `mindforge obsidian stage --vault <copy> --source <note.md> --staged-export --output-dir <dir> --diff --write --confirm` wrote only staged export files.
- [ ] The staged export path is:
- [ ] The manifest path is:
- [ ] `mindforge obsidian preflight --vault <copy> --manifest <manifest.json>` returned PASS, WARNING, or BLOCKED.
- [ ] I manually inspected staged markdown and manifest before trusting the result.
- [ ] Existing formal note hashes stayed unchanged.

## Friction

- [ ] Diff preview was readable.
- [ ] include/exclude behavior matched my expectation.
- [ ] Preflight reasons were clear.
- [ ] No-write boundary was obvious.
- [ ] Unclear output should become a v0.7 patch.
- [ ] Larger workflow changes should enter the v0.8 backlog.

## Non-goals Confirmed

- [ ] No RAG / embedding was used.
- [ ] No Obsidian plugin was used.
- [ ] No Web UI / TUI was used.
- [ ] No automatic vault cleanup or wikilink rewrite happened.
