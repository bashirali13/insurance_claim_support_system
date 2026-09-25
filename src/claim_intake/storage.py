"""Local filesystem storage: claim records, reports, and the event log (research R9, R11)."""

import os
import re
from datetime import datetime
from pathlib import Path

from claim_intake.contracts import ClaimRecord, EventLogEntry, InternalReport
from claim_intake.pii import find_pii


class ClaimStore:
    """Sanitized claim records in data/claims/<claim_id>.json."""

    def __init__(self, root: Path):
        self.dir = Path(root) / "data" / "claims"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, claim_id: str) -> Path:
        return self.dir / f"{claim_id}.json"

    def reserve_claim_id(self, year: int) -> str:
        """Next CLM-<year>-<NNNN>, claimed by creating its file so numbers never repeat."""
        pattern = re.compile(rf"^CLM-{year}-(\d{{4}})\.json$")
        taken = [int(m.group(1)) for p in self.dir.iterdir() if (m := pattern.match(p.name))]
        number = max(taken, default=0) + 1
        while True:
            claim_id = f"CLM-{year}-{number:04d}"
            try:
                self._path(claim_id).open("x").close()
                return claim_id
            except FileExistsError:
                number += 1

    def release(self, claim_id: str) -> None:
        """Give back a reserved number whose claim was never saved."""
        self._path(claim_id).unlink(missing_ok=True)

    def save(self, record: ClaimRecord) -> None:
        """Write to a temp file, then atomically replace, so a record is never half-written."""
        path = self._path(record.claim_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def load(self, claim_id: str) -> ClaimRecord:
        return ClaimRecord.model_validate_json(self._path(claim_id).read_text(encoding="utf-8"))


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
