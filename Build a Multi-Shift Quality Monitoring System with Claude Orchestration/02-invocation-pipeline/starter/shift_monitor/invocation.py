"""Three invocation shapes.

thin     — prompt only.
rich     — hot state + new defects.
resumed  — prior partial findings + new defects since the last manifest step.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .state import HotState

InvocationShape = Literal["thin", "rich", "resumed"]


@dataclass(frozen=True)
class Invocation:
    shape: InvocationShape
    prompt: str


def thin(prompt: str) -> Invocation:
    return Invocation(shape="thin", prompt=prompt)


def rich(
    role: str, hot_state: HotState, new_defects: Sequence[Mapping[str, Any]]
) -> Invocation:
    lines = [
        f"You are the on-call {role} for Northridge Plant 3.",
        "",
        "## Current hot state",
        f"- recent_defect_hashes: {list(hot_state.recent_defect_hashes)}",
        f"- current_shift_summary: {hot_state.current_shift_summary}",
        "- active_alerts:",
    ]
    if hot_state.active_alerts:
        lines.extend(f"  - {a}" for a in hot_state.active_alerts)
    else:
        lines.append("  - (none)")
    lines.append("- threshold_statuses:")
    if hot_state.threshold_statuses:
        lines.extend(f"  - {k}: {v}" for k, v in hot_state.threshold_statuses.items())
    else:
        lines.append("  - (none)")
    lines.extend(
        [
            "",
            "## New defects since last shift",
        ]
    )
    if new_defects:
        for d in new_defects:
            lines.append(
                f"- {d['id']} | {d['ts']} | shift={d['shift']} | "
                f"component={d['component']} | severity={d['severity']} | "
                f"{d['description']}"
            )
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "Respond with: a Summary, Findings, Recommended actions, and an "
            "Updated hot state proposal as a ```json fenced block containing "
            "current_shift_summary, active_alerts, and threshold_statuses.",
        ]
    )
    return Invocation(shape="rich", prompt="\n".join(lines))


def resumed(
    session_id: str,
    summary: str,
    latest_message: str,
    prior_steps: Sequence[Mapping[str, Any]],
    new_defects: Sequence[Mapping[str, Any]],
) -> Invocation:
    lines = [
        f"Resuming session {session_id}.",
        "",
        "## Prior partial findings",
    ]
    if prior_steps:
        for step in prior_steps:
            payload_repr = repr(step.get("payload", ""))[:120]
            lines.append(f"- {step.get('name', '?')}: {payload_repr}")
    else:
        lines.append("- (none)")
    lines.extend(["", "## Prior summary", summary, "", "## New defects since last partial step"])
    if new_defects:
        for d in new_defects:
            lines.append(
                f"- {d['id']} | {d['ts']} | component={d['component']} | "
                f"severity={d['severity']} | {d['description']}"
            )
    else:
        lines.append("- (none)")
    lines.extend(["", "## Latest instruction", latest_message])
    return Invocation(shape="resumed", prompt="\n".join(lines))
