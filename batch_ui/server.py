"""Server Flask del batch approval workflow (Step 2 sezione 6 del tech plan).

Endpoint:
  GET  /                                              lista dei batch
  GET  /batch/<batch_id>                              dettaglio batch
  GET  /batch/<batch_id>/draft/<draft_name>           HTMX: diff viewer della bozza
  POST /batch/<batch_id>/draft/<draft_name>/<action>  cambia stato (approve|reject|park|edit)
  POST /batch/<batch_id>/bulk-approve                 approva tutte le bozze con conf >= soglia
  POST /batch/<batch_id>/flush                        applica al vault + log decisioni
  GET  /healthz                                       200 per il watcher

Ascolta su 127.0.0.1:7423 (single-user, locale, niente auth).

Configurazione via env vars (utili per i test):
  WIKI_STATUS_DIR  -> path a `_status/`  (default: <cwd>/_status)
  WIKI_VAULT_ROOT  -> path a `vault/`    (default: <cwd>/vault)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, request

from categorizers._enums import StatoBozza

from . import drafts as drafts_mod
from . import flush as flush_mod
from . import state as state_mod

logger = logging.getLogger(__name__)

# Mapping da stringa azione URL allo stato target.
_ACTION_TO_STATO: dict[str, StatoBozza] = {
    "approve": StatoBozza.APPROVED,
    "reject": StatoBozza.REJECTED,
    "park": StatoBozza.PARKED,
    "edit": StatoBozza.EDITED,
}


def create_app(
    *,
    status_dir: Path | None = None,
    vault_root: Path | None = None,
    testing: bool = False,
) -> Flask:
    """Crea l'app Flask. Path overridabili per i test."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["STATUS_DIR"] = Path(
        status_dir or os.environ.get("WIKI_STATUS_DIR") or Path.cwd() / "_status"
    )
    app.config["VAULT_ROOT"] = Path(
        vault_root or os.environ.get("WIKI_VAULT_ROOT") or Path.cwd() / "vault"
    )
    app.config["TESTING"] = testing
    _register_routes(app)
    return app


def _drafts_root(app: Flask) -> Path:
    return app.config["STATUS_DIR"] / "drafts"


def _batch_dir(app: Flask, batch_id: str) -> Path:
    """Risolve la cartella di un batch, abortendo 404 se non esiste o e' fuori dal root."""
    root = _drafts_root(app)
    candidate = (root / batch_id).resolve()
    # Sicurezza minima: niente path traversal anche se siamo single-user 127.0.0.1.
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        abort(404)
    if not candidate.exists() or not candidate.is_dir():
        abort(404)
    return candidate


def _draft_path(batch_dir: Path, draft_name: str) -> Path:
    """Risolve il path di una bozza, abortendo 404 se non valida."""
    candidate = (batch_dir / draft_name).resolve()
    try:
        candidate.relative_to(batch_dir.resolve())
    except ValueError:
        abort(404)
    if not candidate.exists() or candidate.suffix != ".md":
        abort(404)
    return candidate


def _register_routes(app: Flask) -> None:
    @app.route("/healthz")
    def healthz() -> Any:
        return ("ok", 200, {"Content-Type": "text/plain; charset=utf-8"})

    @app.route("/")
    def index() -> Any:
        batches = drafts_mod.list_batches(_drafts_root(app))
        summary = []
        for bid in batches:
            bdir = _drafts_root(app) / bid
            names = [d.name for d in drafts_mod.list_drafts(bdir)]
            counts = state_mod.count_by_stato(bdir, names)
            summary.append({"id": bid, "total": len(names), "counts": counts})
        return render_template("index.html", batches=summary)

    @app.route("/batch/<batch_id>")
    def batch_view(batch_id: str) -> Any:
        bdir = _batch_dir(app, batch_id)
        drafts = drafts_mod.list_drafts(bdir)
        state = state_mod.load_state(bdir)
        rows = []
        for d in drafts:
            entry = state.get(d.name, {})
            rows.append(
                {
                    "draft": d,
                    "stato": entry.get("stato", StatoBozza.PENDING.value),
                    "ts": entry.get("ts"),
                    "edits": entry.get("edits"),
                }
            )
        counts = state_mod.count_by_stato(bdir, [d.name for d in drafts])
        filtro = request.args.get("filtro")
        if filtro:
            rows = [r for r in rows if _matches_filtro(r, filtro)]
        return render_template(
            "batch.html",
            batch_id=batch_id,
            rows=rows,
            counts=counts,
            filtro=filtro or "tutte",
            stati=[s.value for s in StatoBozza],
        )

    @app.route("/batch/<batch_id>/draft/<path:draft_name>", methods=["GET"])
    def draft_view(batch_id: str, draft_name: str) -> Any:
        bdir = _batch_dir(app, batch_id)
        path = _draft_path(bdir, draft_name)
        draft = drafts_mod.load_draft(path)
        entry = state_mod.get_draft_state(bdir, draft.name)
        diff_html = drafts_mod.render_diff_viewer(draft)
        return render_template(
            "_diff_viewer.html",
            batch_id=batch_id,
            draft=draft,
            stato=entry.get("stato"),
            diff_html=diff_html,
        )

    @app.route("/batch/<batch_id>/draft/<path:draft_name>/<action>", methods=["POST"])
    def draft_action(batch_id: str, draft_name: str, action: str) -> Any:
        bdir = _batch_dir(app, batch_id)
        path = _draft_path(bdir, draft_name)
        if action not in _ACTION_TO_STATO:
            abort(400, description=f"Azione non valida: {action}")
        stato = _ACTION_TO_STATO[action]
        edits = None
        note = None
        if action == "edit":
            edits = request.form.get("edits") or request.form.get("content")
            if not edits:
                abort(400, description="Edit senza contenuto")
        if "note" in request.form:
            note = request.form.get("note")
        state_mod.set_draft_state(bdir, draft_name, stato, edits=edits, note=note)
        # Restituisce il partial della singola riga aggiornata (HTMX swap)
        draft = drafts_mod.load_draft(path)
        entry = state_mod.get_draft_state(bdir, draft.name)
        return render_template(
            "_draft_row.html",
            batch_id=batch_id,
            draft=draft,
            stato=entry.get("stato"),
            ts=entry.get("ts"),
            edits=entry.get("edits"),
        )

    @app.route("/batch/<batch_id>/bulk-approve", methods=["POST"])
    def bulk_approve(batch_id: str) -> Any:
        bdir = _batch_dir(app, batch_id)
        try:
            threshold = float(request.form.get("threshold", "0.85"))
        except ValueError:
            threshold = 0.85
        approved = 0
        for draft in drafts_mod.list_drafts(bdir):
            entry = state_mod.get_draft_state(bdir, draft.name)
            if entry.get("stato") not in (StatoBozza.PENDING.value, StatoBozza.PARKED.value):
                continue
            conf = draft.confidence
            if conf is not None and conf >= threshold:
                state_mod.set_draft_state(bdir, draft.name, StatoBozza.APPROVED)
                approved += 1
        return jsonify({"approved": approved, "threshold": threshold})

    @app.route("/batch/<batch_id>/flush", methods=["POST"])
    def flush(batch_id: str) -> Any:
        bdir = _batch_dir(app, batch_id)
        policy = request.form.get("conflict_policy", "skip")
        if policy not in ("skip", "overwrite", "rename", "merge"):
            policy = "skip"
        user = request.form.get("user") or "valentino"
        result = flush_mod.flush_batch(
            batch_dir=bdir,
            status_dir=app.config["STATUS_DIR"],
            vault_root=app.config["VAULT_ROOT"],
            user=user,
            conflict_policy=policy,  # type: ignore[arg-type]
        )
        return jsonify(result.as_dict())

    @app.errorhandler(404)
    def _not_found(_err: Any) -> Any:
        return (jsonify({"error": "not found"}), 404)

    @app.errorhandler(400)
    def _bad_request(err: Any) -> Any:
        return (jsonify({"error": "bad request", "detail": str(err.description)}), 400)


def _matches_filtro(row: dict[str, Any], filtro: str) -> bool:
    """Filtro veloce sulla vista batch (per nome bozza o per stato)."""
    filtro = filtro.lower()
    if filtro == "tutte":
        return True
    if filtro in {s.value for s in StatoBozza}:
        return row["stato"] == filtro
    name = row["draft"].name.lower()
    # Filtri rapidi semantici
    if filtro == "schede":
        return "scheda" in name
    if filtro == "dedup":
        return "dedup" in name
    if filtro == "persone":
        return "person" in name or "persona" in name
    return filtro in name


def run(host: str = "127.0.0.1", port: int = 7423, debug: bool = False) -> None:
    """Avvia il server Flask in modo bloccante."""
    app = create_app()
    logger.info("batch_ui avviato su http://%s:%d", host, port)
    app.run(host=host, port=port, debug=debug, use_reloader=False)
