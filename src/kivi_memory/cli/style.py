"""Terminal ink. Respects NO_COLOR, non-tty, and --plain."""

from __future__ import annotations

import os
import sys


def color_enabled(plain: bool = False, stream: object | None = None) -> bool:
    if plain:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    out = stream if stream is not None else sys.stdout
    return bool(getattr(out, "isatty", lambda: False)())


class Ink:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _s(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def dim(self, text: str) -> str:
        return self._s("2", text)

    def bold(self, text: str) -> str:
        return self._s("1", text)

    def heard(self, text: str) -> str:
        # slate — what the machines guessed
        return self._s("38;5;245", text)

    def kept(self, text: str) -> str:
        # copper — the user's written form
        return self._s("1;38;5;180", text)

    def label(self, text: str) -> str:
        return self._s("38;5;66", text)

    def apply(self, text: str) -> str:
        return self._s("1;38;5;108", text)

    def abstain(self, text: str) -> str:
        return self._s("38;5;67", text)

    def warn(self, text: str) -> str:
        return self._s("38;5;136", text)

    def rule(self, width: int = 56) -> str:
        return self.dim("─" * width)
