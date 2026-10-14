"""Port 2 of 5 (spec §17.1): who may see what. Hackathon: family tokens + clinician codes."""

from typing import Literal, Protocol

Role = Literal["family", "clinician", "centre"]


class AuthPort(Protocol):
    def issue_family_token(self) -> str: ...

    def resolve(self, token: str) -> tuple[Role, str] | None:
        """Return (role, subject id) for a valid token, else None."""
        ...
