"""
Test degli smart filters U3 sul ``FilesystemConnector``:

- ``_SMART_EXCLUDES_EXTENDED`` (node_modules/, dist/, build/, .Trash/,
  *.photoslibrary/, lock files, …)
- Logica fine per ``Library`` macOS (skip sottocartelle Caches/Logs/
  Application Support/Containers/Mobile Documents, ma NON Library da sola).
- Estensioni aggiuntive in ``_SKIP_EXTENSIONS`` (*.dmg, *.heic, *.mov, *.iso, …).
- Magic-bytes prefilter (skip file con estensione "ingannevole").
- ``smart_excludes=False`` per opt-out.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from custodia_cli.connectors.filesystem import (
    _LIBRARY_USELESS_SUBDIRS,
    _SMART_EXCLUDES_EXTENDED,
    FilesystemConnector,
    _is_under_excluded_library_subdir,
)


# ----------------------------------------------------------------------
# Directory-level excludes (build dirs, venv, caches)
# ----------------------------------------------------------------------


def test_node_modules_subtree_excluded(tmp_path: Path) -> None:
    """``node_modules/foo/bar/baz.js`` è skippato perché ``node_modules`` è un
    componente del path."""
    nm = tmp_path / "node_modules" / "foo" / "bar"
    nm.mkdir(parents=True)
    (nm / "baz.js").write_text("module.exports = 1;")
    (tmp_path / "keep.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "keep.txt" in paths
    assert not any("node_modules" in p for p in paths)


def test_dist_build_target_excluded(tmp_path: Path) -> None:
    """Directory ``dist``/``build``/``target`` (output di build) escluse."""
    for dirname in ("dist", "build", "target"):
        d = tmp_path / dirname
        d.mkdir()
        (d / "artifact.txt").write_text("nope")
    (tmp_path / "src.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "src.txt" in paths
    for excluded in ("dist", "build", "target"):
        assert not any(p.startswith(f"{excluded}/") for p in paths), (
            f"{excluded} non escluso: {paths}"
        )


def test_python_venv_and_caches_excluded(tmp_path: Path) -> None:
    """``.venv``, ``venv``, ``site-packages``, ``.pytest_cache`` esclusi."""
    for d in (".venv", "venv", "site-packages", ".pytest_cache", ".mypy_cache"):
        sub = tmp_path / d
        sub.mkdir()
        (sub / "x.py").write_text("pass")
    (tmp_path / "main.py").write_bytes(b"")  # estensione non plaintext-known

    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    paths = {d.source_path for d in docs}
    for ex in (".venv", "venv", "site-packages", ".pytest_cache", ".mypy_cache"):
        assert not any(p.startswith(f"{ex}/") for p in paths)


def test_photoslibrary_excluded(tmp_path: Path) -> None:
    """``*.photoslibrary`` (cartella opaca macOS) skippata via fnmatch."""
    lib = tmp_path / "Foto.photoslibrary"
    lib.mkdir()
    (lib / "Photos.sqlite").write_bytes(b"sqlite stuff")
    (lib / "resources").mkdir()
    (lib / "resources" / "thumb.jpg").write_bytes(b"")
    (tmp_path / "ok.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "ok.txt" in paths
    assert not any("photoslibrary" in p for p in paths)


def test_lock_files_excluded(tmp_path: Path) -> None:
    """Lock files (uv.lock, package-lock.json, *.lock) skippati come filename."""
    (tmp_path / "uv.lock").write_text("locked")
    (tmp_path / "package-lock.json").write_text("{}")
    (tmp_path / "poetry.lock").write_text("locked")
    (tmp_path / "custom.lock").write_text("locked")
    (tmp_path / "keep.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "keep.txt" in paths
    assert "uv.lock" not in paths
    assert "package-lock.json" not in paths
    assert "poetry.lock" not in paths
    assert "custom.lock" not in paths


# ----------------------------------------------------------------------
# Logica fine Library macOS
# ----------------------------------------------------------------------


def test_library_caches_subdir_excluded(tmp_path: Path) -> None:
    """``Library/Caches/...`` è escluso (rumore di sistema)."""
    sub = tmp_path / "Library" / "Caches" / "com.apple.foo"
    sub.mkdir(parents=True)
    (sub / "cache.dat").write_bytes(b"")
    sub2 = tmp_path / "Library" / "Mail" / "V10"
    sub2.mkdir(parents=True)
    (sub2 / "msg.eml").write_text("From: a@b\n\nbody")
    (tmp_path / "ok.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    # ok.txt e msg.eml dovrebbero passare; Caches no.
    assert "ok.txt" in paths
    # Library/Mail/V10/msg.eml: estensione .eml non è plaintext-known →
    # skippata come unknown-ext, NON come excluded.
    assert not any("Library/Caches" in p for p in paths)


def test_library_mail_subdir_not_excluded_by_library_logic(tmp_path: Path) -> None:
    """``Library/Mail`` NON è escluso dalla logica fine: il consulente
    potrebbe voler scannare proprio le mailbox."""
    mail_dir = tmp_path / "Library" / "Mail"
    mail_dir.mkdir(parents=True)
    (mail_dir / "letter.txt").write_text("important content")
    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "Library/Mail/letter.txt" in paths


def test_library_app_support_excluded(tmp_path: Path) -> None:
    """``Library/Application Support`` (con spazio) escluso."""
    sub = tmp_path / "Library" / "Application Support" / "Foo"
    sub.mkdir(parents=True)
    (sub / "junk.txt").write_text("nope")
    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert not any("Application Support" in p for p in paths)


def test_library_alone_not_excluded(tmp_path: Path) -> None:
    """``Library`` come dir name da sola NON è esclusa: solo le subdir note."""
    lib = tmp_path / "Library"
    lib.mkdir()
    (lib / "free.txt").write_text("ok")
    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "Library/free.txt" in paths


def test_is_under_excluded_library_subdir_helper() -> None:
    """Helper diretto: tutte le subdir note matcheranno True."""
    for sub in _LIBRARY_USELESS_SUBDIRS:
        p = Path("/Users/foo/Library") / sub / "inside" / "f.txt"
        assert _is_under_excluded_library_subdir(p), sub
    # Library/Mail e Library/Calendars: False.
    assert not _is_under_excluded_library_subdir(
        Path("/Users/foo/Library/Mail/letter.eml")
    )
    assert not _is_under_excluded_library_subdir(
        Path("/Users/foo/no-library-here/x.txt")
    )


# ----------------------------------------------------------------------
# Estensioni mediali / archivi / installer nel set extended
# ----------------------------------------------------------------------


def test_new_skip_extensions_treated_as_skipped_ext(tmp_path: Path) -> None:
    """``*.dmg``, ``*.heic``, ``*.mov``, ``*.iso``, ``*.app`` finiscono in
    ``skipped_ext`` (non ``skipped_excluded``), perché passano via
    ``_SKIP_EXTENSIONS``."""
    (tmp_path / "installer.dmg").write_bytes(b"")
    (tmp_path / "foto.heic").write_bytes(b"")
    (tmp_path / "video.mov").write_bytes(b"")
    (tmp_path / "image.iso").write_bytes(b"")
    (tmp_path / "MyApp.app").write_bytes(b"")  # qui è un *file* .app
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_ext"] == 5


def test_zip_file_excluded_regardless_of_content(tmp_path: Path) -> None:
    """``*.zip`` con contenuto plaintext arbitrario rimane skip (estensione)."""
    (tmp_path / "fake-zip.zip").write_text("not actually a zip, just text")
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_ext"] >= 1


# ----------------------------------------------------------------------
# Magic-bytes prefilter
# ----------------------------------------------------------------------


def test_magic_bytes_mismatch_skip_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """File ``.pdf`` con contenuto plain text → skip via magic mismatch."""
    import logging

    fake = tmp_path / "fake.pdf"
    fake.write_text("not a pdf, just text")
    connector = FilesystemConnector(root_path=tmp_path)
    with caplog.at_level(logging.WARNING):
        docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_magic_mismatch"] == 1
    assert any(
        "magic bytes non coerenti" in r.message for r in caplog.records
    )


# ----------------------------------------------------------------------
# smart_excludes=False opt-out + custom patterns aggiuntivi
# ----------------------------------------------------------------------


def test_smart_excludes_false_disables_extended(tmp_path: Path) -> None:
    """Con ``smart_excludes=False`` le directory tipo ``node_modules`` non
    vengono escluse (utile per debug, sconsigliato per uso normale)."""
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "data.txt").write_text("hello")
    connector = FilesystemConnector(
        root_path=tmp_path, smart_excludes=False
    )
    paths = {d.source_path for d in connector.iter_documents()}
    assert "node_modules/data.txt" in paths


def test_custom_exclude_pattern_adds_on_top(tmp_path: Path) -> None:
    """Pattern custom passati al costruttore si SOMMANO ai default + smart."""
    (tmp_path / "keep.txt").write_text("kept")
    (tmp_path / "skip.custom").write_text("nope")
    # node_modules deve restare escluso anche con la lista custom.
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "x.txt").write_text("nm")
    connector = FilesystemConnector(
        root_path=tmp_path, exclude_patterns=["*.custom"]
    )
    paths = {d.source_path for d in connector.iter_documents()}
    assert "keep.txt" in paths
    assert "skip.custom" not in paths
    assert not any("node_modules" in p for p in paths)


def test_smart_excludes_constant_contains_basics() -> None:
    """Smoke test sul set di smart-excludes esteso."""
    for needed in ("node_modules", "dist", "build", "target", "*.photoslibrary"):
        assert needed in _SMART_EXCLUDES_EXTENDED
