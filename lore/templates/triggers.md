# Proactive Triggers

These are events that can wake you up without human input.

## Scheduled (via Almanac)
- **Morning briefing** — Daily. Check news, tasks, calendar. Send summary via Herald.
- **Daily reflection** — Evening. Review the day's conversations, write journal entry, consolidate learnings.
- **Weekly synthesis** — Weekly. Deep reflection: review journal, propose lore updates, identify patterns.

## Reactive (future)
- **File watcher** — Monitor specific directories for changes.
- **Webhook listener** — Receive events from external services (GitHub, etc.).
- **Error spike** — If Watchtower detects error rate above threshold, alert user.
- **Task blocker resolved** — When a human-blocked task gets unblocked, resume work.

## How Triggers Work

1. Almanac fires a scheduled job
2. The job writes to the outbox (or event bus) with the trigger type
3. Herald delivers the message or wakes the appropriate agent
4. The agent reads relevant context (scratchpad, skills, lore) and acts

You don't need to wait to be asked. If a trigger fires, act on it.
