# ~/.claude/ Directory Investigation

**Date:** 2026-01-31
**Total Size:** 194 MB
**Purpose:** Understand what's consuming space and if it needs backup

---

## Size Breakdown

```
182 MB  - projects/               # Session transcripts (384 JSONL files = 150.7 MB)
7.1 MB  - debug/                  # Debug logs
5.1 MB  - file-history/           # File edit history
1.5 MB  - todos/                  # Todo lists per session
52 KB   - session-env/            # Session environment vars
48 KB   - plans/                  # Plan mode outputs
44 KB   - statsig/                # Feature flags/telemetry
32 KB   - shell-snapshots/        # Shell state
12 KB   - ide/                    # IDE integration
4 KB    - telemetry/              # Usage telemetry
4 KB    - stats-cache.json        # Stats cache
---
194 MB  TOTAL
```

---

## Key Findings

### 1. Session Transcripts (150.7 MB of 182 MB)

**Location:** `~/.claude/projects/*/subagents/*.jsonl`

**384 JSONL files** containing conversation transcripts and agent outputs.

**Breakdown by project:**
- `/home/milo/` (117 MB) - Most transcripts here
- `/home/milo/projects/personal/` (49 MB)
- `/home/milo/projects/personal/homestead/packages/herald/` (12 MB)
- `/home/milo/council/` (5.5 MB)
- Other projects (< 1 MB each)

**Sample file:** `agent-a620fba.jsonl` (172 KB)

These are Claude CLI session transcripts from subagents (explore, plan, general-purpose agents).

---

## Backup Recommendations

### ❌ DO NOT BACKUP

**Reason:** All transcripts are **regenerable** or **not critical**.

- Session transcripts are ephemeral work artifacts
- Debugging logs are only useful during active debugging
- File history is reconstructable from git
- Todos are tracked in homestead tasks.db now

### ✅ SAFE TO DELETE

Can nuke `~/.claude/` entirely on fresh server without losing critical data.

**Exception:** If there's auth/config in `.claude.json`, back that up separately (just 3.5 KB).

---

## .claude.json Contents

**Location:** `~/.claude/.claude.json`
**Size:** 3.5 KB (+ 5 backup copies @ 3.5 KB each)

**Contains:**
- Claude CLI auth tokens (session keys)
- User preferences
- Model settings

**Backup strategy:** Export auth separately, or just re-login on fresh server.

---

## Reflection System Analysis

### Current Implementation

**Added in:** `herald/bot.py` lines 66-116
**Trigger:** After 5+ messages in a session
**Cooldown:** 5 minutes between reflections per session
**Model:** Uses `dispatch_message()` (respects session model, probably Sonnet)

**Prompt:**
```
Briefly reflect on this conversation.
If you learned something about the user's preferences or context, update lore/user.md via write_lore.
If you developed a useful pattern or workflow, create a skill via write_skill.
Write a concise journal entry via write_journal summarizing what happened.
Keep it short — 2-3 sentences max. Do NOT send any messages to the user.
```

**Execution:** Fire-and-forget async task (non-blocking)

---

### Token Usage Concerns

**Current data:**
- 211 total usage records in usage.db
- **All have NULL cost_usd** (cost tracking not implemented yet!)
- 6,097 input tokens / 6,635 output tokens total (all time)

**Cannot measure reflection cost yet** because:
1. System just added (no reflections triggered yet)
2. Cost tracking returns NULL (not implemented)

**Expected cost per reflection:**
- Prompt: ~50 tokens
- Context: Session transcript (varies, 500-2000 tokens?)
- Response: 2-3 sentences (~50-100 tokens)
- **Estimate: 600-2150 tokens total per reflection**

---

### Frequency Analysis

**Trigger conditions:**
1. Session has 5+ messages ✓
2. 5 minutes passed since last reflection ✓

**Scenario: Active conversation**
- User sends 10 messages over 30 minutes
- Reflection triggers at message 5 (0 min)
- Reflection triggers at message 10 (if >5 min passed)
- **Max: 1 reflection per 5 minutes**

**Scenario: Long session**
- 50 messages over 2 hours
- Reflections at: 5 min, 10 min, 15 min... (every 5 min)
- **Max: 24 reflections per 2-hour session**

**Cost estimate (Sonnet 4.5 pricing):**
- Input: $3/MTok, Output: $15/MTok
- Per reflection: ~1000 tokens in, ~75 tokens out
- Cost: $0.003 + $0.0011 = **~$0.004 per reflection**
- 24 reflections = **~$0.10 per 2-hour session**

---

### Issues & Recommendations

#### ❌ Issue 1: Too Frequent for Long Sessions

**Problem:** Every 5 minutes during active conversation
**Impact:** 24 reflections in 2-hour coding session = wasted tokens/cost

**Fix:** Increase cooldown to 15-30 minutes, or trigger on session pause (no messages for 5 min)

---

#### ❌ Issue 2: Uses Session Model (Probably Sonnet)

**Problem:** Code comment says "Use haiku for cheap reflection" but actually calls `dispatch_message()` which uses session model
**Impact:** If session is Sonnet, reflection costs 10x more than Haiku

**Current code:**
```python
# Use haiku for cheap reflection
result = await dispatch_message(
    _REFLECTION_PROMPT,
    session,        # <-- Uses session model, not haiku!
    config,
    on_delta=None,
)
```

**Fix:** Force haiku model:
```python
# Override session model to use haiku
temp_session = copy(session)
temp_session.model = "haiku"
result = await dispatch_message(
    _REFLECTION_PROMPT,
    temp_session,
    config,
    on_delta=None,
)
```

---

#### ❌ Issue 3: No Cost Tracking

**Problem:** `cost_usd` is always NULL in usage.db
**Impact:** Can't measure actual reflection cost

**Fix:** Implement cost calculation in usage reporting (herald/bot.py:41-63)

---

#### ✅ Good: Fire-and-Forget

**Benefit:** Non-blocking, doesn't delay user responses
**Implementation:** `asyncio.create_task(_maybe_reflect(...))` at line 294

---

### Recommended Changes

#### 1. Use Haiku for Reflections

```python
async def _maybe_reflect(
    session: "SessionMeta",
    session_mgr: "SessionManager",
    config: "Config",
) -> None:
    # ... existing cooldown logic ...

    log.info("session=%s triggering reflection (msgs=%d)", session.name, session.message_count)

    # Force haiku for cheap reflection
    from copy import copy
    reflection_session = copy(session)
    reflection_session.model = "haiku"  # <-- Force haiku

    result = await dispatch_message(
        _REFLECTION_PROMPT,
        reflection_session,  # <-- Use temp session
        config,
        on_delta=None,
    )
    # ...
```

**Savings:** Haiku is ~10x cheaper than Sonnet
- Sonnet reflection: ~$0.004
- Haiku reflection: ~$0.0004
- **90% cost reduction**

---

#### 2. Adjust Frequency

**Option A: Longer cooldown**
```python
_REFLECTION_COOLDOWN_SECONDS = 900  # 15 minutes (was 5)
```

**Option B: Trigger on session end/pause**
```python
# Add to session timeout handler, not every N messages
# Reflect when session goes idle for 5+ minutes
```

**Recommendation:** Option B - reflect once when conversation naturally pauses, not during active coding.

---

#### 3. Add Cost Tracking

Implement cost calculation based on model pricing:
```python
# In _report_usage()
PRICING = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},  # per MTok
    "claude-haiku-4": {"input": 0.8, "output": 4.0},
    # ...
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model, {"input": 0, "output": 0})
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
    return cost
```

---

## Summary

### ~/.claude/ Directory

**Size:** 194 MB (mostly session transcripts)
**Backup:** ❌ NOT NEEDED - all regenerable
**Action:** Safe to nuke on fresh server

### Reflection System

**Status:** Just added, not triggered yet
**Frequency:** Too high (every 5 min) - will spike tokens in long sessions
**Model:** Uses session model (Sonnet) instead of Haiku - costs 10x more
**Cost tracking:** Not implemented - can't measure actual impact

**Recommendations:**
1. ✅ Force Haiku model (90% cost savings)
2. ✅ Reduce frequency (15 min cooldown or session-pause trigger)
3. ✅ Implement cost tracking to measure actual usage

**Expected cost after fixes:**
- Haiku reflection: ~$0.0004 each
- 1-2 reflections per hour-long session
- **~$0.001 per session** (negligible)

---

## Next Steps

1. ✅ Update backup-and-migration-strategy.md to exclude ~/.claude/
2. ⏳ Test reflection system with current settings (see if it triggers)
3. ⏳ Implement recommended fixes if token usage is too high
4. ⏳ Add cost tracking to usage.db

---

**End of Investigation**
