"""
Test per ``custodia_web.services.job_state``.

Verifichiamo il roundtrip set/get/clear su ``st.session_state``. Streamlit
in bare mode (senza ``streamlit run``) emette warning ma supporta comunque
session_state come dict-like, sufficiente per i test.
"""

from __future__ import annotations

import threading

import pytest
import streamlit as st

from custodia_cli.jobs import CancelToken
from custodia_web.services import job_state


@pytest.fixture(autouse=True)
def _reset_session_state():
    """Pulisce session_state prima e dopo ogni test."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def _make_active_job() -> job_state.ActiveJob:
    return job_state.ActiveJob(
        run_id=1,
        token=CancelToken(),
        kind="scan",
        thread=threading.Thread(target=lambda: None),
        label="test scan",
    )


def test_get_active_jobs_returns_empty_initially() -> None:
    assert job_state.get_active_jobs() == {}


def test_set_and_get_active_job_roundtrip() -> None:
    job = _make_active_job()
    job_state.set_active_job("proj-a", job)
    fetched = job_state.get_active_job("proj-a")
    assert fetched is job
    assert fetched.run_id == 1


def test_get_active_job_missing_returns_none() -> None:
    assert job_state.get_active_job("nonexistent") is None


def test_clear_active_job_removes_entry() -> None:
    job = _make_active_job()
    job_state.set_active_job("proj-a", job)
    job_state.clear_active_job("proj-a")
    assert job_state.get_active_job("proj-a") is None


def test_clear_active_job_no_op_when_missing() -> None:
    # Non deve sollevare.
    job_state.clear_active_job("never-existed")
    assert job_state.get_active_jobs() == {}


def test_has_active_job_with_kind_filter() -> None:
    job = _make_active_job()
    job_state.set_active_job("proj-a", job)
    assert job_state.has_active_job("proj-a")
    assert job_state.has_active_job("proj-a", "scan")
    assert not job_state.has_active_job("proj-a", "build")
    assert not job_state.has_active_job("proj-b")


def test_multiple_projects_isolated() -> None:
    job_a = _make_active_job()
    job_b = job_state.ActiveJob(
        run_id=42,
        token=CancelToken(),
        kind="build",
        thread=threading.Thread(target=lambda: None),
        label="build x",
    )
    job_state.set_active_job("a", job_a)
    job_state.set_active_job("b", job_b)
    assert job_state.get_active_job("a").run_id == 1
    assert job_state.get_active_job("b").run_id == 42
    job_state.clear_active_job("a")
    assert job_state.get_active_job("a") is None
    assert job_state.get_active_job("b") is not None
