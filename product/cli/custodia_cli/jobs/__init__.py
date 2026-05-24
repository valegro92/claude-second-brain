"""
custodia_cli.jobs: infrastruttura per eseguire scan/build in modo asincrono.

Esporta:
- :class:`Job`, :class:`JobRunner`, :class:`JobStatus`
- :class:`CancelToken`, :class:`CancelledError`
- :class:`ProgressReporter`, :class:`ProgressSnapshot`

Single-user locale, AsyncIO + threading in-process. Niente Redis/Celery.
"""

from __future__ import annotations

from custodia_cli.jobs.cancel import CancelledError, CancelToken
from custodia_cli.jobs.progress import ProgressReporter, ProgressSnapshot
from custodia_cli.jobs.runner import Job, JobRunner, JobStatus

__all__ = [
    "CancelToken",
    "CancelledError",
    "Job",
    "JobRunner",
    "JobStatus",
    "ProgressReporter",
    "ProgressSnapshot",
]
