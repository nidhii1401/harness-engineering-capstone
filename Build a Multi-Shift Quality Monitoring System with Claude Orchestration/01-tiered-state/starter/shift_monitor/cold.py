"""Cold tier: monthly Markdown summaries derived deterministically from the warm tier."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .warm import WarmStore


@dataclass
class ColdStore:
    store: WarmStore
    cold_dir: Path

    def write_monthly_summary(self, year: int, month: int) -> Path:
        total = self.store.count_for_month(year, month)
        top = self.store.top_components_for_month(year, month, n=3)
        lines = [
            f"# {year:04d}-{month:02d}",
            "",
            f"Total defects: {total}",
            "",
            "## Top components",
        ]
        for component, count in top:
            lines.append(f"- {component}: {count} defects")
        self.cold_dir.mkdir(parents=True, exist_ok=True)
        path = self.cold_dir / f"{year:04d}-{month:02d}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
