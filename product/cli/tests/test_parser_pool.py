"""
Test del ``ParserPool`` — wrapper ``ThreadPoolExecutor`` per parsing
parallelo di PDF/DOCX/XLSX.
"""

from __future__ import annotations

import os
from pathlib import Path

import openpyxl
import pytest

from custodia_cli.connectors.parsers.pool import (
    ParserPool,
    _default_max_workers,
)


# ----------------------------------------------------------------------
# Helper: genera N XLSX rapidi su disco (XLSX è il binario più veloce
# da costruire fra quelli supportati).
# ----------------------------------------------------------------------


def _make_xlsx(path: Path, marker: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append([f"marker-{marker}", "value", "extra"])
    ws.append(["row2", 1, 2])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# ----------------------------------------------------------------------
# parse_batch + happy path
# ----------------------------------------------------------------------


def test_parse_batch_returns_all_results(tmp_path: Path) -> None:
    """Pool 4-worker su 10 XLSX: tutti i risultati arrivano, nessuna eccezione."""
    paths: list[Path] = []
    for i in range(10):
        p = tmp_path / f"file-{i:02d}.xlsx"
        _make_xlsx(p, f"id-{i}")
        paths.append(p)

    received: dict[Path, str | Exception] = {}
    with ParserPool(max_workers=4) as pool:
        for path, result in pool.parse_batch(paths):
            received[path] = result

    assert len(received) == 10
    for p in paths:
        assert p in received
        result = received[p]
        assert isinstance(result, str)
        # Marker della singola riga 1 colonna 1 deve apparire.
        idx = p.stem.split("-")[1]
        assert f"marker-id-{int(idx)}" in result


# ----------------------------------------------------------------------
# Context manager enforcement
# ----------------------------------------------------------------------


def test_submit_outside_context_raises(tmp_path: Path) -> None:
    """``submit`` fuori dal context manager → RuntimeError."""
    p = tmp_path / "f.xlsx"
    _make_xlsx(p, "x")
    pool = ParserPool(max_workers=2)
    with pytest.raises(RuntimeError, match="context manager"):
        pool.submit(p)


def test_parse_batch_outside_context_raises(tmp_path: Path) -> None:
    p = tmp_path / "f.xlsx"
    _make_xlsx(p, "x")
    pool = ParserPool(max_workers=2)
    with pytest.raises(RuntimeError, match="context manager"):
        list(pool.parse_batch([p]))


# ----------------------------------------------------------------------
# Estensione sconosciuta
# ----------------------------------------------------------------------


def test_parse_batch_yields_valueerror_for_unknown_extension(
    tmp_path: Path,
) -> None:
    """Path con estensione non supportata → yield (path, ValueError(...))."""
    weird = tmp_path / "data.weirdext"
    weird.write_bytes(b"\x00\x01\x02")
    good = tmp_path / "good.xlsx"
    _make_xlsx(good, "ok")

    with ParserPool(max_workers=2) as pool:
        results = dict(pool.parse_batch([weird, good]))

    assert isinstance(results[weird], ValueError)
    assert isinstance(results[good], str)
    assert "ok" in results[good]


# ----------------------------------------------------------------------
# Parser che solleva → cattura via Future.result()
# ----------------------------------------------------------------------


def test_parse_batch_isolates_parser_exceptions(tmp_path: Path) -> None:
    """Se un parser solleva (es. ParserError su PDF corrotto), il pool
    deve isolare l'errore e continuare con gli altri."""
    # Creiamo un PDF "corrotto" che fa esplodere pypdf.
    bad = tmp_path / "corrupt.pdf"
    bad.write_bytes(b"this is not a valid pdf at all, total garbage")
    good = tmp_path / "good.xlsx"
    _make_xlsx(good, "ok")

    with ParserPool(max_workers=2) as pool:
        results = dict(pool.parse_batch([bad, good]))

    assert bad in results
    assert good in results
    # bad → eccezione (probabile ParserError), good → stringa.
    assert isinstance(results[bad], Exception)
    assert isinstance(results[good], str)


# ----------------------------------------------------------------------
# Configurazione worker
# ----------------------------------------------------------------------


def test_max_workers_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUSTODIA_PARSER_WORKERS env var → rispettato e clampato 1..16."""
    monkeypatch.setenv("CUSTODIA_PARSER_WORKERS", "6")
    assert _default_max_workers() == 6
    monkeypatch.setenv("CUSTODIA_PARSER_WORKERS", "999")
    assert _default_max_workers() == 16
    monkeypatch.setenv("CUSTODIA_PARSER_WORKERS", "0")
    assert _default_max_workers() == 1


def test_max_workers_invalid_env_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env non parseable → fallback a default basato su cpu_count."""
    monkeypatch.setenv("CUSTODIA_PARSER_WORKERS", "abc")
    val = _default_max_workers()
    assert val >= 2
    assert val <= 8


def test_default_max_workers_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default cap a 8 anche su macchine con CPU >> 8."""
    monkeypatch.delenv("CUSTODIA_PARSER_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 32)
    assert _default_max_workers() == 8


def test_max_workers_floor_at_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """Su CPU=1 il default minimo è 2 (cpu-1 ⇒ 0, max(2, 0)=2)."""
    monkeypatch.delenv("CUSTODIA_PARSER_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    assert _default_max_workers() == 2


def test_pool_invalid_max_workers_raises() -> None:
    with pytest.raises(ValueError):
        ParserPool(max_workers=0)


# ----------------------------------------------------------------------
# Shutdown + parse sincrono
# ----------------------------------------------------------------------


def test_shutdown_via_context_manager(tmp_path: Path) -> None:
    """Dopo __exit__ il pool non accetta più submit."""
    p = tmp_path / "f.xlsx"
    _make_xlsx(p, "x")

    with ParserPool(max_workers=2) as pool:
        fut = pool.submit(p)
        assert fut.result() is not None

    # Fuori dal with: submit deve sollevare RuntimeError.
    with pytest.raises(RuntimeError):
        pool.submit(p)


def test_parse_sync_works_without_context(tmp_path: Path) -> None:
    """``parse()`` sincrono usabile anche senza context manager."""
    p = tmp_path / "f.xlsx"
    _make_xlsx(p, "sync")
    pool = ParserPool(max_workers=2)
    text = pool.parse(p)
    assert "marker-sync" in text


def test_parse_sync_unknown_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.weirdext"
    p.write_bytes(b"\x00")
    pool = ParserPool()
    with pytest.raises(ValueError):
        pool.parse(p)


def test_close_is_idempotent(tmp_path: Path) -> None:
    pool = ParserPool(max_workers=2)
    pool.close()  # noop, mai aperto
    pool.close()  # noop di nuovo
