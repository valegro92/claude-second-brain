# _brief/ — Planning Step 2 e Step 3

Cartella di note di pianificazione del prodotto. Non è documentazione utente: vive qui come riferimento di design per chi continuerà l'implementazione.

I brief Step 1 (`00-product-vision`, `01-audit-issues`, `02-framework-pmi`, `03-manuale-custode-draft`) sono stati rimossi a fine Step 1: i loro contenuti sono ora nei file finali (`vault/`, `skills/`, `docs/`).

## Cosa resta

| File | Contenuto | Quando serve |
|---|---|---|
| `04-step-2-tech-plan.md` | Architettura tecnica completa di scanner/extractor/categorizer/reconciler/batch-UI. Layout cartelle, sprint roadmap 6-8 settimane, Python+uv+Flask+HTMX. | Prima riga di codice dello Step 2. |
| `05-mcp-audit.md` | Verifica MCP server per le 5 fonti (Google Drive, M365, Email, NAS, server). Verdetti per ognuna: cosa riusare, cosa scrivere custom, cosa escludere v1. | Sprint 0 di Step 2, per decidere le dipendenze. |
| `06-cost-and-risk.md` | Cost model lato Valentino (~5.300 EUR/cliente, break-even 9 clienti/anno), 3 modelli pricing, audit GDPR+settoriale, contratto skeleton, 5 obiezioni tipiche. | Prima della firma del primo contratto cliente. Da rivedere con avvocato GDPR italiano. |
| `07-naming-brand.md` | 14 candidati nome prodotto, shortlist 4 finalisti, raccomandazione finale ("Catasto") con razionale e checklist verifica pre-adozione. | Quando si decide il naming pubblico del prodotto, prima del primo sito/preventivo formale. |

## Cosa non c'è qui

- Documentazione utente (vive in `docs/`)
- Codice (lo Step 2 lo metterà in `bootstrap/`, `scanners/`, `extractors/`, ecc.)
- Materiali commerciali finali (slide, video demo — Step 3)
