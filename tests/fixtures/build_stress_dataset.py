"""Genera un dataset di **stress test realistico** per validare il pipeline su volumi PMI piccoli-medi.

Differenze rispetto a ``build_pilot_dataset``:
  * **150 file** (vs 48), distribuiti su 5 clienti + 4 fornitori + 3 anni
  * Pattern italiani specifici: fatture emesse/ricevute, DDT, conferme ordine,
    contratti quadro, listini, manuali tecnici fornitore
  * File con caratteri italiani nel nome (à, è, ì, ò, ù)
  * File con spazi e accenti (test ricezione filesystem)
  * 3 file binari grossi (>40 MB simulati come sparse) per testare filtro size
  * Cartella ``_OLD_NON_USARE/`` con 15 file vecchi (3+ anni)
  * Cartella ``Backup_2022/`` con 5 zip da escludere
  * 10 coppie di file duplicati (sha identici cross-cartella)
  * 8 sequenze ``_v1/_v2/_v3/_FINAL`` per testare dedup soft

Output: ``_status/stress/`` (di default) con struttura realistica:

    _inbox/stress/
    ├── Clienti/
    │   ├── Rossi_Srl/
    │   ├── Bianchi_SpA/
    │   ├── Verdi_Costruzioni/
    │   ├── Neri_Forniture/
    │   └── Gialli_Industriale/
    ├── Fornitori/
    │   ├── ACME_Acciai/
    │   ├── Borghi_Componenti/
    │   ├── Centrale_Logistica/
    │   └── Delta_Software/
    ├── _OLD_NON_USARE/
    ├── Backup_2022/
    └── Modelli/

Uso CLI::

    python -m tests.fixtures.build_stress_dataset --output /tmp/stress/_inbox/stress/

Idempotente: cancella e rigenera. Seed fisso per riproducibilità.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

from tests.fixtures.build_pilot_dataset import (
    GeneratedFile,
    _add,
    _generate_docx,
    _generate_eml,
    _generate_pdf,
    _generate_txt,
    _generate_xlsx,
    _set_mtime,
    _setup_random,
)

logger = logging.getLogger("tests.fixtures.build_stress_dataset")

# Soggetti: 5 clienti + 4 fornitori
CLIENTI = [
    ("Rossi Srl", "rossi-srl"),
    ("Bianchi SpA", "bianchi-spa"),
    ("Verdi Costruzioni", "verdi-costruzioni"),
    ("Neri Forniture", "neri-forniture"),
    ("Gialli Industriale", "gialli-industriale"),
]

FORNITORI = [
    ("ACME Acciai", "acme-acciai"),
    ("Borghi Componenti", "borghi-componenti"),
    ("Centrale Logistica", "centrale-logistica"),
    ("Delta Software", "delta-software"),
]

# Anni di riferimento: il "presente" e' 2026
ANNO_CORRENTE = 2026
ANNI_RECENTI = [2024, 2025, 2026]
ANNI_ARCHIVIO = [2020, 2021, 2022]


def _dt(anno: int, mese: int = 6) -> datetime:
    """Helper: data UTC al primo del mese."""
    return datetime(anno, mese, 1, 12, 0, tzinfo=timezone.utc)


def _testo_fattura(numero: str, controparte: str, importo: float, anno: int) -> tuple[str, str]:
    titolo = f"Fattura {numero} del {anno}"
    body = (
        f"FATTURA N. {numero}\n"
        f"Data: 15/06/{anno}\n"
        f"Cliente: {controparte}\n\n"
        f"Descrizione: Fornitura materiale tecnico per commessa {anno}-Q2.\n"
        f"Importo imponibile: EUR {importo:,.2f}\n"
        f"IVA 22%: EUR {importo * 0.22:,.2f}\n"
        f"Totale: EUR {importo * 1.22:,.2f}\n\n"
        f"Pagamento: bonifico a 30gg data fattura.\n"
        f"IBAN: IT99X0123456789012345678901\n"
    )
    return titolo, body


def _testo_ddt(numero: str, cliente: str, anno: int) -> tuple[str, str]:
    titolo = f"DDT {numero} del {anno}"
    body = (
        f"DOCUMENTO DI TRASPORTO N. {numero}\n"
        f"Data spedizione: 12/06/{anno}\n"
        f"Destinatario: {cliente}\n\n"
        f"Causale: vendita\n"
        f"Vettore: corriere espresso\n\n"
        f"Articolo 1: Lamiera acciaio inox AISI 304 - 50 kg\n"
        f"Articolo 2: Bulloneria varia - 1 collo\n"
        f"Articolo 3: Cuscinetti SKF 6205 - 12 pz\n\n"
        f"Peso lordo: 78 kg | Colli: 3\n"
    )
    return titolo, body


def _testo_conferma_ordine(numero: str, cliente: str, anno: int) -> tuple[str, str]:
    titolo = f"Conferma ordine {numero}"
    body = (
        f"CONFERMA D'ORDINE N. {numero}\n"
        f"Data: 05/06/{anno}\n"
        f"Cliente: {cliente}\n\n"
        f"Confermiamo l'accettazione del Vs ordine con consegna prevista entro 30gg.\n"
        f"Importo totale: EUR 12.500,00 + IVA\n"
        f"Modalità pagamento: 30% acconto, 70% saldo a consegna.\n\n"
        f"Ringraziamo per la fiducia accordata.\n"
    )
    return titolo, body


def _testo_listino(fornitore: str, anno: int) -> tuple[str, str]:
    titolo = f"Listino {fornitore} {anno}"
    body = (
        f"LISTINO PREZZI {anno} - {fornitore}\n\n"
        f"Codice    Descrizione                    Prezzo unitario\n"
        f"L001      Lamiera acciaio 2mm           EUR 18,50/kg\n"
        f"L002      Lamiera acciaio 3mm           EUR 19,80/kg\n"
        f"L003      Tubo inox DN50                EUR 32,40/m\n"
        f"L004      Profilato L 50x50             EUR 12,30/m\n\n"
        f"Condizioni: porto franco destinazione, pagamento 60gg DF.\n"
        f"Sconto quantità: 5% > 1000 EUR, 8% > 5000 EUR.\n"
    )
    return titolo, body


def _testo_manuale(componente: str, fornitore: str) -> tuple[str, str]:
    titolo = f"Manuale {componente}"
    body = (
        f"MANUALE TECNICO - {componente}\n"
        f"Fornitore: {fornitore}\n\n"
        f"1. Installazione\n"
        f"Verificare la planarita' del piano di appoggio. Coppia di serraggio bulloni: 35 Nm.\n\n"
        f"2. Manutenzione\n"
        f"Ispezione visiva ogni 500 ore. Sostituzione cuscinetti ogni 5000 ore.\n\n"
        f"3. Sicurezza\n"
        f"Non avviare con carter di protezione aperto. Tensione: 400V trifase.\n"
    )
    return titolo, body


def _testo_contratto_quadro(cliente: str, anno: int) -> tuple[str, str]:
    titolo = f"Contratto quadro {cliente} {anno}"
    body = (
        f"CONTRATTO QUADRO DI FORNITURA - {anno}\n\n"
        f"Tra {cliente} (committente) e la nostra azienda (fornitore).\n\n"
        f"Art. 1 - Oggetto\n"
        f"Fornitura continuativa di materiale tecnico secondo listino allegato.\n\n"
        f"Art. 2 - Durata\n"
        f"Anno solare {anno}, rinnovo tacito salvo disdetta entro 60gg.\n\n"
        f"Art. 3 - Modalità\n"
        f"Ordini via email a sales@azienda.it. Conferma entro 24h lavorative.\n\n"
        f"Art. 4 - Pagamento\n"
        f"30gg data fattura, bonifico bancario.\n"
    )
    return titolo, body


def _add_clienti_files(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Aggiunge ~80 file distribuiti tra i 5 clienti."""
    for cliente_nome, cliente_slug in CLIENTI:
        cliente_dir = output_dir / "Clienti" / cliente_nome.replace(" ", "_")
        cliente_dir.mkdir(parents=True, exist_ok=True)
        offerte_dir = cliente_dir / "Offerte"
        offerte_dir.mkdir(exist_ok=True)
        ordini_dir = cliente_dir / "Ordini"
        ordini_dir.mkdir(exist_ok=True)
        fatture_dir = cliente_dir / "Fatture"
        fatture_dir.mkdir(exist_ok=True)

        # 3 fatture emesse (uno per anno recente)
        for i, anno in enumerate(ANNI_RECENTI):
            num = f"{anno}/{(i + 1) * 17:04d}"
            tit, body = _testo_fattura(num, cliente_nome, 8500 + i * 1500, anno)
            path = _generate_pdf(
                fatture_dir / f"fattura_{anno}_{(i + 1) * 17:04d}.pdf",
                tit,
                body,
                _dt(anno, 6),
            )
            _add(generated, path, cliente_slug, str(anno), "fattura")

        # 2 DDT (anno corrente)
        for i in range(2):
            num = f"{ANNO_CORRENTE}/{200 + i:03d}"
            tit, body = _testo_ddt(num, cliente_nome, ANNO_CORRENTE)
            path = _generate_pdf(
                cliente_dir / f"ddt_{ANNO_CORRENTE}_{200 + i:03d}.pdf",
                tit,
                body,
                _dt(ANNO_CORRENTE, 6 + i),
            )
            _add(generated, path, cliente_slug, str(ANNO_CORRENTE), "ddt")

        # 2 conferme ordine
        for i, anno in enumerate(ANNI_RECENTI[:2]):
            num = f"CO-{anno}-{i + 1:03d}"
            tit, body = _testo_conferma_ordine(num, cliente_nome, anno)
            path = _generate_eml(
                ordini_dir / f"conferma_{num}.eml",
                "ufficio.ordini@azienda.it",
                f"acquisti@{cliente_slug}.it",
                tit,
                body,
                _dt(anno, 5),
            )
            _add(generated, path, cliente_slug, str(anno), "conferma_ordine")

        # Pattern v1/v2/FINAL su offerta corrente (per testare dedup soft)
        for suffix in ("_v1", "_v2", "_FINAL"):
            tit = f"Offerta revamp {cliente_nome} {ANNO_CORRENTE}{suffix}"
            body = (
                f"OFFERTA COMMERCIALE\n"
                f"Cliente: {cliente_nome}\n"
                f"Oggetto: Revamp linea produttiva\n"
                f"Importo: EUR 45.000 + IVA\n"
                f"Validità: 30gg dalla data di emissione.\n"
            )
            path = _generate_docx(
                offerte_dir / f"offerta_revamp{suffix}.docx",
                tit,
                body,
                _dt(ANNO_CORRENTE, 4),
            )
            _add(generated, path, cliente_slug, str(ANNO_CORRENTE), f"offerta{suffix}")

        # 1 contratto quadro DOCX
        tit, body = _testo_contratto_quadro(cliente_nome, ANNO_CORRENTE)
        path = _generate_docx(
            cliente_dir / f"contratto_quadro_{ANNO_CORRENTE}.docx",
            tit,
            body,
            _dt(ANNO_CORRENTE, 1),
        )
        _add(generated, path, cliente_slug, str(ANNO_CORRENTE), "contratto")

        # 1 anagrafica xlsx
        path = _generate_xlsx(
            cliente_dir / "contatti.xlsx",
            "Contatti",
            ["Nome", "Ruolo", "Email", "Telefono"],
            [
                ["Marco Bianchi", "Direttore acquisti", f"m.bianchi@{cliente_slug}.it", "335-1234567"],
                ["Laura Verdi", "Ufficio tecnico", f"l.verdi@{cliente_slug}.it", "335-7654321"],
                ["Giulia Rossi", "Amministrazione", f"g.rossi@{cliente_slug}.it", "335-9876543"],
            ],
            _dt(ANNO_CORRENTE, 3),
        )
        _add(generated, path, cliente_slug, str(ANNO_CORRENTE), "anagrafica")


def _add_fornitori_files(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Aggiunge ~30 file distribuiti tra i 4 fornitori."""
    for fornitore_nome, fornitore_slug in FORNITORI:
        fornitore_dir = output_dir / "Fornitori" / fornitore_nome.replace(" ", "_")
        fornitore_dir.mkdir(parents=True, exist_ok=True)

        # 2 listini (anno corrente + anno passato)
        for anno in ANNI_RECENTI[:2]:
            tit, body = _testo_listino(fornitore_nome, anno)
            path = _generate_pdf(
                fornitore_dir / f"listino_{anno}.pdf",
                tit,
                body,
                _dt(anno, 1),
            )
            _add(generated, path, fornitore_slug, str(anno), "listino")

        # 1 manuale tecnico
        tit, body = _testo_manuale("Pompa centrifuga PC-200", fornitore_nome)
        path = _generate_pdf(
            fornitore_dir / "manuale_PC-200.pdf",
            tit,
            body,
            _dt(2024, 5),
        )
        _add(generated, path, fornitore_slug, "2024", "manuale")

        # 2 fatture ricevute
        for i in range(2):
            num = f"{ANNO_CORRENTE}/F{500 + i:03d}"
            tit, body = _testo_fattura(num, fornitore_nome, 3200 + i * 800, ANNO_CORRENTE)
            path = _generate_pdf(
                fornitore_dir / f"fattura_ricevuta_{ANNO_CORRENTE}_{500 + i:03d}.pdf",
                tit,
                body,
                _dt(ANNO_CORRENTE, 5 + i),
            )
            _add(generated, path, fornitore_slug, str(ANNO_CORRENTE), "fattura_ricevuta")

        # 1 contratto fornitura
        tit = f"Contratto fornitura {fornitore_nome}"
        body = (
            f"CONTRATTO QUADRO DI FORNITURA - {ANNO_CORRENTE}\n"
            f"Fornitore: {fornitore_nome}\n"
            f"Durata: 12 mesi rinnovabili.\n"
            f"Condizioni di pagamento: 60gg DF\n"
            f"Penali ritardo: 0,5%/giorno (max 5% importo)\n"
        )
        path = _generate_docx(
            fornitore_dir / "contratto_quadro.docx",
            tit,
            body,
            _dt(ANNO_CORRENTE, 1),
        )
        _add(generated, path, fornitore_slug, str(ANNO_CORRENTE), "contratto_fornitura")


def _add_archivio_files(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Cartella _OLD_NON_USARE/ con 15 file vecchi (3+ anni)."""
    archivio_dir = output_dir / "_OLD_NON_USARE"
    archivio_dir.mkdir(parents=True, exist_ok=True)

    for i, anno in enumerate(ANNI_ARCHIVIO):
        # 5 file per anno
        for j in range(5):
            tit = f"Documento vecchio {anno} #{j + 1}"
            body = f"Documento archiviato dell'anno {anno}. Cliente storico.\nNon piu' attivo dal {anno + 1}."
            path = _generate_pdf(
                archivio_dir / f"vecchio_{anno}_{j + 1:02d}.pdf",
                tit,
                body,
                _dt(anno, 6),
            )
            _add(generated, path, "archivio", str(anno), "vecchio")


def _add_modelli_files(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Cartella Modelli/ con template aziendali."""
    modelli_dir = output_dir / "Modelli"
    modelli_dir.mkdir(parents=True, exist_ok=True)

    templates = [
        ("template_offerta_standard", "Modello Offerta", "Modello standard per offerte commerciali. Sostituire i campi tra parentesi."),
        ("template_lettera_incarico", "Modello Lettera Incarico", "Modello standard per lettere d'incarico professionale."),
        ("template_contratto_breve", "Modello Contratto Breve", "Modello contratto per forniture sotto i 5000 EUR."),
    ]
    for slug, tit, body in templates:
        path = _generate_docx(
            modelli_dir / f"{slug}.docx",
            tit,
            body,
            _dt(2025, 1),
        )
        _add(generated, path, "modelli", "2025", "template")


def _add_files_con_accenti(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """File con caratteri italiani nel nome (stress filesystem unicode)."""
    accenti_dir = output_dir / "Comunicazioni"
    accenti_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("comunicazione_clientÈ.txt", "Comunicazione al clientè. Contiene caratteri unicode italiani."),
        ("perizia_qualità.txt", "Perizia di qualità per il lotto 2026/A. Risultati positivi."),
        ("relazione_attività.txt", "Relazione sintetica delle attività svolte nel Q1 2026."),
    ]
    for fname, content in files:
        path = _generate_txt(accenti_dir / fname, content, _dt(2026, 3))
        _add(generated, path, "comunicazioni", "2026", "comunicazione")


def _add_binari_esclusi(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """File binari che il perimetro deve escludere."""
    backup_dir = output_dir / "Backup_2022"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for i in range(3):
        # File .zip vuoto (per testare exclude extension)
        path = backup_dir / f"backup_2022_Q{i + 1}.zip"
        path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # ZIP vuoto minimal
        _set_mtime(path, _dt(2022, 3 * (i + 1)))
        _add(generated, path, "backup", "2022", "zip")

    # 2 file .dwg vuoti (escluso da filtri esempio)
    cad_dir = output_dir / "Disegni_CAD"
    cad_dir.mkdir(parents=True, exist_ok=True)
    for i in range(2):
        path = cad_dir / f"disegno_{i + 1:03d}.dwg"
        path.write_bytes(b"AC1018" + b"\x00" * 100)  # DWG header fake
        _set_mtime(path, _dt(2024, 6))
        _add(generated, path, "cad", "2024", "dwg")


def _add_email_libere(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Email standalone in Comunicazioni/Email/."""
    email_dir = output_dir / "Comunicazioni" / "Email"
    email_dir.mkdir(parents=True, exist_ok=True)

    emails = [
        (
            "richiesta_offerta_rossi.eml",
            "Richiesta offerta urgente Rossi Srl",
            "Buongiorno, abbiamo bisogno di un'offerta entro fine settimana per il revamp linea produttiva. Cordiali saluti.",
            "marco.bianchi@rossi-srl.it",
        ),
        (
            "reminder_pagamento_neri.eml",
            "Reminder pagamento fattura 2026/17",
            "Gentile cliente, la fattura 2026/17 risulta scaduta. La preghiamo di provvedere al pagamento.",
            "amministrazione@azienda.it",
        ),
        (
            "invito_fiera_meccanica.eml",
            "Invito fiera MECSPE 2026",
            "Vi invitiamo allo stand B17 alla fiera MECSPE 2026 a Bologna, 28-30 marzo.",
            "eventi@mecspe.com",
        ),
    ]
    for fname, subject, body, mittente in emails:
        path = _generate_eml(
            email_dir / fname,
            mittente,
            "info@azienda.it",
            subject,
            body,
            _dt(2026, 3),
        )
        _add(generated, path, "email", "2026", "email")


def _add_duplicati_cross_cartella(output_dir: Path, generated: list[GeneratedFile]) -> None:
    """Genera 5 coppie di file con CONTENUTO IDENTICO in cartelle diverse.

    Stress test per dedup_hash: il pipeline deve riconoscerli come canonici.
    """
    duplicati_dir = output_dir / "_duplicati_test"
    duplicati_dir.mkdir(exist_ok=True)

    for i in range(5):
        content = f"Contenuto duplicato {i}: stesso file in due posti diversi.\n" * 20
        # Versione 1: in _duplicati_test/
        path1 = duplicati_dir / f"file_duplicato_{i + 1}.txt"
        path1.write_text(content, encoding="utf-8")
        _set_mtime(path1, _dt(2025, 6))
        _add(generated, path1, "duplicati", "2025", "duplicato")

        # Versione 2: in Clienti/Rossi_Srl/ con nome diverso
        rossi_dir = output_dir / "Clienti" / "Rossi_Srl"
        rossi_dir.mkdir(parents=True, exist_ok=True)
        path2 = rossi_dir / f"copia_dello_stesso_file_{i + 1}.txt"
        path2.write_text(content, encoding="utf-8")
        _set_mtime(path2, _dt(2025, 7))
        _add(generated, path2, "rossi-srl", "2025", "duplicato_copia")


def build_stress_dataset(output_dir: Path) -> list[GeneratedFile]:
    """Genera il dataset stress test in ``output_dir``.

    Idempotente: cancella la cartella se esiste e rigenera.
    Seed fisso per riproducibilità.
    """
    _setup_random()
    if output_dir.exists():
        logger.info("Cartella esistente: cancello e ricreo (%s)", output_dir)
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    generated: list[GeneratedFile] = []
    _add_clienti_files(output_dir, generated)
    _add_fornitori_files(output_dir, generated)
    _add_archivio_files(output_dir, generated)
    _add_modelli_files(output_dir, generated)
    _add_files_con_accenti(output_dir, generated)
    _add_binari_esclusi(output_dir, generated)
    _add_email_libere(output_dir, generated)
    _add_duplicati_cross_cartella(output_dir, generated)

    logger.info(
        "Dataset stress test generato in %s: %d file totali.",
        output_dir,
        len(generated),
    )
    return generated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera dataset stress test PMI italiana.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_inbox/stress"),
        help="Cartella di output (default: _inbox/stress).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Logging dettagliato.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    generated = build_stress_dataset(args.output)
    # Counters per tipo
    from collections import Counter

    counters = Counter(g.tipo for g in generated)
    print(f"\nDataset stress test generato: {len(generated)} file in {args.output}")
    print("\nDistribuzione per tipo:")
    for tipo, n in sorted(counters.items(), key=lambda x: -x[1]):
        print(f"  {tipo:25s}: {n}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
