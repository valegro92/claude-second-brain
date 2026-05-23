"""Scanner per filesystem locale (NAS, server SMB/NFS, cartelle locali).

Itera in modo iterativo con ``os.scandir``, calcola SHA256, applica i filtri di
perimetro e supporta il resume tramite un file di "path già processati"
(funzionalmente un set su disco, append-only, uno per riga).

Niente chiamate di rete, niente OAuth: solo filesystem.
"""
from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterator

from scanners._base import FileRecord, Scanner

logger = logging.getLogger(__name__)

# python-magic è opzionale: se non c'è, ci si arrangia con mimetypes
try:
    import magic  # type: ignore

    _HAS_MAGIC = True
except Exception:  # pragma: no cover - opzionale
    _HAS_MAGIC = False
    magic = None  # type: ignore


# Soglia oltre la quale il file viene hashato a blocchi (1 MiB)
_HASH_CHUNK = 1024 * 1024


def _guess_mime(path: Path) -> str | None:
    """Indovina il MIME prima per estensione e poi, se disponibile, con libmagic."""
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    if _HAS_MAGIC:
        try:
            return magic.from_file(str(path), mime=True)  # type: ignore[union-attr]
        except Exception as exc:  # pragma: no cover - dipende dall'ambiente
            logger.debug("magic fallito su %s: %s", path, exc)
    return None


def _sha256_file(path: Path) -> str:
    """SHA256 a blocchi per non caricare il file intero in memoria."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class NasScanner(Scanner):
    """Scanner per filesystem locale / mount NAS.

    Config attesa::

        sorgenti:
          nas:
            enabled: true
            mount: "/Volumes/NAS-cliente/condiviso"
            perimetro:
              include: ["Commerciale", "Amministrazione"]
              exclude: ["CAD-vivi"]
        filtri_globali:
          max_file_mb: 50
          exclude_extensions: [".dwg", ".step"]
          exclude_paths_glob: ["**/.git/**", "**/node_modules/**"]
    """

    source_name = "nas"

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        super().__init__(config, state_dir)
        sorgente = config.get("sorgenti", {}).get(self.source_name, {})
        mount = sorgente.get("mount") or sorgente.get("root")
        if not mount:
            raise ValueError(
                f"Config '{self.source_name}.mount' mancante: serve la radice da scandagliare"
            )
        self.root = Path(mount).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Root NAS non esiste: {self.root}")
        self.exclude_globs: list[str] = list(
            config.get("filtri_globali", {}).get("exclude_paths_glob", [])
        )
        # Set di path già processati (resume). Append-only, una riga per file.
        self._seen: set[str] = self._load_seen()

    # ----------------------------------------------------------- resume helpers
    def _load_seen(self) -> set[str]:
        if not self.cursor_path.exists():
            return set()
        try:
            return {
                line.strip()
                for line in self.cursor_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
        except OSError as exc:  # pragma: no cover - difensivo
            logger.warning("Impossibile leggere cursor %s: %s", self.cursor_path, exc)
            return set()

    def _mark_seen(self, path: str) -> None:
        self._seen.add(path)
        with self.cursor_path.open("a", encoding="utf-8") as f:
            f.write(path + "\n")

    # --------------------------------------------------------------- filesystem
    def _iter_files(self, root: Path) -> Iterator[Path]:
        """Walk iterativo con ``os.scandir`` (più veloce di ``rglob`` su grandi alberi)."""
        stack: list[Path] = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            if entry.is_symlink():
                                continue  # niente symlink di default
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                yield Path(entry.path)
                        except OSError as exc:
                            logger.warning("Skip %s: %s", entry.path, exc)
            except (PermissionError, OSError) as exc:
                logger.warning("Skip cartella %s: %s", current, exc)

    def _matches_glob_exclude(self, path: Path) -> bool:
        rel = path.as_posix()
        return any(fnmatch(rel, pat) for pat in self.exclude_globs)

    def _build_record(self, path: Path) -> FileRecord | None:
        try:
            st = path.stat()
        except OSError as exc:
            logger.warning("Stat fallito su %s: %s", path, exc)
            return None
        try:
            rel = str(path.relative_to(self.root))
        except ValueError:
            rel = str(path)
        record = FileRecord(
            source=self.source_name,
            source_id=str(path),
            path=rel,
            name=path.name,
            size=st.st_size,
            mtime=datetime.fromtimestamp(st.st_mtime),
            mime=_guess_mime(path),
            author=None,
            last_modified_by=None,
            permissions={
                "mode": oct(st.st_mode & 0o777),
                "uid": st.st_uid,
                "gid": st.st_gid,
            },
            extras={"abs_path": str(path)},
        )
        return record

    # --------------------------------------------------------------- API
    def scan(self) -> Iterator[FileRecord]:
        """Itera tutti i file sotto la root, applica filtri, calcola SHA256 solo sui file ammessi."""
        logger.info("NAS scan start root=%s", self.root)
        for path in self._iter_files(self.root):
            key = str(path)
            if key in self._seen:
                continue
            if self._matches_glob_exclude(path):
                self._mark_seen(key)
                continue
            record = self._build_record(path)
            if record is None:
                self._mark_seen(key)
                continue
            if not self.apply_filters(record):
                self._mark_seen(key)
                continue
            # Hash solo sui file che passano i filtri (costoso su NAS)
            try:
                record.sha256 = _sha256_file(path)
            except OSError as exc:
                logger.warning("Hash fallito su %s: %s", path, exc)
                self._mark_seen(key)
                continue
            self.write_record(record)
            self._mark_seen(key)
            yield record
        logger.info("NAS scan done — %d file processati", len(self._seen))
