import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "common"))

from common.events import EventBus


def test_publish_and_history(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    event = bus.publish("task.created", {"id": "123"}, source="steward")
    assert event.id is not None
    assert event.topic == "task.created"

    history = bus.history("task.created")
    assert len(history) == 1
    assert history[0].payload["id"] == "123"


def test_glob_pattern_history(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    bus.publish("task.created", {"id": "1"})
    bus.publish("task.updated", {"id": "1"})
    bus.publish("session.created", {"id": "2"})

    task_events = bus.history("task.*")
    assert len(task_events) == 2


def test_subscribe_and_notify(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("test.*", handler)
    bus.publish("test.foo", {"msg": "hello"})

    assert len(received) == 1
    assert received[0].payload["msg"] == "hello"


def test_pending_and_mark_processed(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    event = bus.publish("job.due", {"job_id": "abc"})

    pending = bus.pending("job.due")
    assert len(pending) == 1

    bus.mark_processed(event.id)
    pending = bus.pending("job.due")
    assert len(pending) == 0
