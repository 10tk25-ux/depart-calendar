from dataclasses import dataclass, field
from typing import Optional
import hashlib


@dataclass
class Event:
    store: str
    title: str
    start: str        # ISO 8601 date: "2026-04-22"
    end: str          # ISO 8601 date (exclusive end for FullCalendar): "2026-05-07"
    url: str
    floor: str = ""
    category: str = ""

    @property
    def id(self) -> str:
        key = f"{self.store}-{self.title}-{self.start}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "store": self.store,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "floor": self.floor,
            "url": self.url,
            "category": self.category,
        }
