"""Mini web UI locale per l'approvazione batch delle bozze (Step 2, sezione 6 del tech plan).

Pacchetto Flask + HTMX + Pico.css. Single-user, ascolta su 127.0.0.1.
"""

from __future__ import annotations

from .server import create_app

__all__ = ["create_app"]
