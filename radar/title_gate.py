from __future__ import annotations

import re

_AI = re.compile(r"(?:\bai\b|artificiell)", re.IGNORECASE)


def title_is_on_topic(title: str, topic_id: str = "ai") -> bool:
    if topic_id != "ai":
        return False
    return bool(_AI.search(title or ""))
