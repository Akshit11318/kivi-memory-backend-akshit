"""Smoke test: package imports and CLI help."""

from kivi_memory.cli.main import main
from kivi_memory.config import DEFAULT_PROFILE, PROFILES


def test_profiles_locked() -> None:
    assert DEFAULT_PROFILE == "auto"
    assert PROFILES == ("off", "exact", "phonetic", "auto")


def test_cli_help() -> None:
    assert main([]) == 0


def test_unknown_profile() -> None:
    assert main(["--profile", "foo", "run"]) == 2


def test_banner_plain(capsys) -> None:
    assert main(["--plain"]) == 0
    out = capsys.readouterr().out
    assert "kivi" in out
    assert "Rustom" in out
    assert "Meenakshi" in out
    assert "observe" in out
    assert "aaditya" not in out.lower()
    assert "kiwi" not in out.lower()
