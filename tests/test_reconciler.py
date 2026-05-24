"""Test dei reconciler (dedup_hash, dedup_soft, schede, persone)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from categorizers._enums import Categoria
from reconcilers import dedup_hash, dedup_soft, persone, schede
from scanners._base import FileRecord


def _rec(
    *,
    name: str,
    source: str = "nas",
    source_id: str | None = None,
    sha256: str | None = None,
    path: str | None = None,
    age_days: int = 30,
    size: int = 100_000,
    mime: str | None = "application/pdf",
    extras: dict | None = None,
    categoria: str | None = None,
) -> FileRecord:
    path = path if path is not None else f"clienti/_esempio/{name}"
    return FileRecord(
        source=source,
        source_id=source_id or f"{source}://{name}",
        path=path,
        name=name,
        size=size,
        mtime=datetime.now(UTC) - timedelta(days=age_days),
        mime=mime,
        sha256=sha256,
        extras=extras or {},
        categoria=categoria,
    )


def _write_jsonl(path: Path, recs: list[FileRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(r.to_jsonl() + "\n")


# ===================================================== dedup_hash
class TestDedupHash:
    def test_3_record_stesso_sha(self, tmp_path: Path):
        sha = "deadbeef" * 8  # 64 chars
        recs = [
            _rec(name="a.pdf", source="nas", source_id="nas://a", sha256=sha, age_days=20),
            _rec(name="a.pdf", source="gdrive", source_id="g1", sha256=sha, age_days=5),
            _rec(name="a.pdf", source="email-attachment", source_id="e1", sha256=sha, age_days=30),
        ]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", [recs[0]])
        _write_jsonl(tmp_path / "inventory" / "gdrive.jsonl", [recs[1]])
        _write_jsonl(tmp_path / "inventory" / "email.jsonl", [recs[2]])
        by_hash = {
            sha: [
                {"source": r.source, "source_id": r.source_id, "mtime": r.mtime.isoformat()}
                for r in recs
            ]
        }
        stats = dedup_hash.apply_dedup_groups(by_hash, tmp_path)
        assert stats["n_groups"] == 1
        assert stats["n_canonical"] == 1
        assert stats["n_duplicates"] == 2

        # Il canonical deve essere gdrive (priorità più alta).
        gdrive_out = json.loads((tmp_path / "inventory" / "gdrive.jsonl").read_text().strip())
        assert gdrive_out["dedup"]["role"] == "canonical"
        assert gdrive_out["dedup"]["canonical"] is None

        nas_out = json.loads((tmp_path / "inventory" / "nas.jsonl").read_text().strip())
        assert nas_out["dedup"]["role"] == "duplicate-of"
        assert nas_out["dedup"]["canonical"] == "gdrive:g1"

    def test_gruppo_di_uno_ignorato(self, tmp_path: Path):
        sha = "aa" * 32
        recs = [_rec(name="solo.pdf", sha256=sha)]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", recs)
        by_hash = {
            sha: [
                {
                    "source": recs[0].source,
                    "source_id": recs[0].source_id,
                    "mtime": recs[0].mtime.isoformat(),
                }
            ]
        }
        stats = dedup_hash.apply_dedup_groups(by_hash, tmp_path)
        assert stats["n_groups"] == 0
        # Nessuna modifica al record (dedup resta None).
        out = json.loads((tmp_path / "inventory" / "nas.jsonl").read_text().strip())
        assert out["dedup"] is None

    def test_run_dedup_hash_senza_by_hash(self, tmp_path: Path):
        # Manca _by_hash.json → ritorna stats zero, niente eccezione.
        (tmp_path / "inventory").mkdir(parents=True)
        stats = dedup_hash.run_dedup_hash(tmp_path)
        assert stats["n_groups"] == 0


# ===================================================== dedup_soft
class TestDedupSoft:
    def test_quattro_versioni_clustered(self, tmp_path: Path):
        recs = [
            _rec(name="offerta_v1.pdf", path="clienti/rossi/offerte/offerta_v1.pdf"),
            _rec(name="offerta_v2.pdf", path="clienti/rossi/offerte/offerta_v2.pdf"),
            _rec(name="offerta_v3.pdf", path="clienti/rossi/offerte/offerta_v3.pdf"),
            _rec(
                name="offerta_FINAL.pdf", path="clienti/rossi/offerte/offerta_FINAL.pdf", age_days=1
            ),
        ]
        clusters = dedup_soft.cluster_soft_dups(recs)
        assert len(clusters) == 1
        assert len(clusters[0]) == 4

    def test_normalize_base_v_numero(self):
        base, matched = dedup_soft.normalize_base("offerta_v12.pdf")
        assert base == "offerta"
        assert matched is True

    def test_normalize_base_copia_di(self):
        base, matched = dedup_soft.normalize_base("Copia di documento.pdf")
        assert base == "documento"
        assert matched is True

    def test_normalize_base_parentesi(self):
        base, matched = dedup_soft.normalize_base("foglio (2).xlsx")
        assert base == "foglio"
        assert matched is True

    def test_normalize_no_match(self):
        base, matched = dedup_soft.normalize_base("documento-stabile.pdf")
        assert matched is False

    def test_run_genera_bozza_decisione(self, tmp_path: Path):
        recs = [
            _rec(name=f"offerta_v{i}.pdf", path=f"clienti/rossi/offerte/offerta_v{i}.pdf")
            for i in (1, 2, 3)
        ] + [
            _rec(
                name="offerta_FINAL.pdf",
                path="clienti/rossi/offerte/offerta_FINAL.pdf",
                age_days=1,
            )
        ]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", recs)
        stats = dedup_soft.run_dedup_soft(tmp_path, batch_id="b001")
        assert stats["n_clusters"] == 1
        assert stats["n_files"] == 4
        draft = tmp_path / "drafts" / "b001" / "dedup-soft-001.md"
        assert draft.exists()
        text = draft.read_text(encoding="utf-8")
        assert "CANONICAL" in text
        assert "offerta_FINAL.pdf" in text  # mtime più recente → canonical
        # Frontmatter
        assert "stato: bozza-generata-da-scandagliamento" in text


# ===================================================== schede
class TestSchede:
    def test_slugify_accenti_e_spazi(self):
        assert schede.slugify("Officina Bianchi Srl") == "officina-bianchi-srl"
        assert schede.slugify("Sant'Angelo & Figli") == "sant-angelo-figli"

    def test_group_records_da_path_clienti(self):
        recs = [
            _rec(
                name="offerta.pdf",
                path=f"Drive/clienti/rossi-srl/offerte/offerta_v{i}.pdf",
                source_id=f"id{i}",
                categoria=Categoria.VIVO.value,
            )
            for i in range(1, 4)
        ]
        groups = schede.group_records(recs)
        assert len(groups) == 1
        g = groups[0]
        assert g.slug == "rossi-srl"
        assert g.tipo == "cliente"
        assert len(g.records) == 3
        assert any(s.startswith("folder:") for s in g.signals)

    def test_group_records_da_email_dominio(self):
        # 2 mail dello stesso dominio cliente.
        recs = [
            _rec(
                name=f"mail-{i}.eml",
                path=f"emails/mail-{i}.eml",
                source="email",
                source_id=f"msg-{i}",
                extras={"from": "Mario Rossi <m.rossi@rossi-srl.it>"},
                categoria=Categoria.DA_CONSULTARE.value,
            )
            for i in range(2)
        ]
        groups = schede.group_records(recs)
        assert len(groups) == 1
        assert groups[0].slug == "rossi-srl"

    def test_group_ignora_dominio_generico(self):
        recs = [
            _rec(
                name="mail.eml",
                source="email",
                extras={"from": "x <x@gmail.com>"},
                categoria=Categoria.VIVO.value,
            )
            for _ in range(3)
        ]
        groups = schede.group_records(recs)
        assert groups == []

    def test_group_ignora_archivio_cestino(self):
        recs = [
            _rec(
                name="vecchio.pdf",
                path="clienti/rossi-srl/vecchio.pdf",
                source_id=f"id-{i}",
                categoria=Categoria.ARCHIVIO.value,
            )
            for i in range(5)
        ]
        groups = schede.group_records(recs)
        assert groups == []

    def test_run_schede_end_to_end(self, tmp_path: Path):
        """Test E2E: 8 record raggruppabili → 1 scheda con 5 file."""
        recs = []
        # 5 PDF nella cartella clienti/rossi-srl/
        for i in range(5):
            recs.append(
                _rec(
                    name=f"doc-{i}.pdf",
                    path=f"Drive/clienti/rossi-srl/doc-{i}.pdf",
                    source_id=f"nas-{i}",
                    sha256=f"{i:064x}",
                    categoria=Categoria.VIVO.value,
                )
            )
        # 3 email dello stesso dominio.
        for i in range(3):
            recs.append(
                _rec(
                    name=f"mail-{i}.eml",
                    path=f"Drive/clienti/rossi-srl/mail-{i}.eml",
                    source="email",
                    source_id=f"msg-{i}",
                    extras={"from": "Mario Rossi <m.rossi@rossi-srl.it>"},
                    categoria=Categoria.VIVO.value,
                )
            )
        _write_jsonl(tmp_path / "inventory" / "mixed.jsonl", recs)

        # Mock LLM per la sezione narrativa.
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(
                    text="## Storia\n\n- 2024: cliente attivo\n\n## Decisioni estratte\n\n- ok"
                )
            ],
            usage=SimpleNamespace(input_tokens=300, output_tokens=80),
        )

        stats = schede.run_schede(tmp_path, batch_id="b001", client=client)
        assert stats["n_groups"] == 1
        assert "rossi-srl" in stats["slugs"]

        # 5 file Regola 01-PMI esistono.
        out_dir = tmp_path / "drafts" / "b001" / "scheda-cliente-rossi-srl"
        assert (out_dir / "rossi-srl.md").exists()
        assert (out_dir / "CLAUDE.md").exists()
        assert (out_dir / "MEMORY.md").exists()
        assert (out_dir / "tasks.md").exists()
        assert (out_dir / "persone.md").exists()
        # Frontmatter corretto.
        moc = (out_dir / "rossi-srl.md").read_text(encoding="utf-8")
        assert "tipo: scheda-cliente" in moc
        assert "stato: bozza-generata-da-scandagliamento" in moc
        assert "TODO" in moc
        # Persone include i mittenti email.
        persone_md = (out_dir / "persone.md").read_text(encoding="utf-8")
        assert "m.rossi@rossi-srl.it" in persone_md
        # Costo loggato.
        cost = (tmp_path / "cost.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(cost) == 1
        assert json.loads(cost[0])["stage"] == "scheda-narrativa"

    def test_run_schede_senza_llm(self, tmp_path: Path):
        recs = [
            _rec(
                name=f"doc-{i}.pdf",
                path=f"Drive/clienti/rossi-srl/doc-{i}.pdf",
                source_id=f"nas-{i}",
                categoria=Categoria.VIVO.value,
            )
            for i in range(3)
        ]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", recs)
        stats = schede.run_schede(tmp_path, batch_id="b002", call_llm=False)
        assert stats["n_groups"] == 1
        moc = (
            tmp_path / "drafts" / "b002" / "scheda-cliente-rossi-srl" / "rossi-srl.md"
        ).read_text()
        assert "TODO" in moc


# ===================================================== persone
class TestPersone:
    def test_extract_persone_da_email(self, tmp_path: Path):
        recs = [
            _rec(
                name="mail-1.eml",
                source="email",
                extras={
                    "from": "Mario Rossi <m.rossi@rossi-srl.it>",
                    "to": "Anna Ferrari <a.ferrari@bianchi.it>",
                    "cc": "Carla Pini <c.pini@rossi-srl.it>",
                },
                age_days=10,
            ),
            _rec(
                name="mail-2.eml",
                source="email",
                extras={
                    "from": "Mario Rossi <m.rossi@rossi-srl.it>",
                    "to": "Anna Ferrari <a.ferrari@bianchi.it>",
                },
                age_days=5,
            ),
        ]
        out = persone.extract_persone(recs, tmp_path)
        assert "m.rossi@rossi-srl.it" in out
        assert "a.ferrari@bianchi.it" in out
        assert "c.pini@rossi-srl.it" in out
        assert out["m.rossi@rossi-srl.it"].n_messaggi == 2
        # Best name fa il merge.
        assert "Mario Rossi" in out["m.rossi@rossi-srl.it"].best_name()

    def test_run_persone_safe_aggregato(self, tmp_path: Path):
        recs = [
            _rec(
                name=f"m-{i}.eml",
                source="email",
                extras={"from": f"X{i} <x{i}@rossi-srl.it>"},
            )
            for i in range(3)
        ]
        _write_jsonl(tmp_path / "inventory" / "email.jsonl", recs)
        config = {
            "privacy": {"modalita": "safe"},
            "cliente": {"dominio_interno": "bianchi.it"},
        }
        stats = persone.run_persone(tmp_path, batch_id="b001", config=config)
        assert stats["n_persone"] == 3
        draft = tmp_path / "drafts" / "b001" / "persone-rossi-srl.md"
        assert draft.exists()
        text = draft.read_text(encoding="utf-8")
        # In safe la tabella con email NON deve esserci.
        assert "x0@rossi-srl.it" not in text
        assert "Persone uniche" in text

    def test_run_persone_full_mostra_email(self, tmp_path: Path):
        recs = [
            _rec(
                name=f"m-{i}.eml",
                source="email",
                extras={"from": f"X{i} <x{i}@rossi-srl.it>"},
            )
            for i in range(2)
        ]
        _write_jsonl(tmp_path / "inventory" / "email.jsonl", recs)
        config = {
            "privacy": {"modalita": "full"},
            "cliente": {"dominio_interno": "bianchi.it"},
        }
        persone.run_persone(tmp_path, batch_id="b002", config=config)
        text = (tmp_path / "drafts" / "b002" / "persone-rossi-srl.md").read_text()
        assert "x0@rossi-srl.it" in text
        assert "x1@rossi-srl.it" in text

    def test_cluster_interni_separati(self, tmp_path: Path):
        recs = [
            _rec(
                name="m-int.eml",
                source="email",
                extras={"from": "AF <a.ferrari@bianchi.it>"},
            ),
            _rec(
                name="m-ext.eml",
                source="email",
                extras={"from": "MR <m.rossi@rossi-srl.it>"},
            ),
        ]
        _write_jsonl(tmp_path / "inventory" / "email.jsonl", recs)
        stats = persone.run_persone(
            tmp_path,
            batch_id="b003",
            config={
                "privacy": {"modalita": "full"},
                "cliente": {"dominio_interno": "bianchi.it"},
            },
        )
        assert stats["n_interni"] == 1
        assert stats["n_cluster_esterni"] == 1
        assert (tmp_path / "drafts" / "b003" / "persone-interni.md").exists()
        assert (tmp_path / "drafts" / "b003" / "persone-rossi-srl.md").exists()
