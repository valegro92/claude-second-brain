# 07 — Manuale persone

Per chiunque in azienda usa la wiki ma non la gestisce. 1 pagina, 5 minuti di lettura.

---

## Cosa è la wiki

Una cartella di file di testo (`.md`) sui sistemi aziendali. Contiene le decisioni, le procedure, le schede dei clienti e dei fornitori che ti servono per lavorare. Claude la legge per te.

**Non è un'altra app**. È una struttura di file che apri dal tuo computer (via Cowork o Claude Code). Lavori con Claude, lui legge la wiki per darti contesto e per scrivere bozze.

---

## Cosa devi fare ogni giorno

### Al mattino, prima di iniziare

Apri Claude (Cowork o Claude Code) sul vault aziendale e scrivi:

```
Buongiorno Claude, sono [le tue iniziali]
```

Es: *"Buongiorno Claude, sono LV"* se sei Luca Verdi.

Claude legge la memoria aziendale, la memoria del tuo reparto e il tuo daily personale di ieri. Ti risponde con un breve orientamento. Da lì parti.

### Durante la giornata

Lavora normalmente. Se vuoi scrivere una nota su un cliente, dirlo a Claude:

> *"Aggiungi nelle note del cliente Rossi Srl che oggi abbiamo deciso di anticipare la consegna al 15 giugno."*

Claude propone una bozza, tu approvi, lui scrive.

### Alla sera, prima di chiudere

Scrivi:

```
Buonanotte Claude
```

Claude riassume cosa hai fatto oggi nel tuo daily. Ti propone 0-3 cose che vale la pena ricordare. Tu rispondi `sì`, `no`, o `correggi`. 60 secondi. Fine.

---

## Cosa puoi fare

| Cosa | Come |
|---|---|
| **Scrivere nel tuo daily** | Automatico — Claude scrive in `Daily/<tue-iniziali>/`. È **privato**, solo tu lo vedi |
| **Aggiungere note a un cliente/fornitore/commessa** | Chiedi a Claude. Lui propone bozza, tu approvi |
| **Cercare un'informazione** | "Claude, dove trovo il contratto firmato di Bianchi Forniture?" → ti risponde con il link |
| **Proporre una promozione** ("questa cosa vale per tutto il reparto") | Glielo dici a Buonanotte. Claude la mette in lista. Il Custode di reparto la rivede venerdì |

---

## Cosa NON devi fare

- **NON modificare le procedure del reparto** (file in `reparti/<X>/procedure/`) senza chiedere al Custode di reparto
- **NON modificare la memoria aziendale** (`MEMORY.md` alla radice del vault) — è dell'Owner
- **NON modificare i file in `references/`** (chi siamo, organigramma, persone, brand voice) — sono del Custode capo
- **NON cancellare file**: se pensi che un file vada eliminato, scrivi al Custode di reparto

Claude conosce queste regole. Se provi a fare una di queste cose, ti ferma e ti dice "questo lo fa il Custode, vuoi che gli scriva una nota?"

---

## A chi chiedere in caso di dubbio

Hai un **Custode di reparto** — è una persona del tuo stesso reparto (Editor senior, capo-area, sales ops, responsabile amministrativo a seconda dei casi). Per saperlo, apri `vault/references/persone.md` e cerca chi ha `Ruolo wiki: Custode` accanto al tuo reparto.

Per cose tecniche (account, accessi, errori di Claude, file che non si aprono): scrivi al **Custode capo** — di solito è l'IT/Office manager dell'azienda.

Per cose strategiche o cross-reparto: passa per il tuo responsabile diretto. Lui poi parlerà con l'Owner se serve.

---

## Privacy

- Il tuo daily (`Daily/<tue-iniziali>/`) è **privato**. Solo tu lo vedi e ci scrivi. Nemmeno il Custode lo apre senza il tuo consenso.
- Le note che scrivi su clienti/fornitori sono **visibili al tuo reparto**. Sono lavoro del reparto, non tue personali.
- Se hai dubbi su cosa è privato e cosa no, **chiedi a Claude** ("Claude, se scrivo questa cosa qui, chi la vede?"). Lui ti risponde guardando il frontmatter del file.

---

## Se vuoi saperne di più

- [`05-manuale-custode.md`](05-manuale-custode.md) — il manuale del Custode. Lo leggi se vuoi capire la governance complessiva o se ti chiedono di diventare Custode di reparto.
- [`06-framework-pmi.md`](06-framework-pmi.md) — la teoria che sta dietro al sistema. Lettura interessante ma non necessaria per usarlo.

Per tutto il resto: **scrivi a Claude o al Custode di reparto.**
