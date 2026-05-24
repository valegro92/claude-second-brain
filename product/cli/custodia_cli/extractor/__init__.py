"""
Extractor LLM-driven per Custodia (U5).

Trasforma stream di SourceDocument in EntityCandidate conformi allo schema
canonical delle schede vault (cliente, fornitore, commessa, comunicazione).

Pipeline a 2 stadi:
1. Categorize (FAST tier): identifica quali entità di un dato tipo compaiono
2. Extract (SMART tier): estrae i campi strutturati via tool-use forzato

Doc multi-chunk: chunk_document() -> merge_entity_candidates() ragionato.
Doc multi-fonte stessa entità: aggregazione conservativa, union su liste,
preferenza confidence più alta sui scalari.
"""

from __future__ import annotations

from custodia_cli.extractor.extractor import EntityCandidate, Extractor

__all__ = ["EntityCandidate", "Extractor"]
