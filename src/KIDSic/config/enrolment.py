"""Reviewed enrolment snapshots; a new review gets a new file instead of rewriting history."""
from pathlib import Path
from KIDSic.dto.enrolment import EnrolmentSnapshot

ENROLMENT_SNAPSHOT = Path(__file__).parents[1] / 'db' / 'seeds' / '2026-11-05_zagreb_enrolment.json'


def load_enrolment_snapshot(path: Path = ENROLMENT_SNAPSHOT) -> EnrolmentSnapshot:
    return EnrolmentSnapshot.model_validate_json(path.read_text(encoding='utf-8'))
