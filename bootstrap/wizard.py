"""Wizard CLI interattivo per `wiki init`.

Sei domande validate, output: `bootstrap/clients/<slug>/config.yml` riempito a
partire da `bootstrap/config.template.yml`. Nessuna chiamata di rete, niente
side-effect oltre la creazione delle cartelle `_status/`, `_inbox/<slug>/` e
la scrittura del config.

Tutto il modulo è progettato per essere testato sostituendo `input_fn` e
`output_fn`: i test passano funzioni mock, in modo da non aver bisogno di un
vero TTY.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# --- costanti -------------------------------------------------------------

#: Sorgenti supportate dallo Step 2 (Vedi `_brief/04-step-2-tech-plan.md` §2).
SOURCES: tuple[str, ...] = ("gdrive", "m365", "email", "nas", "server")

#: Modalità privacy ammesse (Vedi `_brief/04-step-2-tech-plan.md` §8).
PRIVACY_MODES: tuple[str, ...] = ("safe", "full")

#: Regex slug kebab-case: minuscole, cifre, trattino singolo, no trattini agli estremi.
_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: Iniziali: esattamente 2 caratteri alfabetici, normalizzate maiuscole.
_INITIALS_RE = re.compile(r"^[A-Za-z]{2}$")


# --- modello dati ---------------------------------------------------------


@dataclass
class WizardAnswers:
    """Risposte raccolte dal wizard, validate."""

    slug: str
    nome: str
    custode: str
    owner: str
    sorgenti: list[str] = field(default_factory=list)
    privacy: str = "safe"

    def is_source_enabled(self, source: str) -> bool:
        return source in self.sorgenti


# --- helper di prompt validati -------------------------------------------


InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


def _default_output(msg: str) -> None:
    # Stampa sul terminale: il wizard è interattivo, qui è ok usare print.
    print(msg)


def _prompt_validated(
    label: str,
    *,
    validator: Callable[[str], str],
    default: str | None,
    input_fn: InputFn,
    output_fn: OutputFn,
    error_hint: str,
) -> str:
    """Loop input -> validate finché non passa.

    ``validator`` restituisce il valore *normalizzato* (es. uppercase per
    iniziali) o solleva ``ValueError`` con messaggio leggibile.
    """
    hint = f" [{default}]" if default else ""
    while True:
        raw = input_fn(f"{label}{hint}: ").strip()
        if not raw and default is not None:
            raw = default
        try:
            return validator(raw)
        except ValueError as exc:
            output_fn(f"  ! {exc}. {error_hint}")


def _validate_slug(value: str) -> str:
    if not _SLUG_RE.match(value):
        raise ValueError(f"slug non valido: '{value}'")
    return value


def _validate_nome(value: str) -> str:
    if not value:
        raise ValueError("nome cliente obbligatorio")
    # Quote-escape banale per finire dentro un YAML "..."
    return value.replace('"', "'")


def _validate_initials(value: str) -> str:
    if not _INITIALS_RE.match(value):
        raise ValueError(f"iniziali non valide: '{value}'")
    return value.upper()


def _validate_sources(value: str) -> list[str]:
    """Lista separata da virgole; supporta `all` come scorciatoia."""
    if not value:
        raise ValueError("almeno una sorgente è obbligatoria")
    if value.lower() == "all":
        return list(SOURCES)
    tokens = [t.strip().lower() for t in value.split(",") if t.strip()]
    unknown = [t for t in tokens if t not in SOURCES]
    if unknown:
        raise ValueError(f"sorgenti sconosciute: {unknown}; ammesse: {SOURCES}")
    # Deduplica preservando ordine
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _validate_privacy(value: str) -> str:
    v = value.lower().strip()
    if v not in PRIVACY_MODES:
        raise ValueError(f"privacy '{value}' non valida; ammesse: {PRIVACY_MODES}")
    return v


# --- wizard principale ---------------------------------------------------


def run_wizard(
    *,
    input_fn: InputFn | None = None,
    output_fn: OutputFn | None = None,
) -> WizardAnswers:
    """Esegue i 6 prompt e ritorna le risposte validate.

    I parametri ``input_fn`` / ``output_fn`` sono iniettabili per i test.
    Default: ``input`` (stdin) e ``print`` (stdout).
    """
    in_fn = input_fn or input
    out_fn = output_fn or _default_output

    out_fn("Wizard di setup cliente — wiki-toolkit Step 2")
    out_fn("Rispondi a 6 domande. Le risposte sono validate.")
    out_fn("")

    slug = _prompt_validated(
        "1) Slug cliente (kebab-case, es. 'officina-bianchi')",
        validator=_validate_slug,
        default=None,
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="usa solo a-z, 0-9 e trattini.",
    )
    nome = _prompt_validated(
        "2) Nome cliente (ragione sociale)",
        validator=_validate_nome,
        default=None,
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="non può essere vuoto.",
    )
    custode = _prompt_validated(
        "3) Iniziali Custode (2 lettere)",
        validator=_validate_initials,
        default=None,
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="esattamente 2 caratteri alfabetici (es. 'GB').",
    )
    owner = _prompt_validated(
        "4) Iniziali Owner (2 lettere)",
        validator=_validate_initials,
        default="VG",
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="esattamente 2 caratteri alfabetici (es. 'VG').",
    )
    sources_raw = _prompt_validated(
        f"5) Sorgenti attive (lista CSV o 'all'; ammesse: {','.join(SOURCES)})",
        validator=lambda v: ",".join(_validate_sources(v)),
        default="nas",
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="separa con virgole, niente spazi.",
    )
    privacy = _prompt_validated(
        f"6) Modalità privacy ({'/'.join(PRIVACY_MODES)})",
        validator=_validate_privacy,
        default="safe",
        input_fn=in_fn,
        output_fn=out_fn,
        error_hint="safe = solo metadati; full = + snippet 500 char.",
    )

    answers = WizardAnswers(
        slug=slug,
        nome=nome,
        custode=custode,
        owner=owner,
        sorgenti=list(_validate_sources(sources_raw)),
        privacy=privacy,
    )
    out_fn("")
    out_fn(
        f"Riepilogo: cliente='{answers.slug}', sorgenti={answers.sorgenti}, privacy={answers.privacy}"
    )
    return answers


# --- rendering del config -------------------------------------------------


def render_config(answers: WizardAnswers, template_text: str) -> str:
    """Sostituisce i placeholder `__X__` nel template con le risposte.

    Mappa:
        __SLUG__            → answers.slug
        __NOME__            → answers.nome
        __CUSTODE__         → answers.custode
        __OWNER__           → answers.owner
        __<SRC>_ENABLED__   → "true"/"false" per ogni SRC in SOURCES
        __PRIVACY__         → answers.privacy
    """
    out = template_text
    out = out.replace("__SLUG__", answers.slug)
    out = out.replace("__NOME__", answers.nome)
    out = out.replace("__CUSTODE__", answers.custode)
    out = out.replace("__OWNER__", answers.owner)
    for src in SOURCES:
        token = f"__{src.upper()}_ENABLED__"
        value = "true" if answers.is_source_enabled(src) else "false"
        out = out.replace(token, value)
    out = out.replace("__PRIVACY__", answers.privacy)
    return out


def write_config(
    answers: WizardAnswers,
    *,
    repo_root: Path,
    template_path: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Scrive il config cliente e crea le cartelle di runtime collegate.

    Ritorna la path del config scritto. Crea:
      - ``bootstrap/clients/<slug>/config.yml``
      - ``_status/`` (vuota, è output di runtime)
      - ``_inbox/<slug>/`` (drop zone watcher per quel cliente)
    """
    tmpl_path = template_path or (repo_root / "bootstrap" / "config.template.yml")
    if not tmpl_path.exists():
        raise FileNotFoundError(f"Template non trovato: {tmpl_path}")
    template_text = tmpl_path.read_text(encoding="utf-8")

    clients_dir = repo_root / "bootstrap" / "clients" / answers.slug
    clients_dir.mkdir(parents=True, exist_ok=True)
    config_path = clients_dir / "config.yml"
    if config_path.exists() and not overwrite:
        raise FileExistsError(
            f"Config esistente: {config_path}. Usa overwrite=True per sovrascrivere."
        )

    rendered = render_config(answers, template_text)
    config_path.write_text(rendered, encoding="utf-8")

    # Cartelle di runtime
    (repo_root / "_status").mkdir(parents=True, exist_ok=True)
    (repo_root / "_inbox" / answers.slug).mkdir(parents=True, exist_ok=True)

    logger.info("Config scritto: %s", config_path)
    return config_path


# --- helper esposti ------------------------------------------------------


def known_sources() -> Iterable[str]:
    """Lista delle sorgenti supportate (usato dal CLI)."""
    return SOURCES
