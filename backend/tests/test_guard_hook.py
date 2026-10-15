"""The PreToolUse guard blocks edits only to files whose first line is a real REVIEWED stamp."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or not GUARD.exists(), reason="jq or guard.sh missing"
)


def _exit_code(path: Path) -> int:
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(path)}})
    return subprocess.run(  # noqa: S603
        ["bash", str(GUARD)],  # noqa: S607
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    ).returncode


@pytest.mark.parametrize(
    ("first_line", "expected"),
    [
        ("# STATUS: DRAFT — drafted by Claude, awaiting human review", 0),
        ("# STATUS: change this line to REVIEWED by <name> on <date>", 0),
        ("# STATUS: REVIEWED by Someone on 2026-01-01", 2),
    ],
)
def test_guard_reviewed_line(tmp_path: Path, first_line: str, expected: int) -> None:
    f = tmp_path / "x.yaml"
    f.write_text(first_line + "\nkey: value\n")
    assert _exit_code(f) == expected
