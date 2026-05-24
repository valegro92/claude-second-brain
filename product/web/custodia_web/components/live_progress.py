"""
Componente UI per il progress live dei job scan/build.

Renderizza lo snapshot prodotto da :func:`StateStore.get_run_progress` in un
layout coerente: progress bar, file corrente, throughput, ETA, breakdown
skippati e errori. Pensato per essere chiamato dentro il loop polling delle
pagine Scan e Build.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def _format_seconds(seconds: float | None) -> str:
    """Formatta una durata in modo conciso, es. ``3 min 12 sec``.

    Restituisce ``"—"`` per ``None`` o valori negativi.
    """
    if seconds is None or seconds < 0:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} sec"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {secs:02d} sec"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def _format_throughput(tps: float | None) -> str:
    if tps is None or tps <= 0:
        return "—"
    if tps < 10:
        return f"{tps:.1f}/sec"
    return f"{int(tps)}/sec"


def _format_skipped(skipped: dict[str, int]) -> str:
    """Renderizza il breakdown skipped. Mostra solo voci > 0."""
    if not skipped:
        return ""
    # ordinamento per valore desc, poi alfabetico
    pretty = {
        "skipped_unchanged": "unchanged",
        "skipped_excluded": "excluded",
        "skipped_size": "size",
        "skipped_ext": "ext",
        "skipped_unknown": "tipo ignoto",
        "skipped_escape": "symlink escape",
        "skipped_magic_mismatch": "magic mismatch",
        "renamed_detected": "rinominati",
    }
    pieces: list[str] = []
    for key, label in pretty.items():
        n = int(skipped.get(key, 0))
        if n > 0:
            pieces.append(f"{n:,} {label}".replace(",", "."))
    return " · ".join(pieces)


def _spinner_or_icon(status: str) -> str:
    """Icona prefisso a seconda dello status."""
    return {
        "running": "⟳",
        "success": "✓",
        "error": "✗",
        "cancelled": "⊘",
        "interrupted": "⚠",
    }.get(status, "•")


def render_live_progress(
    snapshot: dict[str, Any] | None,
    *,
    title: str = "Job in corso",
) -> None:
    """Renderizza progress live + breakdown.

    Args:
        snapshot: dict ritornato da ``StateStore.get_run_progress`` (con chiavi
            ``status`` + ``progress``) oppure ``None`` se non ancora disponibile.
        title: intestazione da mostrare (es. "Scan filesystem").
    """
    if snapshot is None:
        st.markdown(f"### ⟳ {title}")
        st.caption("In attesa del primo update…")
        st.progress(0.0)
        return

    progress_payload = snapshot.get("progress") or {}
    inner_status = progress_payload.get("status") or snapshot.get("status") or "running"

    icon = _spinner_or_icon(inner_status)
    st.markdown(f"### {icon} {title}")

    total = progress_payload.get("total")
    current = int(progress_payload.get("current", 0) or 0)

    # Progress bar
    if total and total > 0:
        ratio = max(0.0, min(1.0, current / total))
        pct = int(ratio * 100)
        st.progress(ratio, text=f"{pct}% · {current:,} / {total:,} file".replace(",", "."))
    else:
        # Indeterminata: mostriamo un'animazione semplice (progress bar al 0–100% pulsante non c'è in Streamlit base).
        st.progress(0.0, text=f"{current:,} file processati".replace(",", "."))

    # File corrente
    current_item = progress_payload.get("current_item")
    if current_item:
        st.markdown(
            "📄 **Sto leggendo:**  \n"
            f"<code style='font-size:0.85rem;color:#475569;'>{current_item}</code>",
            unsafe_allow_html=True,
        )

    # Throughput + ETA
    throughput = progress_payload.get("throughput_per_sec")
    eta = progress_payload.get("eta_seconds")
    cols = st.columns(2)
    cols[0].metric("Throughput", _format_throughput(throughput))
    cols[1].metric("ETA stimato", _format_seconds(eta))

    # Skipped breakdown
    skipped = progress_payload.get("skipped") or {}
    skipped_text = _format_skipped(skipped)
    errors = int(progress_payload.get("errors", 0) or 0)
    if skipped_text:
        st.caption(f"Skippati: {skipped_text}")
    if errors > 0:
        st.caption(f"⚠ Errori parser: {errors}")


def render_final_summary(
    snapshot: dict[str, Any] | None,
    *,
    title: str,
    extra_lines: list[str] | None = None,
) -> None:
    """Renderizza summary finale (success / cancelled / error)."""
    if snapshot is None:
        st.warning("Nessun dato sul job (è stato pulito troppo presto?).")
        return

    progress_payload = snapshot.get("progress") or {}
    inner_status = progress_payload.get("status") or snapshot.get("status") or "running"
    current = int(progress_payload.get("current", 0) or 0)
    errors = int(progress_payload.get("errors", 0) or 0)
    skipped = progress_payload.get("skipped") or {}
    skipped_text = _format_skipped(skipped)

    if inner_status == "success":
        st.success(f"✓ {title} completato — **{current:,}** file processati".replace(",", "."))
    elif inner_status == "cancelled":
        st.warning(
            f"⊘ {title} annullato dopo **{current:,}** file. I file già "
            "processati sono nello state store; rerun riprenderà via manifest.".replace(",", ".")
        )
    elif inner_status == "interrupted":
        st.error(
            f"⚠ {title} interrotto (crash o kill processo). "
            f"{current:,} file salvati prima dell'interruzione.".replace(",", ".")
        )
    elif inner_status == "error":
        st.error(f"✗ {title} fallito dopo {current:,} file.".replace(",", "."))
    else:
        st.info(f"Status finale: {inner_status}")

    if skipped_text:
        st.caption(f"Skippati: {skipped_text}")
    if errors > 0:
        st.caption(f"Errori parser: {errors}")
    if extra_lines:
        for line in extra_lines:
            st.caption(line)


__all__ = ["render_live_progress", "render_final_summary"]
