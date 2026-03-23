# AGENTS.md
Guidance for coding agents working in `dan-computer-use-mcp`.

## Scope
- Applies to the entire repository.
- No Cursor rules were found in `.cursor/rules/` or `.cursorrules`.
- No Copilot instructions were found in `.github/copilot-instructions.md`.
- `CLAUDE.md` exists and must also be followed.

## Repo Snapshot
- Project: Dan Computer Use MCP.
- Type: Python MCP server for cross-platform computer control.
- Python: 3.11+.
- Packaging: setuptools via `pyproject.toml` with a `src/` layout.
- Main package: `src/dan_computer_use_mcp`.
- Main server: `src/dan_computer_use_mcp/server.py`.
- Module entrypoint: `src/dan_computer_use_mcp/__main__.py`.
- Console script: `dan-computer-use-mcp = dan_computer_use_mcp.server:main`.
- Primary tests: `tests/test_server.py`.

## Key Files
- `pyproject.toml` - dependencies, Ruff settings, pytest settings, entrypoints.
- `src/dan_computer_use_mcp/server.py` - tool definitions, handlers, config loading, browser state, MCP wiring.
- `tests/test_server.py` - test patterns and tool-count assertions.
- `README.md` and `INSTALL.md` - user-facing setup docs.
- `mcp.json` - example client-side MCP config snippet.
- `server.json` - package/server manifest metadata.
- `run-mcp.sh`, `start-mcp.sh`, and `dan-mcp-config.json` - local launch/config helpers.

## Repo Gotchas
- Code and tests expect 30 tools. Some comments and docs still say 24.
- `src/` is the source of truth. Ignore `build/lib/` copies when reading or editing code.
- `dist/`, `build/`, `*.egg-info/`, caches, and generated artifacts are not authoritative.
- `run-mcp.sh` and `start-mcp.sh` currently hardcode local interpreter or repo paths; do not assume they are portable.
- `mcp.json` is a client config example. `server.json` is package metadata, not the runtime editor config.
- `server.py` still contains a stale `# TOOLS (24 total)` comment even though `ALL_TOOLS` contains 30 entries.
- Development may happen on macOS, but changes must preserve Windows and Linux behavior unless the task explicitly narrows platform scope.

## Setup
- Work from the repo root.
- Install editable package:
```bash
pip install -e .
```
- Install dev dependencies:
```bash
pip install -e .[dev]
```
- Validate the packaged CLI:
```bash
pipx install .
```
- Install Playwright browser runtime:
```bash
playwright install chromium
```
- Optional OCR dependency: macOS `brew install tesseract`, Ubuntu/Debian `sudo apt install tesseract-ocr`, Windows `choco install tesseract`.
- Linux window dependencies:
```bash
sudo apt install xdotool wmctrl
```

## Build, Run, Lint, Test
- Editable install / local package path:
```bash
pip install -e .
```
- Packaged CLI validation path:
```bash
pipx install .
```
- Run the server as a module:
```bash
python -m dan_computer_use_mcp
```
- Run the server via console script or launchers:
```bash
dan-computer-use-mcp
./run-mcp.sh
./start-mcp.sh
```
- Run tests:
```bash
pytest tests/ -v
pytest tests/test_server.py -v
pytest tests/test_server.py::TestServer::test_tool_count -v
pytest tests/test_server.py -k test_run_command -v
```
- Run lint:
```bash
ruff check src/dan_computer_use_mcp/
ruff check src/dan_computer_use_mcp/server.py
```

## Architecture
- The codebase is centered on `src/dan_computer_use_mcp/server.py`.
- Tool definitions are `Tool(...)` objects near the top of that module.
- Each tool should map 1:1 to `handle_<tool_name>`.
- `ALL_TOOLS` and `HANDLERS` must stay synchronized.
- `call_tool` returns `list[TextContent]` and wraps handler JSON strings in `TextContent(type="text", text=...)`.
- Global module state holds config, session actions, browser lifecycle, browser mode, and OCR availability caching.
- Blocking GUI, subprocess, filesystem, and OCR work is offloaded via `asyncio` executor calls.
- Config is loaded from `./dan-mcp-config.json`, then `~/.dan-computer-use-mcp.json`, then overridden by `DAN_MCP_*` environment variables.
- Preserve feature parity across macOS, Windows, and Linux where feasible; when parity is impossible, keep behavior explicitly gated and document the limitation in code/tests/docs touched by the change.

## Code Style
- Prefer small, targeted edits over broad refactors.
- Preserve current architecture unless the task explicitly requires structural changes.
- Keep cross-platform branches intact when changing OS-specific behavior.
- Do not simplify logic in ways that silently regress Windows or Linux branches just because development is occurring on macOS.
- Keep dangerous-command protections intact in shell execution paths.
- Use 4-space indentation, keep lines at or under 100 characters, default to ASCII, and avoid formatting churn in untouched sections.
- Prefer short docstrings and avoid comments unless they clarify non-obvious logic.
- Keep JSON-like payload keys stable and consistently ordered when practical.

## Imports
- Group imports as standard library, third-party, then local.
- Separate import groups with one blank line.
- Prefer top-level imports for normal dependencies.
- Use local imports only for optional or platform-specific code paths.
- Remove unused imports when touching a file.

## Typing
- Add explicit type hints for new helpers, handlers, and non-trivial locals when useful.
- Prefer precise types such as `dict[str, Any]`, `list[str]`, and `tuple[bool, str]`.
- Keep handler signatures consistent with the existing async pattern.
- MCP-facing handler returns should remain JSON strings, not Python dicts.

## Naming
- Use `snake_case` for functions, variables, and handlers.
- Use `UPPER_CASE` for registries and constants such as `ALL_TOOLS` and `HANDLERS`.
- Keep tool names verb-first and snake_case.
- Match handler names exactly: `tool_name` -> `handle_tool_name`.

## Async Rules
- Tool handlers should be `async def`.
- Do not block the event loop with GUI automation, subprocesses, OCR, or file-heavy work.
- Use `asyncio.get_event_loop().run_in_executor(...)` for blocking operations unless an API is already async.
- Keep Playwright usage async and reuse shared browser lifecycle helpers and globals.

## Error Handling
- Expected operational failures should return structured JSON errors, not uncaught exceptions.
- Catch specific exceptions before broad fallbacks.
- Include actionable messages for missing binaries, unsupported platforms, invalid paths, and timeouts.
- Prefer degraded behavior or clear capability errors over crashes when a platform-specific dependency is unavailable.
- Use the module logger rather than `print(...)`.
- Preserve current behavior where `call_tool` catches top-level failures and returns JSON error text.

## JSON Response Conventions
- Prefer responses that always include `"ok"`.
- Success shape: `{"ok": true, ...}`.
- Failure shape: `{"ok": false, "error": "..."}`.
- Use stable keys such as `error`, `message`, `path`, `count`, `stdout`, `stderr`, and `truncated`.
- If data is clipped, include `truncated`.

## Filesystem, Subprocesses, Logging
- Prefer `pathlib.Path` over manual path-string handling and expand user paths with `.expanduser()` when inputs may contain `~`.
- Keep path handling platform-neutral: avoid hardcoded POSIX separators, account for Windows drive letters, and normalize only when required by the tool contract.
- Only create parent directories when the tool contract requires it.
- Set sensible subprocess timeouts, avoid shell-specific syntax when possible, and handle missing executables gracefully.
- Prefer argument lists over brittle shell strings when platform quoting or escaping would differ.
- Keep subprocess environment handling minimal and explicit so macOS-only assumptions do not leak into Windows/Linux execution.
- Preserve window-management branches for macOS, Windows, and Linux; gate platform-specific binaries and APIs cleanly rather than folding behavior into one platform path.
- Keep browser automation behavior consistent across platforms by reusing shared Playwright flows, avoiding OS-specific timing hacks unless guarded, and returning the same response schema.
- When a capability depends on optional tools like `xdotool`, `wmctrl`, or OCR binaries, detect availability early and return actionable fallback/error messages.
- Reuse existing `DAN_MCP_*` environment-variable patterns for configuration.
- Record user-visible actions through `_log_action(...)` when extending tool behavior.

## Testing Guidance
- Pytest is configured in `pyproject.toml` with `asyncio_mode = auto` and `addopts = -v`.
- Async tests should use `@pytest.mark.asyncio`.
- Current tests often import handlers inside the test body and parse results with `json.loads(...)`.
- Assert both payload shape and important content.
- Update tests when changing tools, handlers, payload schemas, or tool counts.
- Prefer mocks or monkeypatching for `pyautogui`, Playwright, subprocess, filesystem, and OS integrations.
- Avoid tests that require real mouse movement, real windows, or live browser UI when a mock will do.
- When touching platform branches, add or update tests that cover both the intended platform path and fallback/error behavior for the others where practical.

## Documentation Expectations
- Keep docs aligned with `pyproject.toml`, actual entrypoints, and current behavior.
- Update docs, tests, `ALL_TOOLS`, and `HANDLERS` together when tool definitions change.
- Correct stale references to 24 tools when touching relevant docs.
- Preserve the distinction between end-user setup docs and package metadata files.

## Workflow Expectations
- Read `CLAUDE.md` before substantial changes and treat it as complementary repo guidance.
- Inspect surrounding code before editing a tool definition or handler.
- Prefer repo conventions over generic framework advice.
- Avoid unrelated refactors during focused tasks.
- Run targeted lint or tests after changes whenever feasible.
- When auditing behavior, inspect `src/` first and use tests to confirm assumptions.
