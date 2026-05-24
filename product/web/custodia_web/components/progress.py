"""
Helper di progress reporting per scan/build.

Streamlit non ama il multi-threading: facciamo il task sincrono dentro al
``st.status`` con callback che aggiornano un placeholder testuale. Sufficiente
per i volumi tipici (decine/centinaia di documenti).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable

import streamlit as st


@contextmanager
def live_progress(label: str):
    """Context manager: ritorna una callback (msg: str) -> None.

    Esempio::

        with live_progress("Scansione filesystem") as report:
            for i, doc in enumerate(it):
                report(f"{i} doc indicizzati")
    """
    status = st.status(label, expanded=True)
    placeholder = status.empty()

    def report(message: str) -> None:
        placeholder.markdown(f"`{message}`")

    try:
        yield report
        status.update(label=f"{label} — completato", state="complete")
    except Exception as exc:  # noqa: BLE001
        status.update(label=f"{label} — errore", state="error")
        placeholder.error(str(exc))
        raise


def make_doc_counter_cb(report: Callable[[str], None], prefix: str = "doc") -> Callable[[int, int], None]:
    """Adatta una report() generica all'API ``progress_cb(new, dup)`` di scan.*"""

    def cb(n_new: int, n_dup: int) -> None:
        report(f"{prefix}: {n_new} nuovi · {n_dup} duplicati")

    return cb


__all__ = ["live_progress", "make_doc_counter_cb"]
