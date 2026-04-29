# Non-sensitive Dogfooding Checklist

## Safety Pre-check

- [ ] I am using a disposable, non-sensitive vault copy.
- [ ] The vault copy contains no real secrets, tokens, client data, or private work notes.
- [ ] I did not create or use a real `.env` file for this run.
- [ ] I used `--profile fake` for processing.
- [ ] I did not call a real LLM.
- [ ] no real LLM was used.
- [ ] I did not write formal Obsidian notes.
- [ ] I did not enable telemetry upload.

## Command Loop

- [ ] `mindforge doctor --paths` was clear.
- [ ] `mindforge scan` found the expected sources.
- [ ] `mindforge process --profile fake --limit 1` generated an `ai_draft`.
- [ ] `mindforge approve list` showed a useful todo list.
- [ ] `mindforge approve show --card <card-path>` helped me decide whether to approve.
- [ ] `mindforge recall --query "..."` found approved knowledge or gave useful recovery advice.
- [ ] `mindforge review weekly` produced a usable learning task list.
- [ ] `mindforge backup export` created a safe backup without secrets.
- [ ] `mindforge obsidian stage --dry-run` previewed changes without writing formal notes.
- [ ] `mindforge today` or `mindforge next` gave a clear next action.

## Friction Notes

- [ ] Which command output was hard to understand?
- [ ] Which command did not suggest the right next action?
- [ ] Which error message should become more actionable?
- [ ] Did the source → draft → approve → recall → review loop complete?
- [ ] Should the issue become a v0.6.x patch or a v0.7 backlog item?

## Explicit Non-goals

- [ ] No RAG / embedding was used.
- [ ] No Obsidian plugin was used.
- [ ] No Web UI / TUI was used.
