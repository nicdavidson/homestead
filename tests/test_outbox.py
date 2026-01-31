from common.outbox import post_message, get_pending, mark_sent, mark_failed


def test_post_and_get_pending(db_path):
    """Post message, get pending, verify contents."""
    post_message(db_path, chat_id=123, agent_name="herald", message="Hello!")

    pending = get_pending(db_path)
    assert len(pending) == 1
    msg = pending[0]
    assert msg.chat_id == 123
    assert msg.agent_name == "herald"
    assert msg.message == "Hello!"
    assert msg.parse_mode == "HTML"
    assert msg.created_at > 0


def test_mark_sent(db_path):
    """Post, mark sent, verify not in pending."""
    post_message(db_path, chat_id=1, agent_name="nightshift", message="done")

    pending = get_pending(db_path)
    assert len(pending) == 1

    mark_sent(db_path, pending[0].id)

    pending = get_pending(db_path)
    assert len(pending) == 0


def test_mark_failed(db_path):
    """Post, mark failed, verify not in pending."""
    post_message(db_path, chat_id=2, agent_name="steward", message="oops")

    pending = get_pending(db_path)
    assert len(pending) == 1

    mark_failed(db_path, pending[0].id)

    pending = get_pending(db_path)
    assert len(pending) == 0


def test_multiple_pending(db_path):
    """Post several, get pending with limit."""
    for i in range(5):
        post_message(db_path, chat_id=10, agent_name="herald", message=f"msg {i}")

    # Get all
    pending = get_pending(db_path)
    assert len(pending) == 5

    # Get with limit
    pending = get_pending(db_path, limit=3)
    assert len(pending) == 3

    # Messages are ordered by created_at, so first posted come first
    assert pending[0].message == "msg 0"
    assert pending[1].message == "msg 1"
    assert pending[2].message == "msg 2"
