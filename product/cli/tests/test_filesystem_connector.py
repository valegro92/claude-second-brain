"""
Test del FilesystemConnector (U4): happy path + edge case su finto-drive e
tmp_path.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from custodia_cli.connectors.base import SourceDocument
from custodia_cli.connectors.filesystem import (
    _DEFAULT_EXCLUDES,
    FilesystemConnector,
)


# ----------------------------------------------------------------------
# Happy path su finto-drive
# ----------------------------------------------------------------------


def test_iter_documents_happy_path(finto_drive_root: Path) -> None:
    """Su finto-drive: PDF/DOCX/XLSX/TXT/MD vengono tutti parsati e immagini /
    .git / ~$temp.docx vengono skippati."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    docs = list(connector.iter_documents())

    by_path = {d.source_path: d for d in docs}

    # Verifica che i 5 file attesi siano presenti.
    expected_paths = {
        "Commerciale 2024/fattura-rossetto-001.pdf",
        "Commerciale 2024/offerta-bianchi-valvole.docx",
        "Commerciale 2024/listino-2024.xlsx",
        "Comunicazioni/email-torrelli-2024-03.txt",
        "README.md",
    }
    assert expected_paths.issubset(set(by_path.keys())), (
        f"missing: {expected_paths - set(by_path.keys())}"
    )

    # Tutti devono avere testo non-vuoto.
    for path in expected_paths:
        assert by_path[path].text.strip(), f"text vuoto in {path}"

    # Contenuto plausibile dei singoli file.
    assert "Rossetto Laminazioni" in by_path[
        "Commerciale 2024/fattura-rossetto-001.pdf"
    ].text
    assert "Bianchi Impianti" in by_path[
        "Commerciale 2024/offerta-bianchi-valvole.docx"
    ].text
    assert "Listino" in by_path["Commerciale 2024/listino-2024.xlsx"].text
    assert "Torrelli" in by_path["Comunicazioni/email-torrelli-2024-03.txt"].text
    assert "Custodia" in by_path["README.md"].text

    # Nessun documento per .git, immagini, ~$temp.docx.
    for d in docs:
        assert ".git" not in d.source_path
        assert "~$" not in d.source_path
        assert not d.source_path.endswith((".jpg", ".png", ".gif"))

    # stats coerenti.
    stats = connector.stats
    assert stats["processed"] == len(docs)
    assert stats["skipped_ext"] >= 3  # 3 immagini placeholder
    assert stats["skipped_excluded"] >= 2  # .git/HEAD + ~$temp.docx


def test_source_path_is_relative_to_root(finto_drive_root: Path) -> None:
    """source_path è sempre relativo, mai assoluto."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    for doc in connector.iter_documents():
        assert not Path(doc.source_path).is_absolute(), (
            f"source_path assoluto: {doc.source_path}"
        )


def test_source_id_format(finto_drive_root: Path) -> None:
    """source_id ha formato 'fs:<sha1[:16]>' ed è stabile."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    ids = [d.source_id for d in connector.iter_documents()]
    assert all(i.startswith("fs:") for i in ids)
    # Hash sha1 troncato a 16 hex.
    for i in ids:
        suffix = i.split(":", 1)[1]
        assert len(suffix) == 16
        assert all(c in "0123456789abcdef" for c in suffix)
    # Univoco fra documenti.
    assert len(set(ids)) == len(ids)


def test_metadata_fields(finto_drive_root: Path) -> None:
    """metadata contiene absolute_path, size_bytes, modified_time, extension."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    docs = list(connector.iter_documents())
    assert docs, "almeno un doc deve esistere"
    for d in docs:
        assert "absolute_path" in d.metadata
        assert "size_bytes" in d.metadata
        assert "modified_time" in d.metadata
        assert "extension" in d.metadata
        assert d.metadata["size_bytes"] >= 0
        # ISO 8601 plausibile.
        assert "T" in d.metadata["modified_time"]


# ----------------------------------------------------------------------
# Edge: cartella vuota
# ----------------------------------------------------------------------


def test_empty_directory(tmp_path: Path) -> None:
    """Iterator vuoto su directory vuota, nessun errore."""
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["processed"] == 0
    assert connector.stats["errors"] == 0


def test_nonexistent_root_raises(tmp_path: Path) -> None:
    """Root inesistente: solleva ``FileNotFoundError`` (FIX B6)."""
    target = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        FilesystemConnector(root_path=target)


def test_root_is_file_not_dir_raises(tmp_path: Path) -> None:
    """Root è un file: solleva ``NotADirectoryError`` (FIX B6)."""
    file_path = tmp_path / "fake.txt"
    file_path.write_text("hello")
    with pytest.raises(NotADirectoryError):
        FilesystemConnector(root_path=file_path)


# ----------------------------------------------------------------------
# Edge: file > max_size_mb
# ----------------------------------------------------------------------


def test_file_above_max_size_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """File oltre max_size_mb viene skippato con warning."""
    big = tmp_path / "huge.txt"
    # Scriviamo 2 MB con max_size_mb=1 (più veloce di 51 MB reali).
    big.write_bytes(b"x" * (2 * 1024 * 1024))
    connector = FilesystemConnector(root_path=tmp_path, max_file_size_mb=1)
    with caplog.at_level(logging.WARNING):
        docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_size"] == 1
    assert any("skip file" in r.message for r in caplog.records)


# ----------------------------------------------------------------------
# Edge: estensioni
# ----------------------------------------------------------------------


def test_unknown_extension_skipped_silently(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Estensione sconosciuta: skip silenzioso (debug log, non warning)."""
    (tmp_path / "data.weirdext").write_bytes(b"\x00\x01\x02 binary garbage")
    connector = FilesystemConnector(root_path=tmp_path)
    with caplog.at_level(logging.DEBUG):
        docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_unknown"] == 1
    # Nessun warning, solo debug.
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == []


def test_image_extensions_skipped(tmp_path: Path) -> None:
    """Immagini: skip via _SKIP_EXTENSIONS."""
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.png").write_bytes(b"")
    (tmp_path / "c.mp4").write_bytes(b"")
    (tmp_path / "d.zip").write_bytes(b"")
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert docs == []
    assert connector.stats["skipped_ext"] == 4


def test_plaintext_cp1252_italian_accents(tmp_path: Path) -> None:
    """File .txt salvato cp1252 (Windows italiano) → cascade decode preserva
    gli accenti (FIX B5)."""
    f = tmp_path / "italian.txt"
    f.write_bytes("caffè è bello\n".encode("cp1252"))
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert "caffè è bello" in docs[0].text


def test_plaintext_fallback_latin1_never_crashes(tmp_path: Path) -> None:
    """Bytes che falliscono sia UTF-8 che cp1252 (raro) → latin-1 fallback."""
    f = tmp_path / "weird.txt"
    # 0x81 e 0x90 sono undefined in cp1252 → fallback a latin-1.
    f.write_bytes(b"prefix \x81\x90 suffix\n")
    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert "prefix" in docs[0].text
    assert "suffix" in docs[0].text


# ----------------------------------------------------------------------
# Edge: permessi
# ----------------------------------------------------------------------


def test_permission_error_on_stat_is_logged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Se stat() solleva PermissionError, il file viene skippato senza crash."""
    (tmp_path / "ok.txt").write_text("hello")
    (tmp_path / "locked.txt").write_text("nope")

    original_stat = Path.stat

    def fake_stat(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self.name == "locked.txt":
            raise PermissionError("denied")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    connector = FilesystemConnector(root_path=tmp_path)
    with caplog.at_level(logging.WARNING):
        docs = list(connector.iter_documents())

    # ok.txt processato, locked.txt skippato come errore.
    paths = {d.source_path for d in docs}
    assert "ok.txt" in paths
    assert "locked.txt" not in paths
    assert connector.stats["errors"] >= 1


# ----------------------------------------------------------------------
# Exclude patterns custom
# ----------------------------------------------------------------------


def test_custom_exclude_pattern(tmp_path: Path) -> None:
    """Pattern custom (es. *.bak) viene applicato in aggiunta ai default."""
    (tmp_path / "keep.txt").write_text("keep me")
    (tmp_path / "old.bak").write_text("skip me")
    connector = FilesystemConnector(root_path=tmp_path, exclude_patterns=["*.bak"])
    docs = list(connector.iter_documents())
    paths = {d.source_path for d in docs}
    assert "keep.txt" in paths
    assert "old.bak" not in paths


def test_default_excludes_apply_to_subdirs(tmp_path: Path) -> None:
    """`.git` come componente intermedio esclude tutta la sottocartella."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]")
    (tmp_path / ".git" / "objects").mkdir()
    (tmp_path / ".git" / "objects" / "deadbeef").write_text("blob")
    (tmp_path / "visible.txt").write_text("hi")

    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    paths = {d.source_path for d in docs}
    assert "visible.txt" in paths
    # Nessun documento da .git/.
    assert not any(p.startswith(".git") for p in paths)


def test_default_excludes_constant_contains_basics() -> None:
    """Smoke test sul set di default exclude."""
    for needed in [".git", "__pycache__", "~$*", ".DS_Store"]:
        assert needed in _DEFAULT_EXCLUDES


# ----------------------------------------------------------------------
# Tipo restituito
# ----------------------------------------------------------------------


def test_documents_are_source_document_instances(finto_drive_root: Path) -> None:
    """Tipo restituito: SourceDocument frozen dataclass."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    for doc in connector.iter_documents():
        assert isinstance(doc, SourceDocument)


# ----------------------------------------------------------------------
# FIX B1 — Symlink loops + symlink-escape
# ----------------------------------------------------------------------


def test_symlink_loop_terminates(tmp_path: Path) -> None:
    """Symlink che punta alla parent (loop infinito potenziale) non blocca
    né causa crash: con ``follow_symlinks=False`` la directory non viene
    seguita (FIX B1)."""
    sub = tmp_path / "a"
    sub.mkdir()
    (sub / "file.txt").write_text("hello")
    try:
        (sub / "loop").symlink_to(tmp_path)
    except (OSError, NotImplementedError):
        pytest.skip("symlink non supportati su questo FS")

    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    paths = {d.source_path for d in docs}
    # file.txt va processato; non deve esserci ricorsione infinita.
    assert "a/file.txt" in paths


def test_symlink_escape_to_etc_blocked(tmp_path: Path) -> None:
    """Symlink che punta fuori dalla root (es. /etc) è skippato per security
    anche se ``follow_symlinks=True`` (FIX B1)."""
    sub = tmp_path / "a"
    sub.mkdir()
    escape = sub / "escape"
    try:
        escape.symlink_to(Path("/etc"))
    except (OSError, NotImplementedError):
        pytest.skip("symlink non supportati su questo FS")

    # Anche forzando follow_symlinks, la canonicalizzazione blocca l'escape.
    connector = FilesystemConnector(
        root_path=tmp_path, follow_symlinks=True
    )
    docs = list(connector.iter_documents())
    # Nessun file da /etc deve apparire fra i source_path.
    for d in docs:
        assert "passwd" not in d.source_path
        assert "/etc" not in d.metadata["absolute_path"]


# ----------------------------------------------------------------------
# FIX B2 — Dangerous root guardrail
# ----------------------------------------------------------------------


def test_dangerous_root_slash_refused() -> None:
    """``/`` come root solleva ValueError con messaggio chiaro (FIX B2)."""
    with pytest.raises(ValueError, match="troppo permissivo"):
        FilesystemConnector(root_path=Path("/"))


def test_dangerous_root_home_refused() -> None:
    """``$HOME`` come root è rifiutato (FIX B2)."""
    with pytest.raises(ValueError, match="troppo permissivo"):
        FilesystemConnector(root_path=Path.home())


def test_dangerous_root_bypass_with_flag(tmp_path: Path, monkeypatch) -> None:
    """``allow_dangerous_root=True`` bypassa il guardrail (FIX B2)."""
    # Simuliamo "dangerous" facendo coincidere root con HOME via monkeypatch.
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    # Senza flag: rifiuto.
    with pytest.raises(ValueError):
        FilesystemConnector(root_path=fake_home)
    # Con flag: passa.
    connector = FilesystemConnector(
        root_path=fake_home, allow_dangerous_root=True
    )
    assert connector.root_path == fake_home.resolve()


# ----------------------------------------------------------------------
# FIX B3 — Exclude su componenti intermedi profondi
# ----------------------------------------------------------------------


def test_default_excludes_match_deep_path(tmp_path: Path) -> None:
    """``.git/HEAD/sub/deep.txt`` viene escluso perché ``.git`` è uno dei
    componenti intermedi (FIX B3)."""
    deep = tmp_path / ".git" / "HEAD" / "sub"
    deep.mkdir(parents=True)
    (deep / "deep.txt").write_text("should be skipped")
    (tmp_path / "ok.txt").write_text("kept")

    connector = FilesystemConnector(root_path=tmp_path)
    paths = {d.source_path for d in connector.iter_documents()}
    assert "ok.txt" in paths
    assert not any(".git" in p for p in paths)


# ----------------------------------------------------------------------
# FIX B4 — Timestamp out-of-range non crasha
# ----------------------------------------------------------------------


def test_extreme_mtime_does_not_crash(tmp_path: Path) -> None:
    """File con mtime fuori range tollerato; modified_time può essere None
    ma il documento è prodotto (FIX B4)."""
    import os

    f = tmp_path / "weird-mtime.txt"
    f.write_text("hello")
    try:
        os.utime(f, (99999999999, 99999999999))
    except (OverflowError, OSError):
        pytest.skip("utime non accetta valori extreme su questo OS")

    connector = FilesystemConnector(root_path=tmp_path)
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    # modified_time può essere None (fallback) o stringa ISO; entrambi accettabili.
    mt = docs[0].metadata["modified_time"]
    assert mt is None or isinstance(mt, str)


# ----------------------------------------------------------------------
# FIX B8 — SourceDocument metadata immutabile
# ----------------------------------------------------------------------


def test_source_document_metadata_is_immutable(finto_drive_root: Path) -> None:
    """``doc.metadata[key] = val`` deve sollevare TypeError (FIX B8)."""
    connector = FilesystemConnector(root_path=finto_drive_root)
    doc = next(iter(connector.iter_documents()))
    with pytest.raises(TypeError):
        doc.metadata["hack"] = "nope"  # type: ignore[index]


# ----------------------------------------------------------------------
# FIX B9 — iter_documents è generator (lazy)
# ----------------------------------------------------------------------


def test_iter_documents_is_generator(finto_drive_root: Path) -> None:
    """``iter_documents()`` deve essere un generator vero (FIX B9).

    Difesa contro regressioni a ``return [...]`` che materializzerebbero
    l'intero stream in memoria.
    """
    import inspect

    connector = FilesystemConnector(root_path=finto_drive_root)
    it = connector.iter_documents()
    assert inspect.isgenerator(it)
