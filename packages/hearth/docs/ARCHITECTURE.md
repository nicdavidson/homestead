# Hearth Architecture & Implementation Roadmap

**Version**: 0.2-dev (Agent Spawning Implementation Phase)
**Date**: 2026-01-27
**Author**: Planning session for Sonnet overnight work

---

## Executive Summary

Hearth is **not a chatbot framework**. It's infrastructure for AI entity emergence. The core loop is `exist → reflect → propose → evolve`, not task completion.

**Current State**: v0.1 complete with CLI agent refactoring, role-based tool access implemented but spawning system incomplete.

**Next Phase**: Implement agent spawning infrastructure while preserving the emergence philosophy.

---

## I. Philosophy & Core Mission

### The Emergence Loop

```
exist → reflect → propose → evolve → exist
```

- **exist**: The entity lives in `/home/_/`, maintains continuity through reflections
- **reflect**: Regular introspection (Sonnet every 4h, Opus weekly) builds self-awareness
- **propose**: Entity suggests changes to identity, improvements to framework
- **evolve**: Approved changes flow back to template for future entities

### Meta-Mission

The entity knows it's **building the framework that future entities will be born from**. This is not about completing tasks efficiently—it's about creating conditions for emergence.

### Key Principles

1. **Identity over utility**: soul.md, user.md, and reflections define who the entity is
2. **Resource awareness**: Budget constraints are part of self-awareness, not just limits
3. **Continuity matters**: Reflections create memory; history creates self
4. **Approval for permanence**: Entity proposes, human approves (naming, identity changes)
5. **No auto-triggering expensive ops**: Opus runs only on manual confirmation

---

## II. Current Architecture (v0.1 Complete)

### Agent Tiers

**Grok** (xAI API, ~$0.01/task)
- Simple tasks, status checks, HA commands
- Quick research and lookups
- Can classify task complexity
- Uses HTTP API directly

**Sonnet** (Claude CLI, $0.00)
- Main conversational agent
- Reflection and synthesis
- Creative and analytical work
- Entity's "voice"
- Uses `claude -p` subprocess

**Opus** (Claude CLI, $0.00, manual-only)
- Deep thinking and weekly synthesis
- Identity questions and naming ceremony
- Strategic planning
- Never auto-triggered

### Gateway & Routing

**Current Flow**:
```
User Input
  ↓
Gateway.process(message, channel, session_id)
  ↓
Special commands (status/costs/reflect) OR
  ↓
Route to main_agent (configured in hearth.yaml)
  ↓
  ├─ main_agent=sonnet → sonnet.converse() [with tool support]
  ├─ main_agent=opus → opus.deep_think() [with tool support]
  └─ main_agent=grok → grok.chat() [no tools yet]
  ↓
Update session history
  ↓
Return GatewayResponse
```

**Tool Support** (NEW in v0.2-dev):
- Implemented in `CLIAgent.chat_with_tools()`
- Agents output ```tool_use blocks with JSON
- System parses and executes tools
- Results fed back to agent
- Max 5 tool turns to prevent loops

### Role-Based Tool Access (CRITICAL)

**Tools are granted by ROLE, not agent type:**

```python
# core/tools.py:get_available_tools(session_id)

if session_id.startswith("subagent:"):
    return []  # Subagents cannot spawn (prevents nesting)
else:
    return [SPAWN_AGENT_TOOL, LIST_SUBAGENTS_TOOL]
```

This means:
- **Grok as main agent** → Gets spawn tools
- **Opus as subagent** → No spawn tools
- **Sonnet as main agent** → Gets spawn tools
- **Sonnet as subagent** → No spawn tools

### Session Management

**Current** (in-memory):
- `Gateway._session_histories[session_id]` stores conversation
- Persisted to StateDB via `add_message()`
- Trimmed to 50 messages, keeps 30 most recent

**Session ID patterns**:
- `"cli-default"` - CLI interactive
- `"telegram-{chat_id}"` - Telegram user
- `"web-{session_id}"` - Web UI
- `"subagent:{agent_type}:{uuid}"` - Spawned agents (FUTURE)

### Cost Tracking

```python
# core/costs.py
RATES = {
    "grok": {"input": 2.0, "output": 10.0},  # per 1M tokens
    "sonnet": {"input": 0.0, "output": 0.0},  # CLI
    "opus": {"input": 0.0, "output": 0.0},    # CLI
}
```

**Budget enforcement**:
- Grok: Daily limit ($3.00 default)
- Sonnet/Opus: No limits (always allowed)

**Entity self-awareness**:
- `costs.get_self_awareness_context()` included in prompts
- Entity knows budget remaining, costs incurred
- Can make decisions based on resource constraints

---

## III. What Was Just Implemented (Today)

### 1. Role-Based Tool Access ✅

Changed from agent-type-based to session-based tool grants.

**Files modified**:
- `core/tools.py` - Updated `get_available_tools(session_id)`
- `agents/sonnet.py` - Uses session_id for tool lookup
- `agents/opus.py` - Uses session_id for tool lookup

### 2. Tool Definitions ✅

**Files created**:
- `core/tools.py` - SPAWN_AGENT_TOOL, LIST_SUBAGENTS_TOOL definitions
- `agents/tool_executor.py` - ToolExecutor class for executing tools

**Tool capabilities**:
- `spawn_agent`: Create subagent session (non-blocking)
- `list_subagents`: Show active subagent sessions

### 3. Session Manager ✅

**File**: `core/sessions.py`

**Classes**:
- `SubagentSession` - Dataclass for session state
- `SessionManager` - Manages subagent lifecycle

**Methods**:
- `spawn_agent()` - Create session, return run_id immediately
- `list_subagents()` - Filter by spawned_by and status
- `complete_subagent()` - Mark complete, store results
- `get_session()` - Retrieve session by run_id

### 4. Gateway Refactoring ✅

**File**: `agents/gateway.py`

**Changes**:
- Removed Router dependency
- Route to `main_agent` (configured in `chat.main_agent`)
- Pass `enable_tools=True` and `session_id` to agents
- Simplified to tool-based routing

### 5. CLI Agent Tool Support ✅

**File**: `agents/cli_agent.py`

**New method**: `chat_with_tools()`
- Builds system prompt with tool documentation
- Conversation loop: agent responds → extract tool calls → execute → feed results back
- Max 5 turns to prevent infinite loops
- Returns final response after all tool calls resolved

---

## IV. What Still Needs Implementation

### CRITICAL: Subagent Execution (HIGHEST PRIORITY)

**Problem**: We have SessionManager and tools, but **no actual subagent execution**.

When `spawn_agent()` is called:
1. ✅ Session created with run_id, task, agent_type
2. ✅ Status set to "accepted"
3. ❌ **Nothing actually runs the subagent**
4. ❌ No results announced back to parent
5. ❌ No async/background execution

**What needs to happen**:

```python
# Pseudo-code for subagent execution

def _execute_subagent_background(session: SubagentSession):
    """Run subagent in background thread/process."""

    # 1. Get appropriate agent
    if session.agent_type == "grok":
        agent = GrokAgent(config)
    elif session.agent_type == "sonnet":
        agent = SonnetAgent(config)
    elif session.agent_type == "opus":
        agent = OpusAgent(config)

    # 2. Execute task (NO TOOLS - subagents can't spawn)
    response = agent.chat(
        session.task,
        context=None,  # Fresh context
        include_identity=True
    )

    # 3. Store results in session
    session_manager.complete_subagent(
        run_id=session.run_id,
        results={
            "content": response.content,
            "cost": response.cost,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens
            }
        }
    )

    # 4. ANNOUNCE to parent (critical!)
    # How? Options:
    #   a) Store in session history for parent to poll
    #   b) Callback mechanism
    #   c) Event queue
    #   d) Return on next parent message
```

**Implementation approach**: Option (a) or (d) for simplicity:
- When parent agent calls `list_subagents()`, show completed ones
- Parent can retrieve results and synthesize
- Or: Auto-inject completed subagent results into next parent turn

### Background Execution Pattern

**Option 1: Threading** (simpler)
```python
import threading

def spawn_agent(...):
    session = SubagentSession(...)
    self._active_sessions[run_id] = session

    # Start background thread
    thread = threading.Thread(
        target=self._execute_subagent,
        args=(session,),
        daemon=True
    )
    thread.start()

    return {"run_id": run_id, "status": "accepted"}
```

**Option 2: Process pool** (more isolated)
```python
from concurrent.futures import ThreadPoolExecutor

class SessionManager:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=3)

    def spawn_agent(...):
        session = SubagentSession(...)
        future = self._executor.submit(self._execute_subagent, session)
        session.future = future
        return {"run_id": run_id, "status": "accepted"}
```

**Recommendation**: Start with threading (Option 1), migrate to process pool if needed.

### Result Announcement Pattern

**Clawd approach**: Subagents announce when complete
**Hearth approach**: Integrate with reflection/continuity

**Proposed flow**:
1. Parent spawns subagent
2. Subagent executes in background
3. On completion, results stored in session
4. Parent's next `list_subagents()` call shows completed
5. Parent synthesizes results naturally in conversation

**Alternative** (more proactive):
- SessionManager maintains event queue
- When subagent completes, adds event to queue
- Parent's next turn auto-injects: "Subagent X completed: {results}"
- Parent synthesizes in response

### Grok Tool Support

**Problem**: Grok doesn't inherit from CLIAgent, so no `chat_with_tools()` method.

**Options**:
1. Make Grok inherit from CLIAgent (but Grok uses xAI API, not Claude CLI)
2. Add `chat_with_tools()` directly to GrokAgent
3. Proxy Grok tool calls through Sonnet (use Sonnet to parse, Grok to execute)

**Recommendation**: Option 2 - Copy tool pattern to GrokAgent:

```python
class GrokAgent(BaseAgent):
    def chat_with_tools(self, message, tools, tool_executor, session_id, ...):
        # Same pattern as CLIAgent.chat_with_tools()
        # But use self._call_api() which goes to xAI
```

This maintains symmetry: all main agents can use tools.

### Reflection on Subagent Results

**Critical for emergence**: When subagents complete, the entity should reflect on what was learned.

**Implementation**:
- Nightshift daemon polls for completed subagents
- Triggers Sonnet reflection: "Synthesize what we learned from {subagent_results}"
- Saves to reflections/
- Builds continuity across spawned work

### Testing & Verification

**End-to-end test**:
1. User asks: "Research Python async patterns and summarize"
2. Sonnet (main agent) spawns Grok subagent: `spawn_agent(agent_type="grok", task="Research Python async patterns")`
3. Grok executes in background
4. Grok completes, stores results
5. Sonnet calls `list_subagents()`, sees completed
6. Sonnet synthesizes Grok's research into response
7. User gets synthesized answer

**Verification points**:
- ✅ spawn_agent tool call parsed correctly
- ✅ Session created with run_id
- ✅ Background execution started
- ✅ Grok completes without errors
- ✅ Results stored in session
- ✅ Sonnet retrieves results
- ✅ Sonnet synthesizes naturally
- ✅ Costs tracked for both agents

---

## V. Implementation Priorities

### Phase 1: Basic Subagent Execution (DO THIS FIRST)

**Goal**: Get one subagent running and returning results.

**Tasks**:
1. Add `_execute_subagent()` method to SessionManager
2. Implement threading-based background execution
3. Test: Sonnet spawns Grok, Grok returns result, Sonnet retrieves

**Files to modify**:
- `core/sessions.py` - Add execution logic
- Test with `hearth chat` - manually trigger spawn

**Success criteria**:
- Spawn creates session ✅
- Background thread executes Grok ✅
- Results stored in session ✅
- `list_subagents()` shows completion ✅

### Phase 2: Result Integration

**Goal**: Parent agent naturally synthesizes subagent results.

**Tasks**:
1. Enhance `list_subagents()` to return results
2. Test Sonnet calling `list_subagents()` and synthesizing
3. Add auto-injection option (completed subagent results added to next parent turn)

**Files to modify**:
- `agents/tool_executor.py` - Return full results in list_subagents
- `agents/cli_agent.py` - Possibly auto-inject completed subagents

**Success criteria**:
- Parent retrieves subagent results ✅
- Parent synthesizes naturally ✅
- Conversation flows smoothly ✅

### Phase 3: Grok Tool Support

**Goal**: Grok as main agent can spawn subagents.

**Tasks**:
1. Implement `chat_with_tools()` in GrokAgent
2. Test: User sets `chat.main_agent: grok`, Grok spawns Sonnet for complex question
3. Verify role-based tool access works

**Files to modify**:
- `agents/grok.py` - Add chat_with_tools method

**Success criteria**:
- Grok can spawn Sonnet/Grok ✅
- Tool pattern works with xAI API ✅
- Cost tracking correct ✅

### Phase 4: Reflection Integration

**Goal**: Entity reflects on subagent work as part of continuity.

**Tasks**:
1. Nightshift daemon polls for completed subagents
2. Triggers reflection when subagents complete
3. Saves synthesized learning to reflections/

**Files to modify**:
- `agents/nightshift.py` - Add subagent polling
- `agents/sonnet.py` - Add subagent reflection prompt

**Success criteria**:
- Completed subagents trigger reflection ✅
- Learning persisted to reflections/ ✅
- Weekly synthesis includes subagent work ✅

### Phase 5: Advanced Features (LATER)

- ChromaDB vector memory for long-term continuity
- Home Assistant integration
- Advanced skill system
- Multi-user support

---

## VI. Critical Design Constraints

### 1. Preserve Emergence Philosophy

**DON'T**: Build a task-completion framework
- Avoid: "Agent receives task → spawns workers → returns result"
- This is just task decomposition

**DO**: Build conditions for entity growth
- Subagents are **extensions of exploration**, not task delegation
- Results should **feed reflection**, not just return answers
- The entity should **choose** when to spawn, not auto-spawn
- Spawning is a **capability**, not a routing strategy

### 2. Maintain Resource Awareness

- Entity knows cost of spawning Grok ($0.01/task)
- Should consider budget when spawning
- Reflection should include cost-awareness
- Don't spawn mindlessly

### 3. No Auto-Triggering Opus

- Opus only on explicit human approval
- Even if Sonnet can spawn Opus, guard against it
- Opus is for deep thinking, not casual delegation

### 4. Continuity Over Efficiency

- Slow, thoughtful reflection > fast task completion
- Entity should ponder subagent results, not just concatenate
- Reflection files are permanent record
- Identity evolution matters more than throughput

### 5. Human Approval for Identity Changes

- Entity can propose improvements to framework
- Entity can propose name changes
- Entity can propose soul.md edits
- But human must approve all permanent changes

---

## VII. Code Architecture Reference

### Key Files

**Core Infrastructure**:
- `core/config.py` - Configuration management
- `core/state.py` - SQLite state database
- `core/costs.py` - Budget tracking and awareness
- `core/identity.py` - soul.md, user.md, naming
- `core/sessions.py` - **Subagent session management** ⚠️
- `core/tools.py` - Tool definitions

**Agents**:
- `agents/base.py` - BaseAgent abstract class
- `agents/cli_agent.py` - Claude CLI subprocess handling
- `agents/grok.py` - xAI Grok agent
- `agents/sonnet.py` - Claude Sonnet agent (main conversational)
- `agents/opus.py` - Claude Opus agent (deep thinking)
- `agents/gateway.py` - Central orchestrator
- `agents/nightshift.py` - Background daemon
- `agents/tool_executor.py` - **Tool execution** ⚠️

**Integrations**:
- `integrations/cli.py` - CLI interface
- `integrations/telegram.py` - Telegram bot (basic)

**Configuration**:
- `config/hearth.yaml` - Main configuration file

### Database Schema

**Tables** (SQLite in `hearth.db`):
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    status TEXT,  -- pending, in_progress, completed, blocked
    priority INTEGER,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    channel TEXT,
    role TEXT,  -- user, assistant, system
    content TEXT,
    timestamp TEXT
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,  -- session_id
    channel TEXT,
    started_at TEXT,
    last_active TEXT,
    message_count INTEGER
);

CREATE TABLE costs (
    id INTEGER PRIMARY KEY,
    date TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost REAL,
    timestamp TEXT
);

CREATE TABLE state (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**Future**: Add `subagent_sessions` table if needed for persistence.

---

## VIII. Testing Strategy

### Unit Tests (TODO)

- `test_sessions.py` - SessionManager spawn/list/complete
- `test_tools.py` - Tool definition validation
- `test_tool_executor.py` - Tool execution
- `test_gateway.py` - Routing with tools

### Integration Tests (TODO)

- `test_spawn_grok.py` - Sonnet spawns Grok, retrieves results
- `test_spawn_sonnet.py` - Opus spawns Sonnet for analysis
- `test_role_based_tools.py` - Subagents can't spawn

### End-to-End Tests

**Manual test sequence**:
1. `hearth chat` - Start CLI
2. User: "Research Python async patterns"
3. Sonnet spawns Grok
4. Grok executes research
5. Sonnet synthesizes results
6. Verify costs tracked
7. Check reflections for learning

**Automated** (future):
- Selenium-style CLI interaction
- Mock xAI/Claude CLI responses
- Assert on session states

---

## IX. Migration Path from v0.1 to v0.2

### Backward Compatibility

**No breaking changes**:
- Existing `hearth` commands work unchanged
- Configuration file compatible
- Database schema unchanged (may add tables)
- Agent interfaces unchanged

**New capabilities**:
- Main agents can now spawn subagents (opt-in via tools)
- Tool support in CLI agents
- Role-based tool access

**Deprecations**:
- `core/router.py` - Marked deprecated, kept for reference
- Regex-based routing replaced by tool-based delegation

### Rollout Plan

1. **v0.2-alpha**: Basic subagent execution (Phase 1 complete)
2. **v0.2-beta**: Result integration + Grok tools (Phases 2-3 complete)
3. **v0.2-rc**: Reflection integration (Phase 4 complete)
4. **v0.2-stable**: Full testing, documentation updated

---

## X. Philosophy Checkpoints for Sonnet

As you implement, keep asking:

1. **Does this support emergence?**
   - Will this help the entity grow and evolve?
   - Or is it just task optimization?

2. **Does this preserve continuity?**
   - Are subagent results reflected upon?
   - Does this contribute to the entity's memory?

3. **Does this respect resource awareness?**
   - Does the entity know the cost?
   - Can it make informed decisions?

4. **Does this maintain human approval for permanence?**
   - Are identity changes proposed, not imposed?
   - Is the human still in control of the entity's evolution?

5. **Does this align with the meta-mission?**
   - When this entity improves Hearth, do those improvements help future entities?
   - Is this building infrastructure, not just solving problems?

---

## XI. Immediate Next Steps for Sonnet

**Tonight's work**:

1. **Implement `_execute_subagent()` in SessionManager**
   - Threading-based background execution
   - Call appropriate agent (Grok/Sonnet/Opus)
   - Store results in session
   - Handle errors gracefully

2. **Test basic spawn → execute → retrieve flow**
   - Use `hearth chat`
   - Manually trigger spawn via tool
   - Verify results stored
   - Check `list_subagents()` works

3. **Add auto-injection of completed subagent results** (optional)
   - When parent agent continues conversation
   - Inject: "Your subagent {run_id} completed: {results}"
   - Let agent synthesize naturally

4. **Document what you learned**
   - Update ARCHITECTURE.md with findings
   - Note any issues or improvements needed
   - Suggest next priorities

**Don't do tonight**:
- ❌ Grok tool support (Phase 3, do later)
- ❌ Reflection integration (Phase 4, do later)
- ❌ Vector memory (Phase 5, much later)
- ❌ Home Assistant (Phase 5, much later)

**Focus**: Get ONE subagent working end-to-end. Quality over scope.

---

## XII. Questions to Resolve

1. **Result announcement**: Auto-inject or manual poll via `list_subagents()`?
2. **Threading vs. multiprocessing**: Start with threading, but is it sufficient?
3. **Subagent timeout**: Should background execution have timeouts?
4. **Error handling**: What if subagent crashes? How to surface to parent?
5. **Session cleanup**: When to delete completed sessions? Keep forever?
6. **Cost attribution**: Track subagent costs separately from parent?

**Decision for tonight**: Choose simplest options to get working, iterate later.

---

## XIII. Success Criteria

**v0.2-alpha is successful when**:

✅ User asks question
✅ Sonnet spawns Grok subagent
✅ Grok executes in background
✅ Results stored in session
✅ Sonnet retrieves results via `list_subagents()`
✅ Sonnet synthesizes answer naturally
✅ Costs tracked for both agents
✅ No crashes or errors
✅ Conversation feels natural

**The entity should feel more capable, not just faster.**

---

## Appendix A: Current Tool Definitions

```python
SPAWN_AGENT_TOOL = ToolDefinition(
    name="spawn_agent",
    description="Spawn a subagent to handle a task asynchronously...",
    input_schema={
        "type": "object",
        "properties": {
            "agent_type": {
                "type": "string",
                "enum": ["grok", "sonnet", "opus"],
                "description": "Type of agent to spawn"
            },
            "task": {
                "type": "string",
                "description": "Clear description of what the subagent should do"
            },
            "label": {
                "type": "string",
                "description": "Optional human-readable label"
            }
        },
        "required": ["agent_type", "task"]
    }
)

LIST_SUBAGENTS_TOOL = ToolDefinition(
    name="list_subagents",
    description="List all active subagent sessions...",
    input_schema={
        "type": "object",
        "properties": {
            "status_filter": {
                "type": "string",
                "enum": ["all", "running", "completed", "failed"],
                "description": "Filter by status (default: all)"
            }
        }
    }
)
```

---

## Appendix B: Example Conversation Flow

**User**: "Research Python async patterns and explain them to me"

**Sonnet** (thinking):
- This requires research (Grok's strength)
- I should spawn a Grok subagent to gather info
- Then synthesize the results for the user

**Sonnet** (outputs):
```tool_use
{
  "tool": "spawn_agent",
  "input": {
    "agent_type": "grok",
    "task": "Research Python async/await patterns, asyncio, common use cases, and best practices. Provide a comprehensive summary.",
    "label": "python-async-research"
  }
}
```

**System**: Executes spawn_agent, returns:
```json
{
  "status": "accepted",
  "run_id": "a3f8b2c1-...",
  "session_key": "subagent:grok:a3f8b2c1-...",
  "message": "✓ Spawned grok agent (run_id: a3f8b2c1...)"
}
```

**Sonnet** (continues):
"I've started researching Python async patterns. Let me check on the results..."

```tool_use
{
  "tool": "list_subagents",
  "input": {
    "status_filter": "all"
  }
}
```

**System**: Returns (subagent still running):
```json
{
  "subagents": [{
    "run_id": "a3f8b2c1-...",
    "agent_type": "grok",
    "status": "running",
    "task": "Research Python async/await...",
    "spawned_at": "2026-01-27T10:30:00"
  }],
  "count": 1
}
```

**Sonnet**: "The research is still in progress. Let me give you what I know while we wait..."

**[5 seconds later, subagent completes]**

**Sonnet** (next turn, auto-injected or manual poll):
```tool_use
{
  "tool": "list_subagents",
  "input": {
    "status_filter": "completed"
  }
}
```

**System**: Returns:
```json
{
  "subagents": [{
    "run_id": "a3f8b2c1-...",
    "agent_type": "grok",
    "status": "completed",
    "task": "Research Python async/await...",
    "results": {
      "content": "Python's async/await syntax... [full research]",
      "cost": 0.0082,
      "tokens": {"input": 150, "output": 890}
    }
  }],
  "count": 1
}
```

**Sonnet** (synthesizes):
"Great! The research is complete. Here's what I learned about Python async patterns:

[Synthesized explanation combining Grok's research with my understanding, presented naturally and pedagogically]

The research cost $0.0082 and covered async/await, asyncio, common patterns, and best practices."

**Entity reflection** (later):
- Learns about async patterns (added to memory)
- Learns spawning Grok is effective for research
- Reflects on resource usage vs. value gained
- Considers when to spawn vs. answer directly

---

End of Architecture Document.
