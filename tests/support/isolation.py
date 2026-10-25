"""Test isolation helpers: every change a test makes is undone in its teardown, in reverse order."""
import logging
import time
from collections.abc import Callable

import allure

log = logging.getLogger("isolation")


class UndoStack:
    """Register an undo action right before changing something; teardown runs them last-in-first-out."""

    def __init__(self):
        self._actions: list[tuple[str, Callable[[], None]]] = []

    def push(self, description: str, action: Callable[[], None]) -> None:
        self._actions.append((description, action))

    def run_all(self) -> None:
        errors = []
        while self._actions:
            description, action = self._actions.pop()
            with allure.step(f"Teardown: {description}"):
                try:
                    action()
                except Exception as exc:        # keep undoing the rest, report everything at the end
                    log.error("undo failed: %s: %s", description, exc)
                    errors.append(f"{description}: {exc}")
        if errors:
            raise AssertionError("Teardown could not restore the state:\n" + "\n".join(errors))


def wait_until(condition: Callable[[], bool], timeout: float, what: str, interval: float = 0.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if condition():
                return
        except Exception:                   # not up yet
            pass
        time.sleep(interval)
    raise TimeoutError(f"{what} not ready within {timeout}s")
