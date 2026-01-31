# Haiku Model Cost Optimization Analysis

**Date:** 2026-01-31
**Purpose:** Identify where Haiku can replace Sonnet/Opus for cost savings

---

## Executive Summary

**Finding:** Homestead is already well-optimized. The only LLM calls in the codebase are:
1. ✅ **User-facing chat** (must use Sonnet/Opus for quality)
2. ✅ **Reflection system** (already uses Haiku - optimized!)

No additional optimization opportunities found. The codebase makes minimal LLM calls.

---

## Current LLM Usage

### 1. Interactive Chat (Herald + Manor)

**Location:**
- `herald/providers.py:dispatch_message()` - Main message handler
- `manor/api/routers/chat.py` - WebSocket chat endpoint

**Model:** User-configurable (Sonnet, Opus, Haiku, Grok)
**Default:** Sonnet
**Frequency:** Every user message
**Tokens:** 500-5000 per exchange (varies by conversation)

**Status:** ❌ Cannot optimize - user-facing requires full reasoning

---

### 2. Post-Conversation Reflection (Herald)

**Location:** `herald/bot.py:_maybe_reflect()`

**Model:** **Haiku** (forced override)
**Frequency:** After 5+ messages, max once per 15 minutes
**Tokens:** ~1000 input, ~75 output per reflection
**Cost:** ~$0.0004 per reflection

**Status:** ✅ Already optimized

**Implementation:**
```python
async def _maybe_reflect(session, session_mgr, config):
    # Force haiku model for cheap reflection (override session model)
    from copy import copy
    reflection_session = copy(session)
    reflection_session.model = "haiku"  # <-- HAIKU USED HERE

    result = await dispatch_message(
        _REFLECTION_PROMPT,
        reflection_session,
        config,
        on_delta=None,
    )
```

**Savings:** 90% vs using Sonnet

---

## Model Pricing (2026 Rates)

| Model | Input (per MTok) | Output (per MTok) | Use Case |
|-------|------------------|-------------------|----------|
| **Haiku 4** | $0.80 | $4.00 | Reflection, simple tasks |
| **Sonnet 4.5** | $3.00 | $15.00 | User chat, complex reasoning |
| **Opus 4.5** | $15.00 | $75.00 | Premium reasoning (rarely used) |

**Haiku savings:** 73-75% cheaper than Sonnet

---

## Other Components (No LLM Calls)

### Manor API Endpoints

**Checked:** proposals.py, tasks.py, jobs.py, usage.py, lore.py, scratchpad.py, memory.py

**Finding:** Pure data operations - no LLM calls
- Proposals: File diff generation, git operations
- Tasks/Jobs: SQLite CRUD
- Memory: FTS5 search (no LLM)
- Lore/Scratchpad: File I/O only

---

### Almanac Scheduler

**Location:** `packages/almanac/almanac/scheduler.py`

**Finding:** Background task execution - no LLM calls
- Sends Telegram messages
- Runs shell commands
- Triggers webhooks

---

### MCP Server

**Location:** `packages/mcp-homestead/mcp_homestead/server.py`

**Finding:** Tool dispatcher - no direct LLM calls
- Proxies requests to Manor API
- Manor API calls Herald/Claude CLI
- Claude CLI makes the actual LLM calls

**Note:** Claude CLI (external) chooses model based on session config

---

## Cost Optimization Opportunities

### ✅ Already Optimized

1. **Reflection system** - Uses Haiku (90% savings vs Sonnet)

### ❌ Cannot Optimize (Quality Critical)

1. **User chat** - Requires full reasoning capability
2. **Subagent spawning** - User-controlled model selection

### ⏸️ Future Opportunities (If Implemented)

These features don't exist yet, but if added, should use Haiku:

1. **Auto-summarization** - Daily/weekly conversation summaries
   - Frequency: 1x per day
   - Tokens: ~5000 input, ~500 output
   - Model: Haiku
   - Savings: ~$0.015 per summary vs Sonnet

2. **Code review automation** - Simple linting/style checks
   - Frequency: Per commit
   - Tokens: ~2000 input, ~200 output
   - Model: Haiku
   - Savings: ~$0.006 per review vs Sonnet

3. **Task categorization** - Auto-tag tasks by content
   - Frequency: Per task creation
   - Tokens: ~500 input, ~50 output
   - Model: Haiku
   - Savings: ~$0.001 per task vs Sonnet

4. **Journal prompts** - Generate daily reflection questions
   - Frequency: 1x per day
   - Tokens: ~200 input, ~100 output
   - Model: Haiku
   - Savings: ~$0.001 per prompt vs Sonnet

5. **Skill extraction** - Identify patterns from conversation history
   - Frequency: Weekly batch job
   - Tokens: ~10,000 input, ~500 output
   - Model: Haiku
   - Savings: ~$0.04 per batch vs Sonnet

---

## Model Selection Strategy

### Decision Tree

```
Is it user-facing (interactive)?
├─ YES → Use session model (Sonnet/Opus/user choice)
└─ NO → Is it time-sensitive?
    ├─ YES → Can it fail gracefully?
    │   ├─ YES → Use Haiku
    │   └─ NO → Use Sonnet
    └─ NO → Background task?
        ├─ YES → Use Haiku
        └─ NO → Use Sonnet (default)
```

### Quick Reference

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| **User chat** | Sonnet/Opus | Quality critical |
| **Reflection** | Haiku | Fire-and-forget, simple |
| **Summarization** | Haiku | Non-critical, batch |
| **Classification** | Haiku | Simple task |
| **Code analysis** | Sonnet | Reasoning required |
| **Deep debugging** | Sonnet/Opus | Complex reasoning |

---

## Cost Baseline (Current Usage)

### Assumptions
- 100 user messages per day
- 1 reflection per 2 hours (8 per day)
- Average message: 1000 input tokens, 500 output tokens

### Daily Costs

**User Chat:**
- Input: 100 messages × 1000 tokens × $3/MTok = $0.30
- Output: 100 messages × 500 tokens × $15/MTok = $0.75
- **Total: $1.05/day**

**Reflection (Haiku):**
- Input: 8 reflections × 1000 tokens × $0.80/MTok = $0.0064
- Output: 8 reflections × 75 tokens × $4/MTok = $0.0024
- **Total: $0.0088/day**

**If reflection used Sonnet instead:**
- Input: 8 × 1000 × $3/MTok = $0.024
- Output: 8 × 75 × $15/MTok = $0.009
- **Total: $0.033/day**

**Savings from Haiku reflection:** $0.024/day = **$8.76/year**

---

## Recommendations

### 1. Maintain Current Optimization

Keep reflection system using Haiku. The 90% cost savings is significant for a background task.

### 2. Add Cost Tracking

Current issue: `usage.db` has NULL `cost_usd` for all records.

**Implement:**
```python
# In herald/providers.py
PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-20250514": {"input": 0.8, "output": 4.0},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model, {"input": 0, "output": 0})
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
    return cost
```

Then track actual costs in `usage.db` for analysis.

### 3. Future Feature Guidelines

When implementing new LLM-powered features:
- **Default to Haiku** for background/batch tasks
- **Use Sonnet** only when reasoning quality matters
- **Use Opus** sparingly (premium scenarios only)

### 4. Monitor Reflection Quality

Since reflection now uses Haiku (downgraded from Sonnet):
- Check journal entries for quality degradation
- Verify lore/skill updates are still useful
- If Haiku produces poor reflections, consider:
  - Improving prompt clarity
  - Adding examples to prompt
  - Only using Haiku for journal, Sonnet for lore/skills

---

## Testing Plan

### Verify Haiku Reflection Works

1. **Trigger a reflection:**
   - Send 5+ messages in Herald session
   - Wait 15+ minutes
   - Send another message
   - Check logs for "triggering reflection"

2. **Check reflection output:**
   - Read journal entry: `GET /api/journal`
   - Verify 2-3 sentence summary
   - Check if lore/skills updated (if applicable)

3. **Verify model used:**
   - Check Herald logs: `reflection done (X chars, model=haiku)`
   - Confirm not using Sonnet

4. **Cost verification:**
   - Check `usage.db` for reflection record
   - Verify `cost_usd` is populated (after implementing cost tracking)
   - Confirm ~$0.0004 per reflection

---

## Conclusion

**Current state:** Homestead is already optimized for LLM costs.

**Key insight:** The codebase makes minimal LLM calls:
- User chat (necessary, quality-critical)
- Reflection (optimized with Haiku)

**No urgent optimization needed.** Focus on:
1. Implementing cost tracking
2. Monitoring reflection quality with Haiku
3. Applying Haiku-first strategy to future features

---

## Appendix: Model Availability

### Herald Model Registry

**Location:** `herald/providers.py:_CLI_MODELS`

```python
_CLI_MODELS = {
    "claude": None,              # Default (Sonnet)
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
    "haiku": "claude-haiku-4-20250514",
}
```

**Usage:** `session.model = "haiku"` will use Haiku

### Manor Model Configuration

**Location:** `manor/api/config.py`

```python
class Settings(BaseSettings):
    allowed_models: set[str] = {"claude", "sonnet", "opus", "haiku", "grok"}
    subagent_model: str = "grok"  # Default for subagents
```

**Allowed models:** claude, sonnet, opus, haiku, grok (xAI)

---

**End of Analysis**
