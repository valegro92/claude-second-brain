"""
Custodia MCP Server - espone vault Obsidian a Claude Code / Codex / Hermes.

Tool esposti:
- list_clients: elenco compatto di tutti i clienti nel vault
- get_client: scheda completa cliente (frontmatter strutturato + body markdown)
- search_vault: ricerca full-text su tutto il vault
- recent_communications: ultime N comunicazioni inbox ordinate per data

Trasporto: stdio (compatibile Claude Code mcp config).
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from markdown body. Returns ({}, text) if no frontmatter."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


class Vault:
    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ValueError(f"Vault root non esiste: {self.root}")

    def _iter_md(self, subdir: str | None = None) -> list[Path]:
        base = self.root / subdir if subdir else self.root
        if not base.exists():
            return []
        return sorted(p for p in base.rglob("*.md") if p.is_file())

    def list_clients(self) -> list[dict[str, Any]]:
        out = []
        for path in self._iter_md("clienti"):
            fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": path.stem,
                    "nome": fm.get("nome", path.stem),
                    "settore": fm.get("settore"),
                    "stato_relazione": fm.get("stato_relazione"),
                    "ultimo_contatto": str(fm.get("ultimo_contatto", "")),
                    "fatturato_2025_ytd": fm.get("fatturato_2025_ytd"),
                }
            )
        return out

    def get_client(self, client_id: str) -> dict[str, Any]:
        path = self.root / "clienti" / f"{client_id}.md"
        if not path.exists():
            return {"error": f"cliente '{client_id}' non trovato"}
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        return {"id": client_id, "frontmatter": fm, "body": body.strip()}

    def search_vault(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        hits = []
        for path in self._iter_md():
            text = path.read_text(encoding="utf-8")
            matches = list(pattern.finditer(text))
            if not matches:
                continue
            # Snippet around first match
            m = matches[0]
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            snippet = text[start:end].replace("\n", " ").strip()
            hits.append(
                {
                    "path": str(path.relative_to(self.root)),
                    "occorrenze": len(matches),
                    "snippet": f"...{snippet}...",
                }
            )
            if len(hits) >= limit:
                break
        return hits

    def recent_communications(self, limit: int = 5) -> list[dict[str, Any]]:
        out = []
        for path in self._iter_md("inbox"):
            fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            out.append(
                {
                    "path": str(path.relative_to(self.root)),
                    "data": str(fm.get("data", "")),
                    "da": fm.get("da"),
                    "oggetto": fm.get("oggetto"),
                    "cliente_collegato": fm.get("cliente_collegato"),
                    "stato": fm.get("stato"),
                    "corpo": body.strip(),
                }
            )
        out.sort(key=lambda x: x["data"], reverse=True)
        return out[:limit]


def build_server(vault_root: Path) -> FastMCP:
    vault = Vault(vault_root)
    mcp = FastMCP("custodia")

    @mcp.tool()
    def list_clients() -> list[dict[str, Any]]:
        """Elenco compatto di tutti i clienti nel vault con metadati principali."""
        return vault.list_clients()

    @mcp.tool()
    def get_client(client_id: str) -> dict[str, Any]:
        """
        Scheda completa di un cliente: frontmatter strutturato (condizioni, eccezioni,
        storico) e body markdown narrativo.

        Args:
            client_id: identificativo cliente (es. 'rossetto-laminazioni').
                       Vedere list_clients per gli id disponibili.
        """
        return vault.get_client(client_id)

    @mcp.tool()
    def search_vault(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Ricerca full-text case-insensitive su tutto il vault. Restituisce path,
        numero occorrenze e snippet attorno al primo match.

        Args:
            query: stringa da cercare
            limit: max risultati (default 10)
        """
        return vault.search_vault(query, limit)

    @mcp.tool()
    def recent_communications(limit: int = 5) -> list[dict[str, Any]]:
        """
        Ultime comunicazioni nell'inbox del vault, ordinate per data discendente.
        Include corpo email e cliente collegato.

        Args:
            limit: numero massimo di messaggi (default 5)
        """
        return vault.recent_communications(limit)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Custodia MCP server")
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path(os.environ.get("CUSTODIA_VAULT", "./vault-demo")),
        help="Path al vault Obsidian (default: $CUSTODIA_VAULT o ./vault-demo)",
    )
    args = parser.parse_args()
    server = build_server(args.vault)
    server.run()


if __name__ == "__main__":
    main()
