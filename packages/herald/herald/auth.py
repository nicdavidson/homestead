from __future__ import annotations

from herald.config import Config


def is_authorized(user_id: int, config: Config) -> bool:
    return user_id in config.allowed_user_ids
