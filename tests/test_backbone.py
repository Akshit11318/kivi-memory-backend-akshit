"""Smoke test: package imports and CLI help."""

from kivi_memory.cli.main import main
from kivi_memory.config import DECIDE_MODES, DEFAULT_DECIDE, DEFAULT_PROFILE, PROFILES


def test_profiles_locked() -> None:
    assert DEFAULT_PROFILE == "auto"
    assert PROFILES == ("off", "exact", "phonetic", "auto")
    assert DEFAULT_DECIDE == "llm"
    assert DECIDE_MODES == ("llm", "ungated")


def test_cli_help() -> None:
    assert main([]) == 0


def test_unknown_profile() -> None:
    assert main(["--profile", "foo", "run"]) == 2


def test_unknown_decide() -> None:
    assert main(["--decide", "foo", "run"]) == 2


def test_llm_decide_without_credentials_is_an_error(monkeypatch, capsys) -> None:
    monkeypatch.delenv("KIVI_LLM_API_KEY", raising=False)
    monkeypatch.delenv("KIVI_LLM_MODEL", raising=False)
    assert main(["--decide", "llm", "run", "--formatted", "hello"]) == 2
    err = capsys.readouterr().err
    assert "KIVI_LLM_API_KEY" in err
    assert "KIVI_LLM_MODEL" in err
    assert "--decide ungated" in err


def test_banner_plain(capsys) -> None:
    assert main(["--plain"]) == 0
    out = capsys.readouterr().out
    assert "kivi" in out
    assert "Rustom" in out
    assert "Meenakshi" in out
    assert "observe" in out
    assert "aaditya" not in out.lower()
    assert "kiwi" not in out.lower()
