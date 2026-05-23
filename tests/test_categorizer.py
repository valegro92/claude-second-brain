"""Test del categorizer (rules + claude + pipeline).

Le chiamate ad Anthropic SDK sono **mockate** con ``unittest.mock``.
Nessun test contatta API esterne.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from categorizers import claude as claude_mod
from categorizers import pipeline, rules
from categorizers._enums import Categoria
from scanners._base import FileRecord


# --------------------------------------------------------- factory helper
def _record(
    *,
    name: str = "documento.pdf",
    path: str | None = None,
    size: int = 200_000,
    age_days: int = 30,
    source: str = "nas",
    source_id: str | None = None,
    mime: str | None = "application/pdf",
    extras: dict | None = None,
    sha256: str | None = None,
) -> FileRecord:
    path = path if path is not None else f"clienti/_esempio/{name}"
    mtime = datetime.now(timezone.utc) - timedelta(days=age_days)
    return FileRecord(
        source=source,
        source_id=source_id or f"{source}://{path}",
        path=path,
        name=name,
        size=size,
        mtime=mtime,
        mime=mime,
        extras=extras or {},
        sha256=sha256,
    )


# ============================================================ rules
class TestRulesAge:
    def test_file_recente_vivo(self):
        r = _record(age_days=10)
        s = rules.score(r)
        assert s[Categoria.VIVO] >= 0.6
        cat, conf, _ = rules.classify(r)
        # Path "/clienti/_esempio/" non è archivio nè vivo speciale → vince VIVO.
        assert cat == Categoria.VIVO
        assert conf >= 0.6

    def test_file_mezza_eta(self):
        r = _record(age_days=200)
        s = rules.score(r)
        assert s[Categoria.VIVO] == pytest.approx(0.3)
        assert s[Categoria.DA_CONSULTARE] == pytest.approx(0.3)

    def test_file_vecchio(self):
        r = _record(age_days=2000, path="documenti/qualcosa.pdf")
        s = rules.score(r)
        assert s[Categoria.ARCHIVIO] >= 0.6
        cat, conf, _ = rules.classify(r)
        assert cat == Categoria.ARCHIVIO


class TestRulesNaming:
    def test_copia_di_va_a_cestino(self):
        r = _record(name="Copia di offerta.pdf", age_days=10)
        s = rules.score(r)
        assert s[Categoria.CESTINO] >= 0.5

    def test_untitled_va_a_cestino(self):
        r = _record(name="Untitled document.pdf", age_days=10)
        s = rules.score(r)
        assert s[Categoria.CESTINO] >= 0.5

    def test_lockfile_office(self):
        r = _record(name="~$documento.docx", age_days=1)
        s = rules.score(r)
        assert s[Categoria.CESTINO] >= 0.5


class TestRulesPath:
    def test_path_archivio(self):
        r = _record(path="commerciale/_archivio/2018/offerta.pdf", age_days=30)
        s = rules.score(r)
        assert s[Categoria.ARCHIVIO] >= 0.7

    def test_path_vivo(self):
        r = _record(path="clienti/attivi/rossi-srl/offerta.pdf", age_days=10)
        s = rules.score(r)
        assert s[Categoria.VIVO] >= 0.6 + 0.3 - 1e-9 or s[Categoria.VIVO] == 1.0

    def test_path_cestino(self):
        r = _record(path="Drive/Cestino/x.pdf", age_days=10)
        s = rules.score(r)
        assert s[Categoria.CESTINO] >= 0.9


class TestRulesDimensione:
    def test_zero_byte(self):
        r = _record(size=0, age_days=10)
        s = rules.score(r)
        assert s[Categoria.CESTINO] >= 0.4

    def test_file_gigante(self):
        r = _record(size=300 * 1024 * 1024, age_days=10)
        s = rules.score(r)
        assert s[Categoria.DA_CHIARIRE] >= 0.3


class TestClassifyRouting:
    def test_confidence_alta_decide_subito(self):
        r = _record(age_days=10)  # VIVO con 0.6+
        cat, conf, _ = rules.classify(r)
        assert cat != Categoria.DA_CHIARIRE
        assert conf >= 0.5

    def test_confidence_bassa_da_chiarire(self):
        # File con segnali deboli (età 500gg, naming neutro, path neutro)
        r = _record(age_days=500, name="qualcosa.pdf", path="generica/qualcosa.pdf")
        cat, conf, why = rules.classify(r)
        # 0.4 da DA_CONSULTARE → sotto 0.5: deve essere DA_CHIARIRE.
        assert cat == Categoria.DA_CHIARIRE
        assert "no-rule-decisive" in why

    def test_needs_llm_true_su_dubbi(self):
        r = _record(age_days=500, name="x.pdf", path="generica/x.pdf")
        assert rules.needs_llm(r) is True

    def test_needs_llm_false_su_archivio_chiaro(self):
        r = _record(age_days=2000, path="_archivio/old/x.pdf")
        assert rules.needs_llm(r) is False


# ============================================================ claude.py
def _mock_response(json_payload: list[dict], in_tok: int = 100, out_tok: int = 50):
    """Costruisce un mock di response Anthropic compatibile con _extract_text."""
    block = SimpleNamespace(text=json.dumps(json_payload))
    usage = SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok)
    return SimpleNamespace(content=[block], usage=usage)


class TestCategorizeBatch:
    def test_batch_vuoto(self, tmp_path: Path):
        out = claude_mod.categorize_batch([], mode="safe", state_dir=tmp_path)
        assert out == []

    def test_batch_normale_logga_costo(self, tmp_path: Path):
        records = [_record(name=f"f{i}.pdf", source_id=f"id{i}", sha256=f"sha{i:062d}") for i in range(3)]
        payload = [{"sha": r.sha256, "cat": "DA-CONSULTARE", "conf": 0.7, "why": "test"} for r in records]
        client = MagicMock()
        client.messages.create.return_value = _mock_response(payload, in_tok=400, out_tok=120)
        out = claude_mod.categorize_batch(
            records, mode="safe", state_dir=tmp_path, client=client, batch_size=20
        )
        assert len(out) == 3
        assert all(o["cat"] == Categoria.DA_CONSULTARE.value for o in out)
        # Cost log scritto.
        cost_file = tmp_path / "cost.jsonl"
        assert cost_file.exists()
        lines = cost_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["stage"] == "categorize"
        assert entry["tokens_in"] == 400
        assert entry["tokens_out"] == 120
        assert entry["cost_eur"] > 0

    def test_batch_size_spezza_chiamate(self, tmp_path: Path):
        records = [_record(name=f"f{i}.pdf", sha256=f"sha{i:062d}") for i in range(25)]
        client = MagicMock()
        # Per ogni chunk il mock risponde con N entry coerenti.
        client.messages.create.side_effect = [
            _mock_response(
                [{"sha": r.sha256, "cat": "VIVO", "conf": 0.8, "why": "x"} for r in records[:20]]
            ),
            _mock_response(
                [{"sha": r.sha256, "cat": "VIVO", "conf": 0.8, "why": "x"} for r in records[20:]]
            ),
        ]
        out = claude_mod.categorize_batch(
            records, mode="safe", state_dir=tmp_path, client=client, batch_size=20
        )
        assert client.messages.create.call_count == 2
        assert len(out) == 25

    def test_safe_non_legge_snippet(self, tmp_path: Path):
        # Predispone un main.md che NON deve essere letto in safe.
        sha = "abcdef1234567890" + "0" * 48
        ext_dir = tmp_path / "extracted" / sha[:12]
        ext_dir.mkdir(parents=True)
        (ext_dir / "main.md").write_text("contenuto-segreto", encoding="utf-8")
        records = [_record(sha256=sha)]
        client = MagicMock()
        client.messages.create.return_value = _mock_response(
            [{"sha": sha, "cat": "VIVO", "conf": 0.9, "why": "x"}]
        )
        claude_mod.categorize_batch(records, mode="safe", state_dir=tmp_path, client=client)
        # Ispeziona il prompt: niente "contenuto-segreto".
        sent_prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "contenuto-segreto" not in sent_prompt

    def test_full_legge_snippet(self, tmp_path: Path):
        sha = "abcdef1234567890" + "0" * 48
        ext_dir = tmp_path / "extracted" / sha[:12]
        ext_dir.mkdir(parents=True)
        (ext_dir / "main.md").write_text("contenuto-segreto", encoding="utf-8")
        records = [_record(sha256=sha)]
        client = MagicMock()
        client.messages.create.return_value = _mock_response(
            [{"sha": sha, "cat": "VIVO", "conf": 0.9, "why": "x"}]
        )
        claude_mod.categorize_batch(records, mode="full", state_dir=tmp_path, client=client)
        sent_prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "contenuto-segreto" in sent_prompt

    def test_risposta_non_json_fallback(self, tmp_path: Path):
        records = [_record(sha256="aa" + "0" * 62)]
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="non sono json")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )
        out = claude_mod.categorize_batch(records, mode="safe", state_dir=tmp_path, client=client)
        assert len(out) == 1
        assert out[0]["cat"] == Categoria.DA_CHIARIRE.value


# ============================================================ pipeline
def _write_jsonl(path: Path, records: list[FileRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_jsonl() + "\n")


class TestPipeline:
    def test_pipeline_solo_regole(self, tmp_path: Path):
        # 3 record, tutti con segnali forti → niente LLM.
        recs = [
            _record(name="rossi-offerta.pdf", path="clienti/attivi/rossi-srl/x.pdf", age_days=10),
            _record(name="_old.pdf", path="commerciale/_archivio/x.pdf", age_days=2000),
            _record(name="Copia di y.pdf", path="generica/x.pdf", age_days=5),
        ]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", recs)

        # Niente client necessario, niente LLM atteso.
        client = MagicMock()
        client.messages.create.side_effect = AssertionError("LLM non doveva essere chiamato")

        stats = pipeline.run_categorization(tmp_path, config={"privacy": {"modalita": "safe"}}, client=client)
        assert stats["n_total"] == 3
        # Tutti decisi da regola (n_llm = 0).
        assert stats["n_llm"] == 0
        # I JSONL aggiornati hanno la categoria.
        out = (tmp_path / "inventory" / "nas.jsonl").read_text().strip().splitlines()
        cats = [json.loads(line)["categoria"] for line in out]
        assert all(c is not None for c in cats)

    def test_pipeline_con_llm_e_audit(self, tmp_path: Path):
        # 1 record dubbio → finisce a LLM.
        rec = _record(age_days=500, name="strano.pdf", path="generica/strano.pdf", sha256="aa" + "0" * 62)
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", [rec])

        client = MagicMock()
        client.messages.create.return_value = _mock_response(
            [{"sha": rec.sha256, "cat": "DA-CONSULTARE", "conf": 0.7, "why": "test"}]
        )
        stats = pipeline.run_categorization(
            tmp_path,
            config={"privacy": {"modalita": "safe"}, "categorizer": {"batch_size": 5}},
            client=client,
        )
        assert stats["n_llm"] == 1
        assert client.messages.create.called

        # Audit ha entry sia rules che claude? Qui solo claude (rules è scattata
        # ma il record era sotto soglia, quindi va come "claude" solo).
        audit = (tmp_path / "audit" / "categorize.jsonl").read_text().strip().splitlines()
        stages = [json.loads(line)["stage"] for line in audit]
        assert "claude" in stages

        # JSONL aggiornato con la categoria scelta dall'LLM.
        out = (tmp_path / "inventory" / "nas.jsonl").read_text().strip().splitlines()
        assert json.loads(out[0])["categoria"] == Categoria.DA_CONSULTARE.value

    def test_pipeline_idempotente(self, tmp_path: Path):
        # Eseguire 2 volte non duplica/rompe nulla.
        recs = [_record(name="ovvio.pdf", path="clienti/attivi/x.pdf", age_days=10)]
        _write_jsonl(tmp_path / "inventory" / "nas.jsonl", recs)
        client = MagicMock()
        client.messages.create.side_effect = AssertionError("non doveva chiamare")
        pipeline.run_categorization(tmp_path, config={}, client=client)
        pipeline.run_categorization(tmp_path, config={}, client=client)
        out = (tmp_path / "inventory" / "nas.jsonl").read_text().strip().splitlines()
        assert len(out) == 1
