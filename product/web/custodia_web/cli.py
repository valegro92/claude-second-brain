"""
Entry CLI ``custodia-web``: avvia ``streamlit run app.py`` con i flag giusti.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Wrap di ``streamlit run`` che punta sempre allo stesso ``app.py``."""
    # Lazy import: evita di caricare streamlit se l'utente fa solo --help.
    from streamlit.web import cli as stcli

    app_path = Path(__file__).resolve().parent.parent / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
