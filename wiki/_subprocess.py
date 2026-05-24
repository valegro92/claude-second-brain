"""Wrapper sicuro per ``subprocess.run`` con timeout standard e logging.

Tutti i call subprocess del toolkit (pandoc, tesseract, eventuali altri)
devono passare da qui. Garantisce:
  - timeout esplicito (default 60s)
  - cattura stdout/stderr
  - errore strutturato (``SubprocessError`` custom)
  - logging della command line eseguita (per audit / debug)
"""

from __future__ import annotations

import logging
import subprocess  # noqa: S404 - call di sistema necessari
from pathlib import Path

from wiki.errors import SubprocessError

logger = logging.getLogger(__name__)


def run_with_timeout(
    cmd: list[str],
    timeout: float = 60.0,
    input_bytes: bytes | None = None,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    """Esegue ``cmd`` con timeout. Ritorna ``CompletedProcess`` o solleva ``SubprocessError``.

    Args:
        cmd: lista di token del comando (no shell). Es: ``["pandoc", "-f", "docx", ...]``.
        timeout: secondi massimi di esecuzione. Oltre, solleva ``SubprocessError``.
        input_bytes: stdin opzionale.
        cwd: working directory opzionale.
        check: se True (default), exit code != 0 solleva ``SubprocessError``.

    Returns:
        ``CompletedProcess`` con stdout/stderr come bytes.

    Raises:
        ``SubprocessError`` se il timeout scatta, il binario non esiste, o exit code != 0.
    """
    logger.debug("subprocess: %s (timeout=%.1fs, cwd=%s)", " ".join(cmd), timeout, cwd)
    try:
        result = subprocess.run(  # noqa: S603 - cmd è lista, no shell
            cmd,
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessError(
            f"Timeout dopo {timeout}s su `{cmd[0]}` (cmd: {' '.join(cmd)})"
        ) from exc
    except FileNotFoundError as exc:
        raise SubprocessError(
            f"Binario non trovato: `{cmd[0]}`. Installa il tool e verifica PATH."
        ) from exc

    if check and result.returncode != 0:
        stderr_preview = (result.stderr or b"")[:500].decode("utf-8", errors="replace")
        raise SubprocessError(
            f"`{cmd[0]}` exit code {result.returncode}. stderr: {stderr_preview}"
        )
    return result


def which_or_none(binary: str) -> str | None:
    """Wrapper compatto su ``shutil.which`` per check disponibilità tool."""
    import shutil

    return shutil.which(binary)
