# MCP Scripted Test Guide

## Purpose
This guide documents how to run MCP scripted-input tests without ASR, and how to avoid the common failure modes that caused long debugging cycles.

## Test Command
```
$env:DEBUG_SCRIPTED_INPUT="1"
$env:DEBUG_SCRIPTED_INPUT_FILE="C:\ssafy\공통\MCP\debug\scripted_input.txt"
$env:DEBUG_SCRIPTED_INPUT_DELAY_MS="12000"
.\venv\Scripts\python.exe .\main.py
```

## Quick Start (scripted input)
1) Ensure no stray MCP processes are running:
   - `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "\\main.py" }`
   - Stop any leftover processes (only MCP instances).

2) Verify scripted input file is clean UTF-8 (no BOM) and correct lines:
   - `C:\ssafy\공통\MCP\debug\scripted_input.txt`

3) Start MCP with scripted input env vars in the same process:
   - Use a PowerShell process that *sets env vars before running* `main.py`.
   - Example (conceptual):
     - set `DEBUG_SCRIPTED_INPUT=1`
     - set `DEBUG_SCRIPTED_INPUT_FILE=...\scripted_input.txt`
     - set `DEBUG_SCRIPTED_INPUT_DELAY_MS=12000`
     - run `C:\ssafy\공통\MCP\venv\Scripts\python.exe .\main.py`

4) Watch logs:
   - MCP log: `C:\ssafy\공통\MCP\logs\app.log`
   - AI server log: `docker logs hearbe` (filter by session id)

## Common Failure Modes (and fixes)
- Scripted input does not run
  - Cause: env vars were set in the parent shell, but MCP started in a *new* process without them.
  - Fix: set env vars inside the same PowerShell process that launches `main.py`.

- Text is garbled (e.g., "?앹닔")
  - Cause: UTF-8 BOM or wrong encoding for `scripted_input.txt`.
  - Fix: rewrite with UTF-8 no BOM.

- WebSocket disconnects mid-run
  - Cause: AI server hot-reload (WatchFiles) during test.
  - Fix: avoid editing AI files during the test run; restart MCP after any AI code edits.

- Multiple MCP instances
  - Cause: previous `main.py` is still running.
  - Fix: terminate all `main.py` processes before starting a new test.

- Extract failures on initial page load
  - Cause: search/cart extract runs before page fully settled.
  - Fix: ensure `wait` precedes extract, or increase `DEBUG_SCRIPTED_INPUT_DELAY_MS`.

## What to Capture
- Session id (from MCP log: `Connected to AI server: ws://.../ws/<session>`)
- AI server command routing logs (rule vs LLM)
- Tool calls executed (click/fill/extract)
- Final TTS output

## Expected Behavior Checklist
- Search -> extract results -> read summary.
- Select item -> product detail extract -> read product info.
- Add to cart -> cart extract -> cart summary.
- Quantity change -> plus/minus clicks (no fill/press).

## Notes
- Use only one MCP instance per test.
- Avoid editing AI code while the test is running.
- If AI server auto-reloads, restart the test from step 1.
