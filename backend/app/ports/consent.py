"""Port 4 of 5 (spec §17.1). Hackathon: one checkbox, stored in the family graph."""

from typing import Protocol


class ConsentPort(Protocol):
    def has_shared_with_centre(self, family_id: str) -> bool: ...

    def set_shared_with_centre(self, family_id: str, value: bool) -> None: ...
