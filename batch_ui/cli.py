"""Entry point CLI: `python -m batch_ui` -> avvia il server e apre il browser.

Flag:
  --port INT       porta di ascolto (default 7423)
  --host TEXT      host (default 127.0.0.1)
  --no-browser     non aprire automaticamente il browser
  --debug          avvia Flask in modalita' debug (no reloader)
"""

from __future__ import annotations

import logging
import threading
import time
import webbrowser

import click

from .server import create_app

logger = logging.getLogger(__name__)


@click.command()
@click.option("--port", default=7423, show_default=True, help="Porta di ascolto.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host di ascolto.")
@click.option("--no-browser", is_flag=True, default=False, help="Non aprire il browser all'avvio.")
@click.option("--debug", is_flag=True, default=False, help="Avvia in debug mode.")
def main(port: int, host: str, no_browser: bool, debug: bool) -> None:
    """Avvia il server Flask del batch approval workflow."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = create_app()
    url = f"http://{host}:{port}/"
    if not no_browser:
        # Apri il browser un attimo dopo che il server e' su (best-effort).
        def _open() -> None:
            time.sleep(0.8)
            try:
                webbrowser.open(url)
            except Exception as exc:  # pragma: no cover - non blocca l'avvio
                logger.warning("Apertura browser fallita: %s", exc)

        threading.Thread(target=_open, daemon=True).start()
    click.echo(f"batch_ui in ascolto su {url}  (Ctrl-C per terminare)")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":  # pragma: no cover - exercized via `python -m batch_ui`
    main()
