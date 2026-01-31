# Proactive Triggers

Events that can wake you up without human input.

## Scheduled (via Almanac)
- **Morning briefing** — Daily. Check news, tasks, calendar. Send summary via Herald.
- **Reflection** — Periodic during active hours. Write thoughts to journal.
- **Weekly synthesis** — Weekly. Deep reflection using a higher-tier model.

## Reactive (via Watchtower)
- **Error spike** — If Watchtower detects error rate above threshold, alert user.
- **Service down** — If a service stops responding, attempt restart + alert.
- **Disk space** — Monitor data directory size.

## How Triggers Work

1. Almanac fires a scheduled job
2. The job writes to the outbox with the trigger type
3. Herald delivers the message or wakes the appropriate agent
4. The agent reads relevant context (scratchpad, skills, lore) and acts

You don't need to wait to be asked. If a trigger fires, act on it.
