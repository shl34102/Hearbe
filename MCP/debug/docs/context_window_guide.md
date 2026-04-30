# Context Window Guide

Purpose: minimize context usage while still diagnosing MCP/AI pipeline issues quickly.

## Minimal Files to Open (by task)

### Scripted test run
- MCP log: `C:\ssafy\공통\MCP\logs\app.log`
- AI server log: `docker logs hearbe` (filter by session id)
- Script input: `C:\ssafy\공통\MCP\debug\scripted_input.txt`

### Cart quantity / selection issues
- `services/llm/planner/cart_action.py`
- `services/llm/planner/cart_item_matcher.py`
- `services/llm/planner/selection/selection.py`
- `api/ws/handlers/text_processing/llm_pipeline_handler.py`

### Product info read issues
- `services/llm/pipelines/read/product_info.py`
- `api/ws/handlers/mcp_handler.py` (product_detail capture)
- `api/ws/handlers/text_processing/llm_pipeline_handler.py`

### Add-to-cart verification / TTS issues
- `api/ws/feedback/action_feedback.py`
- `api/ws/handlers/command_pipeline.py`

## Log Filters
- Find session id in MCP log: `Connected to AI server: ws://.../ws/<session>`
- AI server filter example: `docker logs hearbe | rg "<session>" -n`
- MCP tool calls: search for `Tool call received` and `MCP result`

## What Not to Load (unless needed)
- Full extractor files (MCP browser extractors) unless selectors are failing.
- Large temp JSON files unless verifying extraction fields.
- Unrelated flows (checkout, OCR, order list) when focusing on cart/search.

## Update Discipline
- When changing logic, update only the smallest relevant module.
- After any AI code change, expect WatchFiles reload -> restart MCP test.
- Avoid parallel MCP instances to keep logs clean.
