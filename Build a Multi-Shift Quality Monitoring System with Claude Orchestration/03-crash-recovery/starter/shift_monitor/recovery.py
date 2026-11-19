"""Resume-vs-fresh decision logic for crash recovery.

The 30-minute threshold is ~1/16 of an 8-hour shift cycle: a resume inside this
window is still operating on the same shift's working set; anything older is
treated as a stale partial that should be re-started from scratch with whatever
findings the manifest already captured injected as a summary.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from .manifest import ManifestState

# TODO: Name the staleness threshold as a module-level constant
# STALE_RESUME_THRESHOLD_MINUTES = 30. The number is not arbitrary — it's about
# one-sixteenth of an 8-hour shift; resumes within this window are still on the
# same shift's working set. Document the rationale in a comment.
# ~1/16 of an 8-hour shift: a resume inside this window is still operating on
# the same shift's working set; anything older is treated as a stale partial.
STALE_RESUME_THRESHOLD_MINUTES = 30

Decision = Literal["resume", "fresh"]


def decide(state: ManifestState, now: datetime) -> Decision:
    if not state.steps:
        return "fresh"
    if state.complete:
        return "fresh"
    last_ts = state.steps[-1].ts
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=now.tzinfo)
    gap = now - last_ts
    if gap <= timedelta(minutes=STALE_RESUME_THRESHOLD_MINUTES):
        return "resume"
    return "fresh"
