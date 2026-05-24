"""
ParserPool: ``ThreadPoolExecutor`` wrapper per parallelizzare il parsing
di PDF/DOCX/XLSX su più worker thread.

NON è asincrono nel senso AsyncIO: usa thread pool stdlib. I parser
sottostanti (pypdf, python-docx, openpyxl) rilasciano il GIL durante
le syscall di lettura e durante alcune sezioni native (lxml, zlib),
quindi un thread pool è sufficiente per ottenere parallelismo reale su
workload I/O-bound + CPU-bound misti.

Default worker count:
- da env ``CUSTODIA_PARSER_WORKERS`` se settato (clamp 1..16),
- altrimenti ``min(8, max(2, os.cpu_count() - 1))``.

Esempio d'uso::

    with ParserPool(max_workers=4) as pool:
        for path, result in pool.parse_batch([p1, p2, p3]):
            if isinstance(result, Exception):
                ...
            else:
                store.save(path, result)
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator

from custodia_cli.connectors.parsers.docx import parse_docx
from custodia_cli.connectors.parsers.pdf import parse_pdf
from custodia_cli.connectors.parsers.xlsx import parse_xlsx

logger = logging.getLogger(__name__)


def _default_max_workers() -> int:
    """Calcola il numero di worker di default.

    Override via env ``CUSTODIA_PARSER_WORKERS`` (clamp 1..16). Se non
    settato o non parseable, fallback a ``min(8, max(2, cpu_count() - 1))``.
    """
    env = os.environ.get("CUSTODIA_PARSER_WORKERS")
    if env:
        try:
            return max(1, min(16, int(env)))
        except ValueError:
            logger.warning(
                "CUSTODIA_PARSER_WORKERS non valido: %r — uso default", env
            )
    cpu = os.cpu_count() or 4
    return min(8, max(2, cpu - 1))


# Registro estensione → parser callable. Restano i parser singoli del modulo
# ``parsers``; il pool si limita a invocarli su thread separati.
_PARSER_BY_EXT: dict[str, Callable[[Path], str]] = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".xlsx": parse_xlsx,
}


class ParserPool:
    """Thread pool per parsing parallelo di documenti binari supportati.

    Va usato come context manager: il ``__exit__`` invoca shutdown ordinato
    del pool (``wait=True``, ``cancel_futures=True``). Usare ``submit`` o
    ``parse_batch`` fuori dal context manager solleva ``RuntimeError``.

    ``parse()`` sincrono è disponibile anche senza context manager (utile
    per test e per il fallback "single-file").
    """

    def __init__(self, max_workers: int | None = None) -> None:
        """Crea il pool. Non avvia thread fino a ``__enter__``.

        Args:
            max_workers: override numero worker. ``None`` (default) usa il
                calcolo di ``_default_max_workers()`` (env / cpu_count).
        """
        if max_workers is not None and max_workers < 1:
            raise ValueError(f"max_workers deve essere >=1, ricevuto {max_workers}")
        self._max_workers = (
            max_workers if max_workers is not None else _default_max_workers()
        )
        self._executor: ThreadPoolExecutor | None = None

    def __enter__(self) -> ParserPool:
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix="parser"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Shutdown ordinato del pool. Idempotente."""
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    @property
    def max_workers(self) -> int:
        """Numero di worker thread configurato (non per forza attivi)."""
        return self._max_workers

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def parse(self, path: Path) -> str:
        """Parsa sincrono un singolo path. Non richiede il context manager.

        Comodo per i test o per i casi "1 file solo, non serve il pool".

        Raises:
            ValueError: nessun parser registrato per l'estensione.
        """
        parser = self._parser_for(path)
        return parser(path)

    def submit(self, path: Path) -> Future[str]:
        """Sottomette un path al pool. Richiede context manager attivo.

        Raises:
            RuntimeError: pool non aperto (uso fuori da ``with``).
            ValueError: estensione non supportata.
        """
        if self._executor is None:
            raise RuntimeError("ParserPool va usato come context manager.")
        parser = self._parser_for(path)
        return self._executor.submit(parser, path)

    def parse_batch(
        self, paths: list[Path]
    ) -> Iterator[tuple[Path, str | Exception]]:
        """Sottomette tutti i ``paths`` al pool e yield ``(path, result)``
        appena pronto.

        Ordine di yield NON è preservato (usa ``as_completed``). Per path con
        estensione non supportata, yield immediato di ``(path, ValueError(...))``.
        Per path che sollevano in parsing, yield ``(path, exception)``.

        Raises:
            RuntimeError: pool non aperto.
        """
        if self._executor is None:
            raise RuntimeError("ParserPool va usato come context manager.")

        future_to_path: dict[Future[str], Path] = {}
        for path in paths:
            ext = path.suffix.lower()
            parser = _PARSER_BY_EXT.get(ext)
            if parser is None:
                yield (path, ValueError(f"Nessun parser per estensione {ext!r}"))
                continue
            fut = self._executor.submit(parser, path)
            future_to_path[fut] = path

        for fut in as_completed(future_to_path):
            path = future_to_path[fut]
            try:
                result = fut.result()
                yield (path, result)
            except Exception as exc:  # noqa: BLE001 — vogliamo isolarli per file
                yield (path, exc)

    # ------------------------------------------------------------------
    # Helper interni
    # ------------------------------------------------------------------

    @staticmethod
    def _parser_for(path: Path) -> Callable[[Path], str]:
        ext = path.suffix.lower()
        parser = _PARSER_BY_EXT.get(ext)
        if parser is None:
            raise ValueError(
                f"Nessun parser registrato per estensione {ext!r} ({path})"
            )
        return parser


__all__ = [
    "ParserPool",
    "_default_max_workers",
]
