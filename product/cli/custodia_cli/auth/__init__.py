"""Helper di autenticazione per i connettori Custodia."""

from __future__ import annotations

from custodia_cli.auth.fic_oauth import get_fic_access_token
from custodia_cli.auth.google_oauth import get_credentials
from custodia_cli.auth.microsoft_oauth import get_access_token

__all__ = ["get_credentials", "get_access_token", "get_fic_access_token"]
