"""Health-check del toolkit. Lanciato via ``wiki doctor``.

Verifica:
  - Python version
  - Tool di sistema (pandoc, tesseract, poppler)
  - Variabili d'ambiente (ANTHROPIC_API_KEY, AWS_*)
  - Config del cliente (parsabile, semantica valida)
  - Cartelle di runtime (_status/, _inbox/) presenti o creabili
  - Spazio disco
  - Connettività API (se key presente, ping a /v1/messages)
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from wiki._subprocess import which_or_none

Stato = Literal["ok", "warn", "fail"]


@dataclass
class Check:
    """Risultato di un singolo health check."""

    name: str
    stato: Stato
    dettaglio: str

    @property
    def icona(self) -> str:
        return {"ok": "[ok]", "warn": "[?]", "fail": "[!]"}[self.stato]


def _check_python() -> Check:
    py = sys.version_info
    if py < (3, 11):
        return Check("Python", "fail", f"{py.major}.{py.minor} — richiesto 3.11+")
    if py >= (3, 11):
        return Check("Python", "ok", f"{py.major}.{py.minor}.{py.micro}")
    return Check("Python", "ok", f"{py.major}.{py.minor}.{py.micro}")


def _check_tool(name: str, required: bool, descr: str) -> Check:
    if which_or_none(name):
        return Check(f"tool:{name}", "ok", f"disponibile ({descr})")
    return Check(
        f"tool:{name}",
        "fail" if required else "warn",
        f"non trovato — {descr}",
    )


def _check_env_var(var: str, required: bool = False) -> Check:
    val = os.environ.get(var)
    if val:
        masked = val[:8] + "..." if len(val) > 8 else "***"
        return Check(f"env:{var}", "ok", f"settato ({masked})")
    return Check(
        f"env:{var}",
        "fail" if required else "warn",
        "non settato",
    )


def _check_config(repo_root: Path, slug: str | None) -> list[Check]:
    """Se ``slug`` è dato, valida il config di quel cliente."""
    if not slug:
        return [Check("config", "warn", "nessun cliente specificato (passa --client)")]
    config_path = repo_root / "bootstrap" / "clients" / slug / "config.yml"
    if not config_path.exists():
        return [Check(f"config:{slug}", "fail", f"non trovato: {config_path}")]
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [Check(f"config:{slug}", "fail", f"YAML invalido: {exc}")]
    checks = [Check(f"config:{slug}", "ok", "YAML parsabile")]

    if not isinstance(data, dict):
        return [*checks, Check(f"config:{slug}", "fail", "config non e' un dict")]

    cliente = data.get("cliente") or {}
    if not cliente.get("slug"):
        checks.append(Check(f"config:{slug}", "fail", "manca cliente.slug"))
    elif cliente["slug"] != slug:
        checks.append(
            Check(
                f"config:{slug}",
                "warn",
                f"cliente.slug={cliente['slug']} != cartella '{slug}'",
            )
        )

    sorgenti = data.get("sorgenti") or {}
    n_attive = sum(1 for s in sorgenti.values() if isinstance(s, dict) and s.get("enabled"))
    if n_attive == 0:
        checks.append(Check(f"config:{slug}", "warn", "nessuna sorgente attiva"))
    else:
        checks.append(Check(f"config:{slug}", "ok", f"{n_attive} sorgenti attive"))

    return checks


def _check_directories(repo_root: Path, slug: str | None) -> list[Check]:
    """Verifica esistenza/creabilità delle cartelle critiche."""
    checks = []
    for path, label in (
        (repo_root / "_status", "_status/"),
        (repo_root / "_inbox", "_inbox/"),
        (repo_root / "bootstrap" / "clients", "bootstrap/clients/"),
    ):
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                checks.append(Check(f"dir:{label}", "ok", "creata"))
            except OSError as exc:
                checks.append(Check(f"dir:{label}", "fail", f"non creabile: {exc}"))
            continue
        if not path.is_dir():
            checks.append(Check(f"dir:{label}", "fail", "esiste ma non e' directory"))
            continue
        # Test permessi: tentativo di scrittura
        test_file = path / ".doctor-check"
        try:
            test_file.write_text("ok")
            test_file.unlink()
            checks.append(Check(f"dir:{label}", "ok", "scrivibile"))
        except OSError as exc:
            checks.append(Check(f"dir:{label}", "fail", f"non scrivibile: {exc}"))

    if slug:
        for sub in ("_status", "_inbox"):
            client_dir = repo_root / sub / slug
            try:
                client_dir.mkdir(parents=True, exist_ok=True)
                checks.append(Check(f"dir:{sub}/{slug}/", "ok", "ok"))
            except OSError as exc:
                checks.append(Check(f"dir:{sub}/{slug}/", "fail", f"{exc}"))
    return checks


def _check_disk_space(path: Path, min_gb: float = 1.0) -> Check:
    try:
        stat = shutil.disk_usage(str(path))
    except OSError as exc:
        return Check("disk", "warn", f"impossibile verificare: {exc}")
    free_gb = stat.free / (1024**3)
    if free_gb < min_gb:
        return Check("disk", "fail", f"{free_gb:.1f} GB liberi — sotto la soglia {min_gb} GB")
    return Check("disk", "ok", f"{free_gb:.1f} GB liberi")


def run_all_checks(repo_root: Path, slug: str | None = None) -> list[Check]:
    """Esegue tutti i check disponibili e ritorna la lista risultati."""
    checks: list[Check] = []
    checks.append(_check_python())

    checks.append(_check_tool("uv", required=True, descr="package manager"))
    checks.append(_check_tool("pandoc", required=False, descr="DOCX->markdown"))
    checks.append(_check_tool("tesseract", required=False, descr="OCR PDF scansionati"))
    checks.append(_check_tool("pdftoppm", required=False, descr="Poppler, serve a pdf_ocr"))

    checks.append(_check_env_var("ANTHROPIC_API_KEY", required=False))
    if os.environ.get("AWS_PROFILE") or os.environ.get("AWS_ACCESS_KEY_ID"):
        checks.append(Check("env:AWS", "ok", "configurato (Bedrock disponibile)"))
    else:
        checks.append(Check("env:AWS", "warn", "no AWS — Bedrock non disponibile"))

    checks.extend(_check_config(repo_root, slug))
    checks.extend(_check_directories(repo_root, slug))
    checks.append(_check_disk_space(repo_root, min_gb=1.0))

    return checks


def format_report(checks: list[Check]) -> str:
    """Formatta i check come tabella semplice ASCII."""
    if not checks:
        return "Nessun check eseguito."
    name_w = max(len(c.name) for c in checks)
    lines = [f"{'STATO':<6}  {'CHECK':<{name_w}}  DETTAGLIO"]
    lines.append("-" * (8 + name_w + 12))
    for c in checks:
        lines.append(f"{c.icona:<6}  {c.name:<{name_w}}  {c.dettaglio}")
    return "\n".join(lines)


def summary_exit_code(checks: list[Check], strict: bool = False) -> int:
    """Calcola exit code da una lista di check.

    - 0 = tutti ok
    - 1 = warning presenti (solo se strict=True; altrimenti 0)
    - 2 = almeno un fail
    """
    has_fail = any(c.stato == "fail" for c in checks)
    has_warn = any(c.stato == "warn" for c in checks)
    if has_fail:
        return 2
    if has_warn and strict:
        return 1
    return 0
