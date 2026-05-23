"""Smoke test per i 5 scanner + dedup_index.

Test progettati per girare in CI senza credenziali cloud:
* NAS usa ``tmp_path``
* GDrive / M365 usano i fixture JSON
* Email usa la directory ``_fixtures/email_eml``
* FileRecord round-trip serializza/deserializza
* ``apply_filters`` rispetta exclude_extensions
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from scanners._base import FileRecord
from scanners.dedup_index import build_hash_index
from scanners.email import EmailScanner
from scanners.gdrive import GDriveScanner
from scanners.m365 import M365Scanner
from scanners.nas import NasScanner
from scanners.server import ServerScanner


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "_fixtures"


# --------------------------------------------------------------------- FileRecord


def test_file_record_roundtrip() -> None:
    record = FileRecord(
        source="nas",
        source_id="/tmp/foo.txt",
        path="foo.txt",
        name="foo.txt",
        size=42,
        mtime=datetime(2024, 5, 23, 10, 0, 0),
        mime="text/plain",
        sha256="abc123",
        extras={"x": 1},
    )
    line = record.to_jsonl()
    assert "\n" not in line
    again = FileRecord.from_jsonl(line)
    assert again.source == "nas"
    assert again.size == 42
    assert again.mtime == datetime(2024, 5, 23, 10, 0, 0)
    assert again.sha256 == "abc123"
    assert again.extras == {"x": 1}


# --------------------------------------------------------------------- NAS


def _make_nas_tree(root: Path) -> dict[str, bytes]:
    """5 file diversi: txt, md, pdf finto, .dwg da escludere, file grande."""
    contents = {
        "commerciale/listino_2024.txt": b"prodotto A: 100eur\nprodotto B: 250eur\n",
        "commerciale/clienti/rossi/offerta.md": b"# Offerta Rossi\n\nDettagli...\n",
        "produzione/disegno.pdf": b"%PDF-1.4 fake pdf bytes for test",
        "produzione/cad/macchina.dwg": b"DWG_FAKE_BINARY",  # da escludere
        "produzione/manuale_grande.txt": b"x" * 1024,  # piccolo, dentro limite
    }
    for rel, data in contents.items():
        full = root / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
    return contents


def _nas_config(root: Path) -> dict:
    return {
        "sorgenti": {
            "nas": {
                "enabled": True,
                "mount": str(root),
            }
        },
        "filtri_globali": {
            "max_file_mb": 50,
            "exclude_extensions": [".dwg"],
            "exclude_paths_glob": [],
        },
    }


def test_nas_scanner_finds_files(tmp_path: Path) -> None:
    src = tmp_path / "nas_root"
    src.mkdir()
    _make_nas_tree(src)
    state = tmp_path / "state"

    scanner = NasScanner(_nas_config(src), state)
    records = list(scanner.scan())

    # 5 file totali, 1 escluso da .dwg -> 4 attesi
    assert len(records) == 4
    names = sorted(r.name for r in records)
    assert "macchina.dwg" not in names
    assert "listino_2024.txt" in names
    # SHA256 calcolato su tutti gli ammessi
    assert all(r.sha256 and len(r.sha256) == 64 for r in records)
    # JSONL scritto
    jsonl = state / "inventory" / "nas.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4


def test_nas_scanner_resume_skips_seen(tmp_path: Path) -> None:
    src = tmp_path / "nas_root"
    src.mkdir()
    _make_nas_tree(src)
    state = tmp_path / "state"

    # Prima passata
    list(NasScanner(_nas_config(src), state).scan())
    # Seconda passata: tutto gia' visto -> 0 nuovi record
    records2 = list(NasScanner(_nas_config(src), state).scan())
    assert records2 == []


def test_apply_filters_excludes_extensions(tmp_path: Path) -> None:
    src = tmp_path / "nas_root"
    src.mkdir()
    (src / "a.dwg").write_bytes(b"x")
    state = tmp_path / "state"
    scanner = NasScanner(_nas_config(src), state)

    bad_record = FileRecord(
        source="nas",
        source_id="x",
        path="bad/file.dwg",
        name="file.dwg",
        size=10,
        mtime=datetime.now(),
    )
    good_record = FileRecord(
        source="nas",
        source_id="y",
        path="ok/file.pdf",
        name="file.pdf",
        size=10,
        mtime=datetime.now(),
    )
    assert scanner.apply_filters(bad_record) is False
    assert scanner.apply_filters(good_record) is True


def test_apply_filters_excludes_oversize(tmp_path: Path) -> None:
    src = tmp_path / "nas_root"
    src.mkdir()
    state = tmp_path / "state"
    scanner = NasScanner(_nas_config(src), state)

    huge = FileRecord(
        source="nas",
        source_id="z",
        path="big/movie.txt",
        name="movie.txt",
        size=100 * 1024 * 1024,  # 100 MB
        mtime=datetime.now(),
    )
    assert scanner.apply_filters(huge) is False


# --------------------------------------------------------------------- Server (wrapper)


def test_server_scanner_uses_server_source(tmp_path: Path) -> None:
    src = tmp_path / "server_root"
    src.mkdir()
    (src / "doc.txt").write_bytes(b"hello server")
    state = tmp_path / "state"
    config = {
        "sorgenti": {"server": {"enabled": True, "mount": str(src)}},
        "filtri_globali": {"max_file_mb": 10, "exclude_extensions": []},
    }
    records = list(ServerScanner(config, state).scan())
    assert len(records) == 1
    assert records[0].source == "server"
    assert (state / "inventory" / "server.jsonl").exists()


# --------------------------------------------------------------------- GDrive mock


def test_gdrive_scanner_mock(tmp_path: Path) -> None:
    config = {
        "sorgenti": {
            "gdrive": {
                "enabled": True,
                "mock_data_path": str(FIXTURES / "gdrive_mock.json"),
            }
        },
        "filtri_globali": {
            "max_file_mb": 50,
            "exclude_extensions": [".dwg"],
        },
    }
    records = list(GDriveScanner(config, tmp_path / "state").scan())
    # 8 file nel fixture, 1 .dwg escluso -> 7 attesi
    assert len(records) == 7
    assert all(r.source == "gdrive" for r in records)
    # Almeno un record con webViewLink negli extras
    assert any(r.extras.get("webViewLink") for r in records)


# --------------------------------------------------------------------- M365 mock


def test_m365_scanner_mock(tmp_path: Path) -> None:
    config = {
        "sorgenti": {
            "m365": {
                "enabled": True,
                "mock_data_path": str(FIXTURES / "m365_mock.json"),
            }
        },
        "filtri_globali": {
            "max_file_mb": 50,  # esclude foto_collaudo.zip (60 MB)
            "exclude_extensions": [],
        },
    }
    records = list(M365Scanner(config, tmp_path / "state").scan())
    # 7 file totali, 1 escluso per size -> 6
    assert len(records) == 6
    assert all(r.source == "m365" for r in records)
    names = [r.name for r in records]
    assert "Foto_collaudo_macchina_CNC.zip" not in names


# --------------------------------------------------------------------- Email mock


def test_email_scanner_mock_directory(tmp_path: Path) -> None:
    config = {
        "sorgenti": {
            "email": {
                "enabled": True,
                "provider": "gmail",
                "mock_data_path": str(FIXTURES / "email_eml"),
                "skip_short_no_attachments": False,  # tieni tutti per test
            }
        },
        "filtri_globali": {"max_file_mb": 10, "exclude_extensions": []},
    }
    records = list(EmailScanner(config, tmp_path / "state").scan())

    msgs = [r for r in records if r.source == "email"]
    attachments = [r for r in records if r.source == "email-attachment"]
    assert len(msgs) == 10  # 10 .eml nel fixture
    # I .eml con allegati sono 002 (1), 005 (2), 009 (1) -> 4 allegati totali
    assert len(attachments) == 4
    # Verifico che gli extras del messaggio contengano subject e from
    sample = msgs[0]
    assert "subject" in sample.extras
    assert sample.extras["from"]


def test_email_scanner_short_no_attachments_filter(tmp_path: Path) -> None:
    config = {
        "sorgenti": {
            "email": {
                "enabled": True,
                "mock_data_path": str(FIXTURES / "email_eml"),
                "skip_short_no_attachments": True,
                "min_body_chars": 500,
            }
        },
        "filtri_globali": {"max_file_mb": 10, "exclude_extensions": []},
    }
    records = list(EmailScanner(config, tmp_path / "state").scan())
    names = [r.extras.get("subject", "") for r in records if r.source == "email"]
    # La notifica breve (004) deve essere scartata
    assert not any("Backup notturno" in n for n in names)


def test_email_scanner_real_mode_not_implemented(tmp_path: Path) -> None:
    config = {
        "sorgenti": {"email": {"enabled": True}},  # niente mock
        "filtri_globali": {},
    }
    scanner = EmailScanner(config, tmp_path / "state")
    with pytest.raises(NotImplementedError):
        list(scanner.scan())


# --------------------------------------------------------------------- Dedup index


def test_dedup_index_builds_by_hash(tmp_path: Path) -> None:
    # Costruisci un inventory NAS minimale, due file con SHA diversa
    state = tmp_path / "state"
    inv = state / "inventory"
    inv.mkdir(parents=True)
    rec_a = FileRecord(
        source="nas",
        source_id="/x/a.txt",
        path="a.txt",
        name="a.txt",
        size=10,
        mtime=datetime(2024, 1, 1),
        sha256="aaa",
    )
    rec_b = FileRecord(
        source="gdrive",
        source_id="id1",
        path="a.txt",
        name="a.txt",
        size=10,
        mtime=datetime(2024, 1, 2),
        sha256="aaa",  # stesso hash di rec_a -> duplicato cross-sorgente
    )
    rec_c = FileRecord(
        source="nas",
        source_id="/x/c.txt",
        path="c.txt",
        name="c.txt",
        size=20,
        mtime=datetime(2024, 1, 3),
        sha256="ccc",
    )
    (inv / "nas.jsonl").write_text(
        rec_a.to_jsonl() + "\n" + rec_c.to_jsonl() + "\n", encoding="utf-8"
    )
    (inv / "gdrive.jsonl").write_text(rec_b.to_jsonl() + "\n", encoding="utf-8")

    index = build_hash_index(state)
    assert "aaa" in index and len(index["aaa"]) == 2
    assert "ccc" in index and len(index["ccc"]) == 1
    # File scritto su disco
    by_hash_file = inv / "_by_hash.json"
    assert by_hash_file.exists()
    loaded = json.loads(by_hash_file.read_text(encoding="utf-8"))
    assert set(loaded.keys()) == {"aaa", "ccc"}
