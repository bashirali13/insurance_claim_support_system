"""Local filesystem storage: claim records, reports, and the event log (research R9, R11)."""

import os
import re
from datetime import datetime
from pathlib import Path

from claim_intake.contracts import ClaimRecord, EventLogEntry, HelpRecord, InternalReport
from claim_intake.pii import find_pii

# Committed, fictional sample claims (FR-204). Copied into data/claims/ only on request.
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


class NumberedFiles:
    """JSON records named <PREFIX>-<year>-<NNNN>.json in one folder (research R5, R9).

    A number is claimed by creating its file, so numbers never repeat, even across restarts.
    """

    def __init__(self, folder: Path, prefix: str):
        self.dir = folder
        self.prefix = prefix
        self.dir.mkdir(parents=True, exist_ok=True)

    def path(self, record_id: str) -> Path:
        return self.dir / f"{record_id}.json"

    def reserve(self, year: int) -> str:
        pattern = re.compile(rf"^{self.prefix}-{year}-(\d{{4}})\.json$")
        taken = [int(m.group(1)) for p in self.dir.iterdir() if (m := pattern.match(p.name))]
        number = max(taken, default=0) + 1
        while True:
            record_id = f"{self.prefix}-{year}-{number:04d}"
            try:
                self.path(record_id).open("x").close()
                return record_id
            except FileExistsError:
                number += 1

    def release(self, record_id: str) -> None:
        """Give back a reserved number whose record was never saved."""
        self.path(record_id).unlink(missing_ok=True)

    def write(self, record_id: str, json_text: str) -> None:
        """Write to a temp file, then atomically replace, so a record is never half-written."""
        path = self.path(record_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json_text, encoding="utf-8")
        os.replace(tmp, path)

    def read(self, record_id: str) -> str:
        return self.path(record_id).read_text(encoding="utf-8")


class ClaimStore:
    """Sanitized claim records in data/claims/<claim_id>.json."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._files = NumberedFiles(self.root / "data" / "claims", "CLM")
        self.dir = self._files.dir

    def reserve_claim_id(self, year: int) -> str:
        return self._files.reserve(year)

    def release(self, claim_id: str) -> None:
        self._files.release(claim_id)

    def save(self, record: ClaimRecord) -> None:
        self._files.write(record.claim_id, record.model_dump_json(indent=2))

    def exists(self, claim_id: str) -> bool:
        return self._files.path(claim_id).exists()

    def load(self, claim_id: str) -> ClaimRecord:
        return ClaimRecord.model_validate_json(self._files.read(claim_id))


class HelpStore:
    """Sanitized help-request records in data/help/<HELP-id>.json (specs/002 FR-215)."""

    def __init__(self, root: Path):
        self._files = NumberedFiles(Path(root) / "data" / "help", "HELP")

    def reserve_help_id(self, year: int) -> str:
        return self._files.reserve(year)

    def release(self, help_id: str) -> None:
        self._files.release(help_id)

    def save(self, record: HelpRecord) -> None:
        self._files.write(record.help_id, record.model_dump_json(indent=2))

    def load(self, help_id: str) -> HelpRecord:
        return HelpRecord.model_validate_json(self._files.read(help_id))


class ReportWriter:
    """Internal markdown reports in output/<claim_id or UNFILED>_<timestamp>.md."""

    def __init__(self, root: Path):
        self.dir = Path(root) / "output"
        self.dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: InternalReport, claim_id: str | None, at: datetime) -> Path:
        path = self.dir / f"{claim_id or 'UNFILED'}_{at:%Y%m%dT%H%M%S}.md"
        path.write_text(report.markdown, encoding="utf-8")
        return path


class EventLog:
    """Append-only JSON Lines in logs/events.log. Every field is structured, never free text."""

    def __init__(self, root: Path):
        self.path = Path(root) / "logs" / "events.log"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: EventLogEntry) -> None:
        line = entry.model_dump_json()
        if find_pii(line):  # FR-025: guard every line, even though fields are structured
            raise ValueError("event log line failed the privacy check")
        with self.path.open("a", encoding="utf-8") as log:
            log.write(line + "\n")


def load_samples(root: Path) -> list[str]:
    """Copy sample claims that aren't already present; never overwrite. Returns the IDs copied."""
    claims = ClaimStore(root).dir
    copied = []
    for sample in sorted(SAMPLES_DIR.glob("CLM-*.json")):
        target = claims / sample.name
        if not target.exists():
            target.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(sample.stem)
    return copied
