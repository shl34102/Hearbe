# LLM Read/Act Pipeline PRD (Phase 0)

## Goal
Separate "read-only response" from "action/command" generation so:
- Read-only requests respond immediately from extracted context (product_detail/cart/order_list/search_results).
- Command LLM is called only when an action is required.
- Compound requests (read + act) execute in a defined order (read → act by default).

## Background (Current Pain)
- LLM command generation timeouts cause "처리 방법 모름" even when context data exists.
- Read-only requests are routed through command generation, creating unnecessary failures.
- Mixed intents ("상품 정보 읽고 장바구니 담아") are not reliably handled.

## Requirements
1) Read-only requests must not depend on command LLM.
2) Read-only responses should be generated from session context, with optional response LLM polish.
3) Compound requests must support deterministic ordering (read-first, then act).
4) Command LLM calls should be minimized; only used for tool-required actions.
5) Migration must be incremental and low-risk (no big-bang refactor).
6) Reuse existing selectors/extractors; do not duplicate per-pipeline scraping logic.

## Non-goals (Phase 0)
- Rewriting all rules/intent logic.
- Changing MCP tools or extraction schemas.
- Full semantic parsing of arbitrary Korean commands.

## Target Architecture (Phase 0/1)

### Pipelines
- **Read Pipeline**: context → response (optional response LLM)
- **Act Pipeline**: action intent → command generation → tool calls
- **Compound Pipeline**: read + act, with ordering rules

### Minimal Orchestration
- A lightweight router chooses pipeline(s) based on detected intent flags.
- Read pipeline runs first when both read & act are present.

## Reuse Policy (Selectors/Extractors)
- **No new selectors**: continue to use `config/sites/*` + `site_manager.get_selector`.
- **No new extractors**: pipelines consume `session.context` populated by existing MCP extractors.
- **Act pipelines** should call existing command builders (`context_rules`) that already use site selectors.

## Proposed File Tree

```
services/llm/pipelines/
  __init__.py
  read/
    __init__.py
    product_info.py
    cart_summary.py        # phase 2
    order_list_summary.py  # phase 2
    search_summary.py      # phase 2
  act/
    __init__.py
    add_to_cart.py         # phase 2
    checkout.py            # phase 2
  compound/
    __init__.py
    read_then_act.py       # phase 2
  shared/
    __init__.py
    intent_splitter.py     # phase 3 (LLM or heuristic)
    context_view.py        # phase 2 (compact context for response LLM)
```

## Phased Migration Plan

### Phase 0 (Now)
**Objective:** Structure + minimal read-only product-info path
- Add pipeline directories + stubs.
- Move product-info read logic into `pipelines/read/product_info.py`.
- Keep compatibility wrapper in existing call sites.

**Files**
- Add: `services/llm/pipelines/**`
- Move/Wrap: `services/llm/planner/product_info_action.py`
- No behavior changes beyond product-info read path.

### Phase 1
**Objective:** Expand read-only coverage
- Cart summary read pipeline
- Order list summary read pipeline
- Search results summary read pipeline
- Standardize response LLM context hints (product/cart/order/search)

**Files**
- Add: `read/cart_summary.py`, `read/order_list_summary.py`, `read/search_summary.py`
- Update: `tts_text_generator.py` (context hints)
- Update: routing to call read pipeline first

### Phase 2
**Objective:** Compound handling (read + act)
- Implement compound orchestrator (`compound/read_then_act.py`)
- Detect combined intents in router (simple heuristic first)

**Status (2026-02-04):** Implemented `read_then_act` with action + read-hint heuristic and wired in pipeline handler.

**Files**
- Add: `compound/read_then_act.py`
- Update: router / pipeline handler to sequence read then act

### Phase 3
**Objective:** Intent splitter (optional LLM)
- Add `intent_splitter.py` that returns `{read, act, order}` from user text
- Use short-token LLM or lightweight heuristic for reliability

**Files**
- Add: `shared/intent_splitter.py`
- Update: router to use splitter

## Acceptance Criteria
- "상품 정보 읽어줘" responds without command LLM.
- Command LLM failures do not block read-only responses.
- Compound commands are handled deterministically (read → act).

## Risks & Mitigations
- **Risk:** Over-triggering read pipeline on action requests.
  - Mitigation: page-type gating + keyword thresholds.
- **Risk:** Response LLM hallucination.
  - Mitigation: provide compact context only, fall back to rule-based text.
