"""Test del file watcher.

Strategia: crea cartella tmp, lancia watcher in modalità non-blocking, scrive
un file dentro, attende che il callback (mock di ``run_pipeline_for_file``)
venga invocato, ferma il watcher.

Niente segnali POSIX (i test possono girare fuori dal main thread).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from wiki.watcher import InboxHandler, _DebounceState, start_watcher


# --- debounce -------------------------------------------------------------


def test_debounce_blocks_second_call_within_window() -> None:
    state = _DebounceState()
    assert state.should_process("/tmp/x", debounce_s=1.0) is True
    # Subito dopo: debounced
    assert state.should_process("/tmp/x", debounce_s=1.0) is False


def test_debounce_allows_after_window(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _DebounceState()
    # Forziamo il "tempo" del modulo a valori controllati
    fake_now = [100.0]
    monkeypatch.setattr("wiki.watcher.time.monotonic", lambda: fake_now[0])
    assert state.should_process("/tmp/x", 1.0) is True
    fake_now[0] = 100.5
    assert state.should_process("/tmp/x", 1.0) is False
    fake_now[0] = 102.0
    assert state.should_process("/tmp/x", 1.0) is True


# --- handler --------------------------------------------------------------


class _RecorderEvent:
    """Mock di FileSystemEvent compatibile con il subset usato dal handler."""

    def __init__(self, src_path: str, is_directory: bool = False) -> None:
        self.src_path = src_path
        self.is_directory = is_directory


def test_handler_invokes_pipeline_on_create(tmp_path: Path) -> None:
    calls: list[Path] = []

    def fake_pipeline(p: Path, _cfg: dict[str, Any], _state: Path) -> Any:
        calls.append(p)
        return None

    handler = InboxHandler(
        config={},
        state_dir=tmp_path / "state",
        pipeline=fake_pipeline,
        debounce_s=0.0,  # niente debounce: testiamo la dispatch base
    )
    f = tmp_path / "documento.txt"
    f.write_text("ciao", encoding="utf-8")
    handler.on_created(_RecorderEvent(str(f)))
    assert calls == [f]


def test_handler_ignores_directory_events(tmp_path: Path) -> None:
    calls: list[Path] = []

    def fake_pipeline(p: Path, _cfg: dict[str, Any], _state: Path) -> Any:
        calls.append(p)

    handler = InboxHandler(config={}, state_dir=tmp_path, pipeline=fake_pipeline, debounce_s=0.0)
    handler.on_created(_RecorderEvent(str(tmp_path / "subdir"), is_directory=True))
    assert calls == []


def test_handler_ignores_editor_temp_files(tmp_path: Path) -> None:
    calls: list[Path] = []

    def fake_pipeline(p: Path, _cfg: dict[str, Any], _state: Path) -> Any:
        calls.append(p)

    handler = InboxHandler(config={}, state_dir=tmp_path, pipeline=fake_pipeline, debounce_s=0.0)
    # Crea fisicamente i file per oltrepassare il check exists()
    for name in (".hidden", "file.swp", "doc~"):
        (tmp_path / name).write_text("x")
        handler.on_created(_RecorderEvent(str(tmp_path / name)))
    assert calls == []


def test_handler_does_not_crash_on_missing_file(tmp_path: Path) -> None:
    """Se on_modified arriva per un path appena cancellato, non deve crashare."""

    def fake_pipeline(*_args: Any, **_kw: Any) -> Any:
        raise AssertionError("non dovrebbe essere chiamato per file inesistente")

    handler = InboxHandler(config={}, state_dir=tmp_path, pipeline=fake_pipeline, debounce_s=0.0)
    handler.on_modified(_RecorderEvent(str(tmp_path / "gone.txt")))


# --- end-to-end con Observer reale ----------------------------------------


def test_start_watcher_end_to_end(tmp_path: Path) -> None:
    """Avvia il watcher reale, droppa un file, verifica che il pipeline mock parte."""
    inbox = tmp_path / "_inbox"
    state = tmp_path / "_status"
    calls: list[Path] = []

    def fake_pipeline(p: Path, _cfg: dict[str, Any], _state: Path) -> Any:
        calls.append(p)

    observer = start_watcher(
        inbox_dir=inbox,
        config={},
        state_dir=state,
        pipeline=fake_pipeline,
        debounce_s=0.0,
        install_signal_handlers=False,
        block=False,
    )
    try:
        # Aspetta che l'observer sia operativo
        time.sleep(0.2)
        f = inbox / "primo.txt"
        f.write_text("hello", encoding="utf-8")
        # Poll fino a 3s per il callback
        deadline = time.monotonic() + 3.0
        while not calls and time.monotonic() < deadline:
            time.sleep(0.05)
        assert calls, "il pipeline non è stato chiamato entro 3s"
        assert calls[0].name == "primo.txt"
        # Verifica anche il pidfile (heartbeat scrive subito)
        assert (state / "watcher.pid").exists()
    finally:
        observer.stop()
        observer.join(timeout=2.0)
