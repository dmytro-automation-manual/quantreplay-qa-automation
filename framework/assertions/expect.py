"""Field-by-field checks that report "expected vs actual" for every field, not only the first failure.

Every check produces a table like

    Execution report for NewOrderSingle
    field        expected      actual        result
    order_id     <non-empty>   2610251459..  ok
    ord_status   NEW(0)        REJECTED(8)   FAILED

The table is logged (ReportPortal), attached to the Allure step and used as the assertion message.
Layer rule: knows no framework models - reads attributes (or dict keys) by name.
"""
import logging
from collections.abc import Mapping
from typing import Any

import allure

log = logging.getLogger("check")


class Matcher:
    def matches(self, actual: Any) -> bool:
        raise NotImplementedError


class _Present(Matcher):
    def matches(self, actual: Any) -> bool:
        return actual is not None and actual != ""

    def __str__(self) -> str:
        return "<non-empty>"


class _Absent(Matcher):
    def matches(self, actual: Any) -> bool:
        return actual is None

    def __str__(self) -> str:
        return "<not sent>"


class OneOf(Matcher):
    def __init__(self, *options: Any):
        self.options = options

    def matches(self, actual: Any) -> bool:
        return actual in self.options

    def __str__(self) -> str:
        return " | ".join(str(o) for o in self.options)


PRESENT = _Present()
ABSENT = _Absent()


def _read(obj: Any, field: str) -> Any:
    return obj.get(field) if isinstance(obj, Mapping) else getattr(obj, field, None)


def _fmt(value: Any) -> str:
    text = "<none>" if value is None else str(value)
    return text if len(text) <= 60 else text[:57] + "..."


def check_fields(title: str, actual: Any, expected: Mapping[str, Any]) -> None:
    """Compare the given fields of `actual` with `expected`; fail with the full table if any differs."""
    if actual is None:
        raise AssertionError(f"{title}: nothing received")
    rows = []
    for field, exp in expected.items():
        act = _read(actual, field)
        ok = exp.matches(act) if isinstance(exp, Matcher) else act == exp
        rows.append((field, _fmt(exp), _fmt(act), "ok" if ok else "FAILED"))
    _report(title, rows)


def check_equal(title: str, actual: Any, expected: Any) -> None:
    """Single value check with the same expected/actual reporting."""
    _report(title, [("value", _fmt(expected), _fmt(actual), "ok" if actual == expected else "FAILED")])


def check_true(title: str, condition: bool, details: str = "") -> None:
    _report(title, [("condition", "true", f"{bool(condition)} {details}".strip(), "ok" if condition else "FAILED")])


def _report(title: str, rows: list[tuple[str, str, str, str]]) -> None:
    header = ("field", "expected", "actual", "result")
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(4)]
    lines = [title] + ["  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in [header] + rows]
    table = "\n".join(lines)
    failed = any(r[3] == "FAILED" for r in rows)
    log.log(logging.ERROR if failed else logging.INFO, "%s", table)
    allure.attach(table, name=("FAILED: " if failed else "") + title, attachment_type=allure.attachment_type.TEXT)
    if failed:
        raise AssertionError("\n" + table)
