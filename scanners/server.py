"""Scanner per server interno: a v1 è un thin wrapper su :mod:`scanners.nas`.

Lo scenario A (Linux/Windows server con cartelle condivise montate) coincide
funzionalmente con un NAS — la pipeline cambia solo per l'etichetta ``source``
(utile per audit e per dedup cross-fonte).
Scenario B (gestionali con DB / web app custom) è escluso v1: workaround
documentato (Custode esporta CSV/Excel manualmente sul NAS).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from scanners._base import FileRecord
from scanners.nas import NasScanner

logger = logging.getLogger(__name__)


class ServerScanner(NasScanner):
    """Wrapper attorno a :class:`NasScanner` che cambia solo ``source_name``."""

    source_name = "server"

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        # NasScanner cerca config in sorgenti.<source_name>: garantito qui = "server"
        super().__init__(config, state_dir)
        logger.info("ServerScanner inizializzato su root=%s", self.root)

    def scan(self) -> Iterator[FileRecord]:  # pragma: no cover - delega banale
        for record in super().scan():
            # Forza source name corretto (NasScanner usa self.source_name, già "server")
            yield record
