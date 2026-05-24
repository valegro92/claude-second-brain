"""Test diff candidato vs vault esistente."""

from __future__ import annotations

from pathlib import Path

from custodia_cli.review.diff import (
    diff_frontmatter,
    existing_vault_path,
    render_diff,
)


def test_diff_identical_all_same() -> None:
    fm = {"nome": "X", "settore": "metal"}
    rows = diff_frontmatter(fm, fm)
    assert all(s == "same" for s, _, _ in rows)


def test_diff_new_field() -> None:
    rows = diff_frontmatter({"nome": "X", "settore": "metal"}, {"nome": "X"})
    statuses = {k: s for s, k, _ in rows}
    assert statuses["settore"] == "new"
    assert statuses["nome"] == "same"


def test_diff_changed_field() -> None:
    rows = diff_frontmatter({"nome": "Y"}, {"nome": "X"})
    statuses = {k: s for s, k, _ in rows}
    assert statuses["nome"] == "changed"
    # repr include both old and new
    repr_text = next(r for s, k, r in rows if k == "nome")
    assert "X" in repr_text and "Y" in repr_text


def test_diff_lost_field() -> None:
    rows = diff_frontmatter({"nome": "X"}, {"nome": "X", "vecchio": 42})
    statuses = {k: s for s, k, _ in rows}
    assert statuses["vecchio"] == "lost"


def test_render_diff_no_existing_file(tmp_path: Path) -> None:
    out = render_diff({"nome": "X"}, tmp_path / "missing.md")
    # Renderable rich; rendering a string contiene "Nuova entità".
    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(out)
    text = console.export_text()
    assert "Nuova entità" in text


def test_render_diff_identical(tmp_path: Path) -> None:
    existing = tmp_path / "x.md"
    existing.write_text(
        "---\nnome: X\n---\nbody\n", encoding="utf-8"
    )
    out = render_diff({"nome": "X"}, existing)
    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(out)
    text = console.export_text()
    assert "Nessun cambiamento" in text


def test_render_diff_with_changes(tmp_path: Path) -> None:
    existing = tmp_path / "x.md"
    existing.write_text(
        "---\nnome: X\nsettore: vecchio\n---\nbody\n", encoding="utf-8"
    )
    out = render_diff({"nome": "X", "settore": "nuovo", "extra": 1}, existing)
    from rich.console import Console

    console = Console(record=True, width=120)
    console.print(out)
    text = console.export_text()
    # cambio + nuovo campo visibili
    assert "settore" in text
    assert "extra" in text


def test_existing_vault_path_uses_plural(tmp_path: Path) -> None:
    p = existing_vault_path(tmp_path, "cliente", "acme")
    assert p == tmp_path / "clienti" / "acme.md"
    p2 = existing_vault_path(tmp_path, "fornitore", "delta")
    assert p2 == tmp_path / "fornitori" / "delta.md"
