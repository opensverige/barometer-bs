from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from radar.models import Claim, Source


class Adapter(ABC):
    name: str

    @abstractmethod
    def fetch(self, window: list[str]) -> Any:
        """Raw payload for the given riksmöten / window keys."""

    @abstractmethod
    def normalize(self, raw: Any) -> list[Source]:
        """Map raw records to Source. Never drop errors silently."""

    @abstractmethod
    def extract(self, sources: list[Source], topic_id: str) -> list[Claim]:
        """Conservative claims only — no inferred policy stance from prose."""
