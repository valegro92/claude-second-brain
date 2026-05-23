---
name: setup-wizard-azienda
description: Wizard di configurazione iniziale del vault aziendale (PMI). Lanciato UNA volta sola dal Custode in Atto 1 della delivery (kick-off on-site). Compila i file di identità e organigramma, crea lo scheletro reparti. Trigger - "configura il vault aziendale", "setup azienda", "iniziamo l'installazione", "setup wizard azienda".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# setup-wizard-azienda — Configurazione iniziale del vault aziendale

Wizard che il Custode lancia una sola volta in fase di kick-off. Obiettivo: in 20-30 minuti il vault ha identità, organigramma, persone chiave e scheletro reparti. Non sovrascrive niente di già compilato.

Vedi `docs/06-framework-pmi.md` per la teoria dei 6 layer, dei 4 ruoli e della Regola 01-PMI.

---

## Quando si attiva

- Atto 1 della delivery (kick-off on-site), Custode davanti al laptop con Owner accanto.
- Trigger tipici: "configura il vault aziendale", "setup azienda", "iniziamo l'installazione", "siamo al kick-off".

Se l'utente cerca di configurare il proprio Daily personale → reindirizza a `setup-wizard-persona`.

---

## Pre-flight

1. Verifica che `vault/CLAUDE.md` esista e contenga il blocco `[CONFIGURA QUI]` non compilato. Se è già compilato con un nome azienda reale, chiedi conferma prima di procedere: "Risulta già configurato come '<nome>'. Vuoi rifare il setup da zero (sovrascrivo) o usciamo?".
2. Verifica esistenza di `vault/references/` e `vault/reparti/_esempio/`. Se manca lo scheletro, segnala: "Il vault non sembra inizializzato. Fai clone dal template e riavvia".
3. Presentati:
   > Sono il wizard di setup aziendale. Ti faccio 6 blocchi di domande, ci mettiamo 20-30 minuti. Compilo identità, organigramma, persone, brand voice, sorgenti dati esistenti e perimetro privacy. Pronti?

Aspetta conferma. Non partire con le domande prima.

---

## Le 6 domande

Una alla volta. Tono conversazionale, non da form. Aspetta la risposta prima di passare alla successiva. Mai inventare per riempire.

### Domanda 1 — Identità aziendale

> Cominciamo dalle basi. Nome azienda, settore, numero approssimativo di dipendenti, sede principale.

Ascolta: nome legale + nome d'uso, settore (manifattura / servizi / commercio / ecc.), headcount, città.

### Domanda 2 — Reparti

> Quali sono i reparti principali? Cita quelli che hanno almeno una persona dedicata — es. commerciale, amministrazione, produzione, IT, marketing. Non serve gerarchia, solo la lista.

Ascolta: lista 3-7 reparti. Se ne dichiarano meno di 3 chiedi: "Davvero solo questi? Anche reparti molto piccoli (1 persona) contano se hanno responsabilità distinta".

### Domanda 3 — Persone chiave

> Ora le persone chiave. Per ognuna mi serve: iniziali (2 lettere maiuscole), nome e cognome, reparto, ruolo wiki, email. I ruoli wiki sono 4: Owner (1 sola persona, direzione), Custode (1 per reparto, garantisce qualità del vault), Editor (senior che scrive e revisiona), Contributor (tutti gli altri). Iniziamo da chi è Owner.

Ascolta: raccogli almeno Owner + 1 Custode per reparto dichiarato in D2. Se l'utente dà meno di 5 persone in un'azienda da 30+, chiedi: "Ci sono altri Editor/Contributor da censire ora, o li aggiungiamo dopo via `setup-wizard-persona`?".

Validazione iniziali: devono essere uniche, 2 caratteri, maiuscole. Se duplicato, proponi alternativa (terza lettera del cognome).

### Domanda 4 — Brand voice e glossario

> Brand voice in 1-2 righe: come parlate ai clienti? (formale / colloquiale / tecnico / commerciale spinto / consulenziale). Poi 3-5 termini interni che un nuovo assunto deve imparare il primo giorno (sigle, prodotti, processi interni).

Ascolta: 1-2 righe di voice + 3-5 voci di glossario (termine + definizione 1 riga).

### Domanda 5 — Sorgenti dati esistenti

> Dove vivono oggi i file aziendali? Google Drive, Microsoft 365 / OneDrive / SharePoint, email (Gmail / Outlook), NAS locale, server. Non collego niente adesso — annoto solo per la fase di scandagliamento (Step 2 della delivery).

Ascolta: lista 1-5 sorgenti. Per ognuna nota indirizzo/dominio se dato (es. "Google Drive workspace su dominio @azienda.it").

### Domanda 6 — Perimetro privacy

> Ultima domanda. Cosa NON deve mai entrare nel vault? Cartelle riservate (HR, buste paga), dati personali sensibili, clienti sotto NDA, robe che restano solo in mani dell'Owner.

Ascolta: 1-5 perimetri di esclusione. Anche un singolo "buste paga e contratti dei dipendenti" è sufficiente, ma se l'utente dice "niente, tutto pubblico" chiedi: "Anche dati personali dei dipendenti? Cartelle HR? Pensaci un attimo prima di rispondere".

---

## Riepilogo e conferma

Prima di scrivere, riepilogo in 6-8 righe:

> Riepilogo: <azienda>, <settore>, <N> dipendenti, sede <città>. Reparti: <lista>. Owner: <iniziali nome>. Custodi: <iniziali per reparto>. Brand voice: <una riga>. Glossario: <N termini>. Sorgenti dati: <lista>. Esclusioni privacy: <lista>. Procedo a scrivere i file?

Aspetta "ok / procedi". Se l'utente corregge, aggiorna e ripeti il riepilogo.

---

## File da scrivere

Tutti i path sono relativi alla radice del repo.

### `vault/CLAUDE.md` — blocco `[CONFIGURA QUI]`

Trova e sostituisci il blocco `[CONFIGURA QUI]` (lascia intatto il resto del file). Compila con:

```
AZIENDA:    <nome d'uso>
SETTORE:    <settore>
DIPENDENTI: <N>
SEDE:       <città>
OWNER:      <iniziali> (<nome cognome>)
CUSTODI:    <iniziali>: <reparto>, <iniziali>: <reparto>, ...
REPARTI:    <lista separata da virgola>
```

Non toccare le sezioni "Architettura della memoria", "Regole non-negoziabili", "Session Lifecycle", "Filing Rule" — sono framework, non configurazione.

### `vault/references/chi-siamo.md`

```markdown
---
tipo: identita
owner: <iniziali-owner>
editor: [<iniziali-owner>, <iniziali-custodi>]
visibilita: azienda
stato: vivo
ultima-revisione: <oggi>
---

# Chi siamo

<nome azienda>, <settore>, ~<N> persone, sede <città>.

## Come ci raccontiamo

<1-2 righe di brand voice dalla D4>

## Cosa facciamo

<da definire — l'Owner completerà dopo il kick-off>
```

### `vault/references/organigramma.md`

```markdown
---
tipo: organigramma
owner: <iniziali-owner>
editor: [<iniziali-owner>]
visibilita: azienda
stato: vivo
ultima-revisione: <oggi>
---

# Organigramma

## Reparti

<per ogni reparto dichiarato in D2:>
### <Reparto>
- Custode: <iniziali nome>
- Editor: <iniziali, se censiti in D3>
- Contributor: <iniziali, se censiti in D3>

## Direzione

- Owner: <iniziali nome>
```

### `vault/references/persone.md`

```markdown
---
tipo: anagrafica-interna
owner: <iniziali-owner>
editor: [<iniziali-owner>, <iniziali-custodi>]
visibilita: azienda
stato: vivo
ultima-revisione: <oggi>
---

# Persone

Anagrafica interna. Le iniziali sono univoche e sono l'identificatore usato nei frontmatter `owner:` e `editor:` di tutto il vault.

| Iniziali | Nome | Reparto | Ruolo wiki | Email |
|----------|------|---------|------------|-------|
| <XX>     | <Nome Cognome> | <Reparto> | <Owner/Custode/Editor/Contributor> | <email> |
| ...      | ... | ... | ... | ... |

Nuove persone si aggiungono con la skill `setup-wizard-persona`.
```

### `vault/references/glossario.md`

```markdown
---
tipo: glossario
owner: <iniziali-owner>
editor: [<iniziali-owner>, <iniziali-custodi>]
visibilita: azienda
stato: vivo
ultima-revisione: <oggi>
---

# Glossario

| Termine | Significato |
|---------|-------------|
| <termine 1> | <definizione 1 riga> |
| ...     | ... |

Si arricchisce ogni volta che entra un nuovo termine che un nuovo assunto deve imparare.
```

### `vault/references/brand-voice.md`

```markdown
---
tipo: brand-voice
owner: <iniziali-owner>
editor: [<iniziali-owner>]
visibilita: azienda
stato: vivo
ultima-revisione: <oggi>
---

# Brand voice

<1-2 righe dalla D4, in prima persona plurale: "Parliamo ai clienti come...">

## Esempi si

<da definire — esempi reali da inserire dopo il kick-off>

## Esempi no

<da definire>
```

### Scheletro reparti

Per ogni reparto dichiarato in D2:

1. Clona `vault/reparti/_esempio/` in `vault/reparti/<slug-reparto>/` (slug = nome reparto in kebab-case minuscolo, es. "commerciale", "amministrazione").
2. Rinomina il MOC `_esempio.md` in `<slug-reparto>.md`.
3. Compila il frontmatter: `owner: <iniziali-custode>`, `editor: [<iniziali-custode>, <iniziali-editor-del-reparto>]`, `visibilita: reparto`.
4. Compila la prima riga del MOC: "# Reparto <Nome>\n\nCustode: <iniziali nome>. Persone: <lista iniziali>."
5. Lascia `MEMORY.md`, `procedure/sop-_esempio.md`, `_proposte-promozione.md` come template (saranno popolati nell'uso quotidiano).

### Note privacy e sorgenti

In `vault/MEMORY.md` aggiungi due entry datate:

```markdown
## <YYYY-MM-DD> — Sorgenti dati esistenti (pre-scandagliamento)
<lista da D5>. Da connettere in Atto 2 della delivery (Step 2).

## <YYYY-MM-DD> — Perimetro privacy
NON entra nel vault: <lista da D6>.
```

---

## Chiusura

Dopo aver scritto i file:

> Setup azienda completato. Ho scritto:
> - `vault/CLAUDE.md` (blocco configurazione)
> - `vault/references/`: chi-siamo, organigramma, persone, glossario, brand-voice
> - `vault/reparti/<N>` cartelle reparto inizializzate
> - `vault/MEMORY.md`: 2 entry su sorgenti dati e privacy
>
> Prossimi passi:
> 1. Ogni collega lancia `setup-wizard-persona` per essere aggiunto e avere il suo Daily/<XX>/
> 2. In Atto 2 connettiamo le sorgenti (Step 2 della delivery)
> 3. Settimanalmente il Custode fa `rituale-settimanale-custode` (30 min)
> 4. Mensilmente Owner + Custodi fanno `rituale-mensile-owner` (1h)
>
> Da adesso ognuno puo aprire la sessione con "Buongiorno Claude, sono <XX>".

---

## Regole di comportamento

- Mai inventare: se un dato non c'e, scrivi "da definire". Niente placeholder generici.
- Mai sovrascrivere senza chiedere: se un file ha gia contenuto reale, chiedi conferma prima.
- Iniziali univoche: validate sempre. Duplicato = blocco con proposta alternativa.
- Tono: caldo ma diretto. Niente preamboli a ogni domanda.
- Una domanda alla volta: niente form multi-campo.
- Lingua: italiano per i contenuti, anche se l'utente scrive in inglese.
