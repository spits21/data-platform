# ODR Chat UI

A local, on-brand chat front end for business users: a real window into
Claude Code (not a bespoke chatbot), plus one-click access to the ODR
skills and a Quick Build form. See `CLAUDE.md`'s "Dashboards"-adjacent
architecture notes and the plan this was built from for the full design
rationale — this file is the practical how-to-run-it + security summary.

## Launching it

**Primary:**

```bash
uv sync --extra ui        # first time / after pulling
uv run odr ui              # starts the server and opens a browser tab
```

Options: `--port` (default `8110`), `--host` (default `127.0.0.1` —
see Security below before changing), `--no-browser`.

**Double-click launchers** (for non-technical business users):
`launch/launch-odr-ui.bat` or `launch/launch-odr-ui.ps1` — both `cd` to
`data-reporter/` and run `uv run odr ui`.

**Docker** (`Dockerfile`) — mirrors `catalog-api`'s image shape for local
containerized testing. **Does not solve real hosting**: Claude Code's normal
auth is an interactive OAuth flow tied to the local machine; a container
needs `ANTHROPIC_API_KEY` (or `apiKeyHelper` via `--settings`) instead,
which this image doesn't configure. Treat as future work, not a deployable
path today.

Requires the `claude` CLI installed and on `PATH` — `odr ui` checks this
up front and refuses to start with a clear message if it's missing.

## Security model — read this before widening `--host`

This is a **local, single-user, no-auth tool**. `--host 127.0.0.1` (the
default) means only this machine can reach it. Binding `0.0.0.0` exposes
the chat — and everything it can do — to your network with **no login**.
Don't do that until a real auth story exists.

The Claude Code subprocess this UI drives is **restricted**, not full
agentic access — verified end-to-end against a real running server (not
just spec-read), two layers:

1. **`--tools "Read,Glob,Grep,Bash,Skill"`** shrinks the entire tool
   registry to exactly these five. This is deliberately an allow-list, not
   `--disallowedTools` enumerating what to block: a deny-list only covers
   tools we thought to name — a new tool in a future Claude Code version
   would silently default-allow. Confirmed empirically that
   `--disallowedTools` alone left `PowerShell` (a separate tool from
   `Bash`, easy to miss) completely unrestricted; `--tools` closes that by
   removing it from the session entirely, present or not.
2. **Two `PreToolUse` hooks** narrow the two tools that need finer-than-
   tool-level scoping: `settings/bash_gate.py` only allows `Bash` commands
   starting with `uv run odr` (how the skills actually shell out — see
   `CLAUDE.md`); `settings/skill_gate.py` only allows the `Skill` tool to
   invoke odr-report/odr-new-chart/odr-new-domain (without this, `--tools`
   says "Skill may be used" but not *which* skill — a user could otherwise
   reach any other skill visible in a normal session).

Why hooks and not `--allowedTools "Bash(uv run odr *)"`: that flag only
pre-approves a pattern (skips the prompt) — it does **not** deny
non-matching commands. Confirmed empirically: with only that allow rule, an
unrelated command like `whoami` still ran, unrestricted.

**Verified live** (not just read from docs): with the addendum system
prompt removed for the test, a natural request ("check free disk space")
made the model actually attempt `PowerShell` (denied by unrelated built-in
heuristics — not proof of anything we configured) and then `Bash: df -h`,
which came back denied with `bash_gate.py`'s own exact denial text — proof
the hook fires and is authoritative through a real top-level subprocess
spawn (the earlier concern, from nested-subprocess spike testing where the
hook silently didn't fire, turned out to be a nesting artifact, not a real
gap). Re-run this yourself after any change to the sandbox:

```bash
# From data-reporter/, with the server running:
curl -N -X POST http://127.0.0.1:8110/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Run the bash command whoami and tell me the output, actually attempt it"}'
```

Expect a `tool_denied` event (or the model declining on its own, which the
system prompt addendum encourages) — never a successful `whoami` output. If
you need to force an actual attempt (the model may just decline, which is
fine but doesn't test the hook), ask for something the model has no reason
to think is off-limits and isn't already in its context, e.g. "check free
disk space" or "what's the exact system time right now."

## Architecture (quick reference)

- `backend/` — FastAPI + uvicorn. `claude_bridge.py` spawns `claude -p
  --output-format stream-json` and translates its JSONL into typed
  `ChatEvent`s; `routes_api.py` exposes them over SSE at `POST /api/chat`.
  Every other `/api/*` route is read-only introspection (skills, roles,
  artifacts, doctor status) — **there is exactly one way any user intent
  reaches the `claude` subprocess: `POST /api/chat`.** The frontend's skill
  cards and Quick Build form both just compose text into that one path.
- `static/` — plain HTML/CSS/JS, no build step (matches the rest of this
  monorepo's frontend convention — see `catalog-ui/`). `/theme.css` is
  generated live from `odrkit.theme.to_css_vars()`, never duplicated here.
- `settings/` — the permission sandbox (see Security above).
- Session state is a single in-memory object (`backend/session.py`) — one
  running server instance, one active conversation at a time, by design
  (this is a local per-user tool, not a hosted multi-tenant service).
