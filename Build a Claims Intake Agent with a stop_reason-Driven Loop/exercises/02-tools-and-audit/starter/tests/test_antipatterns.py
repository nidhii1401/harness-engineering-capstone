"""Anti-pattern audit.

Verifies, by static AST analysis, that the agentic loop does NOT:
- use string-membership tests against text content to drive control flow
- use an integer-literal iteration cap as its primary stopping mechanism
- omit reference to `stop_reason` as the loop-breaking signal

And that the package broadly does not branch on `claim_type` equality
outside of the tool-schema definitions and the cost-estimate module.

Each test parses the relevant file with `ast` and walks the tree. There are
no runtime imports of claims_intake here — the audit is static, so it works
even if loop.py / tools.py do not run end-to-end.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "claims_intake"
LOOP_PY = PKG / "loop.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# Anti-pattern 1 — no string-membership tests against assistant text in the loop
# ---------------------------------------------------------------------------
def test_no_string_membership_against_text_in_loop() -> None:
    """No `"some_token" in <something>` expressions in loop.py.

    Heuristic: any `ast.Compare` node using `ast.In` whose `left` operand is a
    string `ast.Constant` is flagged. The loop has no legitimate reason to test
    for the presence of a magic string inside the model's output — that would be
    natural-language-driven control flow.
    """
    offenders: list[str] = []
    for node in ast.walk(_parse(LOOP_PY)):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, ast.In) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    offenders.append(f"{LOOP_PY.name}:{node.lineno}: {ast.unparse(node)}")
    assert not offenders, (
        "string-membership tests against text drive natural-language control flow; "
        "use stop_reason instead:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Anti-pattern 2 — no integer-literal iteration cap as the primary stop mechanism
# ---------------------------------------------------------------------------
def test_no_integer_literal_iteration_cap_in_loop() -> None:
    """No `for _ in range(<int literal>)` and no `while <var> < <int literal>` in loop.py.

    Token/wall-clock/config-sourced budgets are explicitly allowed because they
    read their cap from a `Budget` instance (an attribute access or a function
    arg), not from a literal. If you need a cap, pass it in.
    """
    offenders: list[str] = []
    for node in ast.walk(_parse(LOOP_PY)):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
            call = node.iter
            if (
                isinstance(call.func, ast.Name)
                and call.func.id == "range"
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, int)
            ):
                offenders.append(f"{LOOP_PY.name}:{node.lineno}: for ... in range(<int literal>)")
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            for comparator in node.test.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, int):
                    offenders.append(f"{LOOP_PY.name}:{node.lineno}: while ... < <int literal>")
    assert not offenders, (
        "integer-literal iteration caps are not a safe stopping mechanism; "
        "use a Budget instead:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Positive evidence — stop_reason is the value that breaks the while loop
# ---------------------------------------------------------------------------
def test_stop_reason_is_loop_control() -> None:
    """loop.py references `stop_reason` AND a `while` loop exits via return/raise on it."""
    tree = _parse(LOOP_PY)

    has_stop_reason_ref = any(
        (isinstance(node, ast.Attribute) and node.attr == "stop_reason")
        or (isinstance(node, ast.Name) and node.id == "stop_reason")
        for node in ast.walk(tree)
    )
    assert has_stop_reason_ref, "loop.py must reference `stop_reason`"

    ok = False
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body_src = ast.unparse(node)
            if "stop_reason" in body_src and ("return" in body_src or "raise" in body_src):
                ok = True
                break
    assert ok, (
        "no `while` loop in loop.py exits via return/raise conditioned on stop_reason; "
        "the loop must break on stop_reason == 'end_turn' and raise on anything unexpected"
    )


# ---------------------------------------------------------------------------
# Decision-tree-in-Python — no `if claim_type == "..."` branches in the package
# ---------------------------------------------------------------------------
def test_no_claim_type_equality_branching_in_package() -> None:
    """Decision logic about claim type lives in the model, not in Python.

    tools.py is exempt (it defines the enum in input_schema).
    pricing.py is exempt (it may map claim_type to per-queue cost weights).
    """
    exempt = {"tools.py", "pricing.py", "__init__.py"}
    offenders: list[str] = []
    for path in sorted(PKG.rglob("*.py")):
        if path.name in exempt:
            continue
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.Compare):
                continue
            if not any(isinstance(op, ast.Eq) for op in node.ops):
                continue
            left = node.left
            is_claim_type = (
                isinstance(left, ast.Name) and left.id == "claim_type"
            ) or (
                isinstance(left, ast.Attribute) and left.attr == "claim_type"
            )
            has_str_const = any(
                isinstance(c, ast.Constant) and isinstance(c.value, str)
                for c in node.comparators
            )
            if is_claim_type and has_str_const:
                offenders.append(f"{path.name}:{node.lineno}: {ast.unparse(node)}")
    assert not offenders, (
        "claim_type equality branching puts decision logic in Python; "
        "move the decision into the model via tool calls:\n" + "\n".join(offenders)
    )
