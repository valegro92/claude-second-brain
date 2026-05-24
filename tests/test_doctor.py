"""Test per ``wiki/doctor.py`` (health check)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiki.doctor import (
    Check,
    _check_config,
    _check_directories,
    _check_disk_space,
    _check_env_var,
    _check_python,
    _check_tool,
    format_report,
    run_all_checks,
    summary_exit_code,
)


def test_check_python_ok() -> None:
    """Stiamo girando su Python 3.11+ in CI."""
    c = _check_python()
    assert c.stato == "ok"
    assert "Python" in c.name


def test_check_tool_existing() -> None:
    c = _check_tool("ls", required=False, descr="test")
    assert c.stato == "ok"


def test_check_tool_missing_required() -> None:
    c = _check_tool("binario-inesistente-xyz", required=True, descr="test")
    assert c.stato == "fail"


def test_check_tool_missing_optional() -> None:
    c = _check_tool("binario-inesistente-xyz", required=False, descr="test")
    assert c.stato == "warn"


def test_check_env_var_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR", "value123extralong")
    c = _check_env_var("TEST_VAR")
    assert c.stato == "ok"
    # Per valori > 8 char il dettaglio mostra preview troncato
    assert "value123" in c.dettaglio


def test_check_env_var_short_value_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valori <= 8 char vengono mascherati con *** (senza preview)."""
    monkeypatch.setenv("SHORT_VAR", "short")
    c = _check_env_var("SHORT_VAR")
    assert c.stato == "ok"
    assert "***" in c.dettaglio


def test_check_env_var_missing() -> None:
    c = _check_env_var("VAR_INESISTENTE_XYZ123")
    assert c.stato == "warn"


def test_check_env_var_missing_required() -> None:
    c = _check_env_var("VAR_INESISTENTE_XYZ123", required=True)
    assert c.stato == "fail"


def test_check_config_missing_slug() -> None:
    checks = _check_config(Path("/tmp"), slug=None)
    assert len(checks) == 1
    assert checks[0].stato == "warn"


def test_check_config_inesistente(tmp_path: Path) -> None:
    checks = _check_config(tmp_path, slug="cliente-x")
    assert any(c.stato == "fail" and "non trovato" in c.dettaglio for c in checks)


def test_check_config_valido(tmp_path: Path) -> None:
    client_dir = tmp_path / "bootstrap" / "clients" / "test"
    client_dir.mkdir(parents=True)
    (client_dir / "config.yml").write_text(
        """
cliente:
  slug: test
  nome: Test
  custode: VG
  owner: VG
sorgenti:
  nas:
    enabled: true
""",
        encoding="utf-8",
    )
    checks = _check_config(tmp_path, slug="test")
    assert any(c.stato == "ok" for c in checks)
    assert not any(c.stato == "fail" for c in checks)


def test_check_config_yaml_malformato(tmp_path: Path) -> None:
    client_dir = tmp_path / "bootstrap" / "clients" / "test"
    client_dir.mkdir(parents=True)
    (client_dir / "config.yml").write_text("{ broken yaml [", encoding="utf-8")
    checks = _check_config(tmp_path, slug="test")
    assert any(c.stato == "fail" and "YAML" in c.dettaglio for c in checks)


def test_check_directories_create(tmp_path: Path) -> None:
    checks = _check_directories(tmp_path, slug="cliente-x")
    assert (tmp_path / "_status").exists()
    assert (tmp_path / "_inbox").exists()
    assert all(c.stato in ("ok", "warn") for c in checks)


def test_check_disk_space(tmp_path: Path) -> None:
    c = _check_disk_space(tmp_path, min_gb=0.001)
    assert c.stato == "ok"


def test_check_disk_space_threshold_irrealistica(tmp_path: Path) -> None:
    c = _check_disk_space(tmp_path, min_gb=10**9)  # 1 miliardo di GB
    assert c.stato == "fail"


def test_format_report() -> None:
    checks = [
        Check("a", "ok", "tutto bene"),
        Check("b", "warn", "attenzione"),
        Check("c", "fail", "errore"),
    ]
    report = format_report(checks)
    assert "[ok]" in report
    assert "[?]" in report
    assert "[!]" in report
    assert "errore" in report


def test_summary_exit_code_all_ok() -> None:
    checks = [Check("a", "ok", "")]
    assert summary_exit_code(checks) == 0


def test_summary_exit_code_warn_non_strict() -> None:
    checks = [Check("a", "warn", "")]
    assert summary_exit_code(checks, strict=False) == 0


def test_summary_exit_code_warn_strict() -> None:
    checks = [Check("a", "warn", "")]
    assert summary_exit_code(checks, strict=True) == 1


def test_summary_exit_code_fail() -> None:
    checks = [Check("a", "fail", "")]
    assert summary_exit_code(checks) == 2


def test_run_all_checks_smoke(tmp_path: Path) -> None:
    """Smoke: run_all_checks ritorna almeno N check coerenti."""
    checks = run_all_checks(tmp_path, slug=None)
    assert len(checks) >= 8
    # Almeno un check per Python
    assert any("Python" in c.name for c in checks)
    # Almeno un check tool
    assert any(c.name.startswith("tool:") for c in checks)
