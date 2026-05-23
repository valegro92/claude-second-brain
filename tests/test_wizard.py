"""Test del wizard di bootstrap.

Strategia: iniettiamo ``input_fn`` e ``output_fn`` per simulare i 6 prompt
senza TTY, e verifichiamo che il config YAML generato sia parseable e abbia
i campi attesi.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bootstrap.wizard import (
    SOURCES,
    WizardAnswers,
    _validate_initials,
    _validate_privacy,
    _validate_slug,
    _validate_sources,
    render_config,
    run_wizard,
    write_config,
)


# --- validators ----------------------------------------------------------


@pytest.mark.parametrize("good", ["acme", "acme-srl", "officina-bianchi", "x123", "a1-b2-c3"])
def test_validate_slug_ok(good: str) -> None:
    assert _validate_slug(good) == good


@pytest.mark.parametrize("bad", ["Acme", "acme_srl", "-acme", "acme-", "acme srl", ""])
def test_validate_slug_ko(bad: str) -> None:
    with pytest.raises(ValueError):
        _validate_slug(bad)


@pytest.mark.parametrize("good", ["gb", "VG", "Ac"])
def test_validate_initials_normalizes_uppercase(good: str) -> None:
    assert _validate_initials(good) == good.upper()


@pytest.mark.parametrize("bad", ["g", "GBR", "g1", "", "G B"])
def test_validate_initials_ko(bad: str) -> None:
    with pytest.raises(ValueError):
        _validate_initials(bad)


def test_validate_sources_csv() -> None:
    assert _validate_sources("nas,gdrive") == ["nas", "gdrive"]


def test_validate_sources_all() -> None:
    assert _validate_sources("all") == list(SOURCES)


def test_validate_sources_dedup() -> None:
    assert _validate_sources("nas,nas,gdrive") == ["nas", "gdrive"]


def test_validate_sources_unknown_ko() -> None:
    with pytest.raises(ValueError):
        _validate_sources("dropbox")


def test_validate_privacy_ok() -> None:
    assert _validate_privacy("safe") == "safe"
    assert _validate_privacy("FULL") == "full"


def test_validate_privacy_ko() -> None:
    with pytest.raises(ValueError):
        _validate_privacy("paranoid")


# --- run_wizard interattivo con input_fn iniettato -----------------------


def _make_io(answers: list[str]) -> tuple[object, list[str]]:
    """Costruisce un input_fn che restituisce in sequenza le risposte e un output buffer."""
    idx = [0]
    out: list[str] = []

    def input_fn(_prompt: str) -> str:
        i = idx[0]
        idx[0] += 1
        if i >= len(answers):
            raise AssertionError(f"input_fn esaurito alla domanda {i+1}")
        return answers[i]

    def output_fn(msg: str) -> None:
        out.append(msg)

    return (input_fn, output_fn, out)  # type: ignore[return-value]


def test_run_wizard_happy_path() -> None:
    in_fn, out_fn, _buf = _make_io(["acme-srl", "Acme Srl", "gb", "vg", "nas,gdrive", "safe"])
    answers = run_wizard(input_fn=in_fn, output_fn=out_fn)  # type: ignore[arg-type]
    assert answers.slug == "acme-srl"
    assert answers.nome == "Acme Srl"
    assert answers.custode == "GB"
    assert answers.owner == "VG"
    assert answers.sorgenti == ["nas", "gdrive"]
    assert answers.privacy == "safe"


def test_run_wizard_retries_on_bad_slug() -> None:
    # Prima risposta cattiva, la seconda ok.
    in_fn, out_fn, _buf = _make_io(
        ["BAD SLUG", "acme", "Acme", "GB", "VG", "nas", "safe"]
    )
    answers = run_wizard(input_fn=in_fn, output_fn=out_fn)  # type: ignore[arg-type]
    assert answers.slug == "acme"


def test_run_wizard_uses_default_for_owner_when_empty() -> None:
    # Risposta vuota su owner → default "VG"
    in_fn, out_fn, _buf = _make_io(
        ["acme", "Acme", "GB", "", "nas", "safe"]
    )
    answers = run_wizard(input_fn=in_fn, output_fn=out_fn)  # type: ignore[arg-type]
    assert answers.owner == "VG"


# --- render + write -------------------------------------------------------


def test_render_config_replaces_placeholders() -> None:
    template = (
        "cliente:\n"
        "  slug: __SLUG__\n"
        "  nome: \"__NOME__\"\n"
        "  custode: __CUSTODE__\n"
        "  owner: __OWNER__\n"
        "sorgenti:\n"
        "  nas:\n"
        "    enabled: __NAS_ENABLED__\n"
        "  gdrive:\n"
        "    enabled: __GDRIVE_ENABLED__\n"
        "privacy:\n"
        "  modalita: __PRIVACY__\n"
    )
    answers = WizardAnswers(
        slug="acme", nome="Acme", custode="GB", owner="VG",
        sorgenti=["nas"], privacy="safe",
    )
    rendered = render_config(answers, template)
    assert "__SLUG__" not in rendered
    cfg = yaml.safe_load(rendered)
    assert cfg["cliente"]["slug"] == "acme"
    assert cfg["sorgenti"]["nas"]["enabled"] is True
    assert cfg["sorgenti"]["gdrive"]["enabled"] is False


def test_write_config_creates_files(tmp_path: Path) -> None:
    """Usa il template reale del repo per assicurarsi che il YAML sia valido."""
    repo_template = Path(__file__).resolve().parents[1] / "bootstrap" / "config.template.yml"
    fake_repo = tmp_path / "fakerepo"
    (fake_repo / "bootstrap").mkdir(parents=True)
    template_dst = fake_repo / "bootstrap" / "config.template.yml"
    template_dst.write_text(repo_template.read_text(encoding="utf-8"), encoding="utf-8")

    answers = WizardAnswers(
        slug="acme", nome="Acme Srl", custode="GB", owner="VG",
        sorgenti=["nas", "email"], privacy="full",
    )
    out = write_config(
        answers,
        repo_root=fake_repo,
        template_path=template_dst,
    )
    assert out.exists()
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    # Smoke check: parseable e tipi sensati
    assert cfg["cliente"]["slug"] == "acme"
    assert cfg["cliente"]["custode"] == "GB"
    assert cfg["sorgenti"]["nas"]["enabled"] is True
    assert cfg["sorgenti"]["email"]["enabled"] is True
    assert cfg["sorgenti"]["gdrive"]["enabled"] is False
    assert cfg["privacy"]["modalita"] == "full"
    # Cartelle di runtime create
    assert (fake_repo / "_status").exists()
    assert (fake_repo / "_inbox" / "acme").exists()


def test_write_config_refuses_overwrite_by_default(tmp_path: Path) -> None:
    repo_template = Path(__file__).resolve().parents[1] / "bootstrap" / "config.template.yml"
    fake_repo = tmp_path / "r"
    (fake_repo / "bootstrap").mkdir(parents=True)
    template_dst = fake_repo / "bootstrap" / "config.template.yml"
    template_dst.write_text(repo_template.read_text(encoding="utf-8"))
    answers = WizardAnswers(
        slug="acme", nome="Acme", custode="GB", owner="VG",
        sorgenti=["nas"], privacy="safe",
    )
    write_config(answers, repo_root=fake_repo, template_path=template_dst)
    with pytest.raises(FileExistsError):
        write_config(answers, repo_root=fake_repo, template_path=template_dst)
    # Con overwrite=True passa
    write_config(answers, repo_root=fake_repo, template_path=template_dst, overwrite=True)
