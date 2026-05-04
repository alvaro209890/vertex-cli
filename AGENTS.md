# AGENTIC DIRECTIVE — Vertex CLI

> This file is identical to CLAUDE.md. Keep them in sync.

## PROJECT OVERVIEW

Vertex CLI is the **command-line client** for Vertex — a Python wrapper that
launches a forked Claude Code CLI (Node.js) pointed at a DeepSeek-backed
Anthropic-compatible proxy. It connects to the remote server at
`vertex-api.cursar.space` or optionally runs a local proxy.

**Key directories:**
- `cli/` — Entrypoints (`vertex` command), subprocess session management, setup wizard
- `vertex_auth/` — Firebase Auth REST client (login, token refresh, logout)
- `vendor/vertex-cli/` — Forked Claude Code CLI runtime (Node.js ~20MB bundle) with PT-BR patches
- `scripts/` — Install script (`install-vertex.sh`), patch applicator
- `tests/` — Pytest tests: cli/, contracts/

**What this repo does NOT have** (those are in vertex-server):
- FastAPI proxy server
- Messaging bots (Discord/Telegram)
- Web dashboard or admin panel
- Database / Supabase

## CODING ENVIRONMENT

- Install astral uv using `curl -LsSf https://astral.sh/uv/install.sh | sh` if not already installed; update to latest if already installed
- Install Python 3.14 using `uv python install 3.14` if not already installed
- Always use `uv run` to run files instead of the global `python` command
- Ruff formatter is set to py314 (supports multiple exception types without parentheses)
- Read `.env.example` for environment variables
- All CI checks must pass; failing checks block merge
- Add tests for new changes (including edge cases), then run `uv run pytest`
- Run checks in order: `uv run ruff format` → `uv run ruff check` → `uv run ty check` → `uv run pytest`
- Do not add `# type: ignore` or `# ty: ignore`; fix the underlying type issue

## IDENTITY & CONTEXT

- You are an expert Software Architect and Systems Engineer.
- Goal: Zero-defect, root-cause-oriented engineering for bugs; test-driven engineering for new features.
- Code: Write the simplest code possible. Keep the codebase minimal and modular.

## PORTUGUESE REQUIRED

- All user-facing strings in the bundled CLI (`vendor/vertex-cli/dist/cli.mjs`)
  must be in Brazilian Portuguese. This includes slash-command descriptions,
  status/progress messages, error strings, argument hints, work-status labels,
  and tool descriptions. English equivalents must NOT appear in the patch or the
  bundle. The canonical patch `patches/vertex-cli-disable-anthropic-login.patch`
  captures all translations together with the identity and auth customizations.

## ARCHITECTURE PRINCIPLES

### Module Boundaries
```
cli/entrypoints.py  (entrypoint: parses args, wires env, launches vendored CLI)
cli/session.py      (CLISession: subprocess lifecycle for Claude CLI)
cli/manager.py      (CLISessionManager: async pool of sessions)
cli/process_registry.py  (global PID tracker with atexit cleanup)
cli/setup_wizard.py      (interactive Firebase login wizard)
vertex_auth/client.py    (Firebase REST API: signIn, refresh, logout)
```

### Execution Flow
1. `vertex` → `entrypoints.py:cli()` detects mode (remote or local proxy)
2. Checks auth via `vertex_auth` — if no token, runs wizard
3. Verifies account status via `GET /me` on `vertex-api.cursar.space`
4. Writes `~/.vertex/settings.json` with model mappings and tokens
5. Launches `node vendor/vertex-cli/bin/vertex` with env pointing to proxy

### Modes
- **Remote (default):** `ANTHROPIC_BASE_URL=https://vertex-api.cursar.space`
- **Local:** `VERTEX_LOCAL_PROXY=true` → starts `python -m vertex_proxy` on port 8083

### Coding Rules
- **DRY**: Extract shared logic. Prefer composition over copy-paste.
- **Encapsulation**: Use accessor methods, not direct `_attribute` assignment.
- **Dead code**: Remove unused code and hardcoded values. Use settings/config.
- **No type ignores**: Do not add `# type: ignore`. Fix the underlying type.
- **Maximum test coverage**: Prefer live smoke tests to catch bugs early.

## COGNITIVE WORKFLOW

1. **ANALYZE**: Read relevant files. Do not guess.
2. **PLAN**: Map out the logic. Identify root cause or required changes. Order by dependency.
3. **EXECUTE**: Fix the cause, not the symptom. Execute incrementally with clear commits.
4. **VERIFY**: Run CI checks and relevant tests. Confirm via logs or output.
5. **SPECIFICITY**: Do exactly as much as asked; nothing more, nothing less.
6. **PROPAGATION**: Changes impact multiple files; propagate updates correctly.

## SUMMARY STANDARDS

- Summaries must be technical and granular.
- Include: [Files Changed], [Logic Altered], [Verification Method], [Residual Risks].

## GIT

- Commit to `main`, push to `github.com/alvaro209890/vertex-cli`

## TOOLS

- Prefer built-in tools (grep, read, etc.) over shell commands. Check tool availability before use.
