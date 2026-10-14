"""Port 3 of 5 (spec §17.1). Hackathon: in-app banner + watcher log."""

from typing import Protocol


class NotifierPort(Protocol):
    def notify(self, family_id: str, kind: str, plain_text: str) -> None: ...
