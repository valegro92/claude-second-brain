"""
Gestione workspace multi-progetto della webapp.

Ogni progetto = un vault cliente. La lista vive in ``~/.custodia/projects.json``
(stesso parent di altri config Custodia futuri).

Schema persistito::

    {
      "version": 1,
      "projects": [
        {"id": "...", "name": "...", "vault_path": "...",
         "created_at": "...", "last_active_at": "...", "color": "#..."}
      ],
      "active_project_id": "..." | null
    }
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".custodia"
PROJECTS_FILE = CONFIG_DIR / "projects.json"
SCHEMA_VERSION = 1

_DEFAULT_COLOR = "#0F766E"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    """Slug semplice per id progetto: 'Rossetto Laminazioni' → 'rossetto-laminazioni'."""
    base = _SLUG_RE.sub("-", value.lower().strip()).strip("-")
    return base or f"prj-{uuid.uuid4().hex[:8]}"


@dataclass
class Project:
    """Metadati di un progetto/vault cliente."""

    id: str
    name: str
    vault_path: str
    created_at: str = field(default_factory=_now_iso)
    last_active_at: str = field(default_factory=_now_iso)
    color: str = _DEFAULT_COLOR

    def vault_pathlib(self) -> Path:
        return Path(self.vault_path).expanduser().resolve()


def _load_raw() -> dict:
    """Legge il file JSON. Ritorna struttura vuota se manca o malformato."""
    if not PROJECTS_FILE.exists():
        return {"version": SCHEMA_VERSION, "projects": [], "active_project_id": None}
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # File corrotto: ricominciamo da capo invece di crashare l'UI.
        return {"version": SCHEMA_VERSION, "projects": [], "active_project_id": None}
    data.setdefault("version", SCHEMA_VERSION)
    data.setdefault("projects", [])
    data.setdefault("active_project_id", None)
    return data


def _save_raw(data: dict) -> None:
    """Scrive il file JSON con atomic rename per evitare corruzione."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PROJECTS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PROJECTS_FILE)


def list_projects() -> list[Project]:
    """Ritorna la lista dei progetti registrati."""
    data = _load_raw()
    return [Project(**p) for p in data["projects"]]


def get_active_project() -> Project | None:
    """Progetto attualmente attivo, o None se nessuno selezionato/registrato."""
    data = _load_raw()
    active_id = data.get("active_project_id")
    if not active_id:
        return None
    for p in data["projects"]:
        if p["id"] == active_id:
            return Project(**p)
    return None


def set_active_project(project_id: str) -> None:
    """Imposta il progetto attivo e aggiorna `last_active_at`."""
    data = _load_raw()
    found = False
    for p in data["projects"]:
        if p["id"] == project_id:
            p["last_active_at"] = _now_iso()
            found = True
            break
    if not found:
        raise ValueError(f"Progetto sconosciuto: {project_id}")
    data["active_project_id"] = project_id
    _save_raw(data)


def create_project(
    name: str,
    vault_path: str | Path,
    color: str = _DEFAULT_COLOR,
) -> Project:
    """Crea (o ritorna se id-collide) un progetto e lo marca attivo.

    Non esegue ``custodia init`` automaticamente: il chiamante decide se/quando.
    """
    if not name.strip():
        raise ValueError("name non può essere vuoto")
    data = _load_raw()
    base_slug = _slugify(name)
    existing_ids = {p["id"] for p in data["projects"]}
    slug = base_slug
    n = 1
    while slug in existing_ids:
        n += 1
        slug = f"{base_slug}-{n}"

    proj = Project(
        id=slug,
        name=name.strip(),
        vault_path=str(Path(vault_path).expanduser()),
        color=color or _DEFAULT_COLOR,
    )
    data["projects"].append(asdict(proj))
    data["active_project_id"] = proj.id
    _save_raw(data)
    return proj


def delete_project(project_id: str) -> None:
    """Rimuove un progetto dalla lista (NON tocca il vault sul disco)."""
    data = _load_raw()
    before = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
    if len(data["projects"]) == before:
        raise ValueError(f"Progetto sconosciuto: {project_id}")
    if data.get("active_project_id") == project_id:
        data["active_project_id"] = data["projects"][0]["id"] if data["projects"] else None
    _save_raw(data)


__all__ = [
    "Project",
    "list_projects",
    "get_active_project",
    "set_active_project",
    "create_project",
    "delete_project",
    "PROJECTS_FILE",
    "CONFIG_DIR",
]
