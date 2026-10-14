"""Port 5 of 5 (spec §17.1). Hackathon: GA4GH Phenopacket v2 JSON download."""

from typing import Any, Protocol


class ExportPort(Protocol):
    def export_phenopacket(self, family_id: str) -> dict[str, Any]: ...
