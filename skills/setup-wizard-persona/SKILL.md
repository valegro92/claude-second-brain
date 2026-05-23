---
name: setup-wizard-persona
description: Onboarding rapido (2 minuti) per ogni nuovo collega che entra nel vault aziendale. Aggiunge la persona in references/persone.md, crea il suo Daily/<XX>/ e configura l'utente attivo nel CLAUDE.md locale. Trigger - "sono nuovo, aggiungimi al vault", "configura il mio Daily", "buongiorno sono <iniziali> sono nuovo", "setup persona".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# setup-wizard-persona — Onboarding personale

Il nuovo collega ha clonato il repo aziendale (o si è collegato al vault condiviso). 2 minuti, 2 domande, e ha il suo Daily attivo. Da quel momento può aprire la sessione con "Buongiorno Claude, sono <XX>".

Vedi `setup-wizard-azienda` per la configurazione iniziale del vault. Vedi `_brief/02-framework-pmi.md` per i 4 ruoli wiki.

---

## Quando si attiva

- Un nuovo collega ha appena ricevuto accesso al vault aziendale.
- Trigger tipici: "sono nuovo, aggiungimi al vault", "configura il mio Daily", "buongiorno sono LV sono nuovo", "non sono ancora in `persone.md`".

Se l'utente si dichiara come una persona già presente in `references/persone.md` → reindirizza a `session-lifecycle` (apertura sessione normale).

---

## Pre-flight

1. Verifica che `vault/references/persone.md` esista e sia compilato. Se no: "Il vault aziendale non risulta ancora inizializzato. Avvisa il Custode di lanciare `setup-wizard-azienda` prima".
2. Leggi `vault/references/persone.md` per conoscere le iniziali già in uso e i reparti dichiarati.
3. Presentati:
   > Ti aggiungo al vault in 2 minuti. Due domande, niente di più. Pronti?

Aspetta conferma.

---

## Le 2 domande

### Domanda 1 — Identità e ruolo

> Iniziali (2 lettere maiuscole), nome e cognome, reparto, ruolo wiki. I ruoli sono 4: Owner (direzione), Custode (responsabile vault del reparto), Editor (senior che scrive e revisiona), Contributor (default — scrivi bozze, leggi tutto). Se non sai cosa scegliere: Contributor.

Ascolta: 4 dati.

Validazione:
- Iniziali univoche: confronta con la tabella in `persone.md`. Se duplicate, proponi alternativa (terza lettera del cognome o sigla diversa).
- Reparto: deve esistere come cartella in `vault/reparti/`. Se non esiste, segnala: "Il reparto <X> non risulta. Verifica con il Custode aziendale, oppure scegli tra: <lista reparti esistenti>".
- Ruolo: deve essere uno dei 4. Default Contributor se vago.

### Domanda 2 — Email

> Email aziendale.

Ascolta: una riga. Validazione minima: contiene `@`.

---

## Riepilogo e conferma

> Riepilogo: <XX> — <Nome Cognome>, reparto <Reparto>, ruolo <Ruolo>, email <email>. Procedo?

Aspetta conferma.

---

## Cosa scrivere

### 1. Aggiungi riga in `vault/references/persone.md`

Apri il file, aggiungi una riga in fondo alla tabella:

```
| <XX> | <Nome Cognome> | <Reparto> | <Ruolo> | <email> |
```

Aggiorna anche `ultima-revisione: <oggi>` nel frontmatter.

### 2. Crea `vault/Daily/<XX>/`

Struttura:

```
vault/Daily/<XX>/
├── README.md
└── <YYYY-MM>/         # cartella mese corrente
```

`vault/Daily/<XX>/README.md`:

```markdown
---
tipo: daily-root
owner: <XX>
editor: [<XX>]
visibilita: privato
stato: vivo
---

# Daily di <Nome Cognome> (<XX>)

Reparto: <Reparto>. Ruolo: <Ruolo>.

Questa cartella contiene i tuoi journal giornalieri. Un file per giorno, organizzati per mese.

I file si creano da soli ogni volta che apri la sessione con "Buongiorno Claude" (vedi skill `session-lifecycle`).

Le promozioni proposte a chiusura sessione finiscono in `vault/reparti/<reparto>/_proposte-promozione.md` — non in questo Daily.
```

### 3. Configura "utente attivo" nel `vault/CLAUDE.md` locale

Cerca nel `vault/CLAUDE.md` il blocco `[CONFIGURA QUI]` (parte aziendale) e aggiungi sotto, in una sotto-sezione `[UTENTE LOCALE]`, la riga:

```
utente attivo: <XX>
```

Se la sotto-sezione `[UTENTE LOCALE]` non esiste, creala in coda al blocco `[CONFIGURA QUI]`. Se esiste e contiene già un altro utente, chiedi: "Risulta già configurato come '<YY>'. Sovrascrivo? (capita se stessa macchina usata da più persone — se è il tuo caso, conferma)".

Nota: questo file è in `vault/` che è condiviso. Il blocco `[UTENTE LOCALE]` viene letto dalla sessione locale ma non deve essere committato sul repo condiviso. Avvisa: "Il blocco `[UTENTE LOCALE]` è tuo, locale — se il vault è in git, aggiungi `[UTENTE LOCALE]` al `.gitignore` o usa una copia locale del CLAUDE.md".

---

## Chiusura

> Fatto. Ora sei <XX> nel vault.
>
> Per aprire la prima sessione: scrivi `Buongiorno Claude` (o `Buongiorno Claude, sono <XX>` se la macchina è condivisa).
> Per chiuderla: `Buonanotte Claude`.
>
> Le promozioni che proporrai a fine giornata finiscono nel `_proposte-promozione.md` del tuo reparto, dove il Custode le rivede settimanalmente.

---

## Regole di comportamento

- 2 domande, non di più. Se l'utente vuole raccontare altro, prendi nota mentale e procedi.
- Iniziali univoche: validate sempre.
- Default Contributor in caso di dubbio sul ruolo.
- Non toccare il vault aziendale oltre la riga in `persone.md` e la cartella `Daily/<XX>/`.
- Niente sovrascritture senza conferma esplicita.
