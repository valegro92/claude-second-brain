# Cheatsheet Custode — Custodia

**1 pagina A4 da tenere a portata di mano.** Riassunto operativo per il Custode designato, consegnato a fine handover (Atto 3).

Manuale completo: [`docs/05-manuale-custode.md`](../05-manuale-custode.md). Framework di riferimento: [`docs/06-framework-pmi.md`](../06-framework-pmi.md).

---

## Sei il Custode. Cosa significa, in 3 righe

Sei la persona responsabile della wiki aziendale (il **vault**). Spendi **3-5 ore a settimana** per i primi 3 mesi, **2-3 ore/settimana a regime**. Senza di te il vault muore in 6 settimane. Senza il vault, la conoscenza aziendale resta nelle teste e nei Drive caotici.

---

## I 3 rituali — l'unica cosa che non puoi saltare

| Quando | Chi | Dove | Tempo | Cosa fai |
|---|---|---|---|---|
| **Ogni giorno** | Ogni persona del reparto | `Daily/<XX>/` | 2 min + 2 min | "Buongiorno Claude, sono XX" al mattino. "Buonanotte Claude" la sera |
| **Ogni venerdì pomeriggio** | Tu (Custode di reparto) | `reparti/<X>/_proposte-promozione.md` | 30 min | Rivedi proposte accumulate, promuovi a L3/L2/L1, lancia `vault-lint` |
| **Primo venerdì del mese** | Tu + Owner + altri Custodi | `vault/MEMORY.md` + `vault/decisioni/` | 1 ora | Rivedi candidate L1, Owner approva ADR cross-reparto, check salute vault |

---

## Comandi `wiki` più usati

Da terminale, in working directory `vault/`:

```bash
# Apertura sessione (lo fa Claude in automatico, ma puoi forzarlo)
wiki greet GB

# Lancia il rituale settimanale (skill rituale-settimanale-custode)
wiki ritual weekly --reparto commerciale

# Lancia il rituale mensile (skill rituale-mensile-owner — co-pilotato con Owner)
wiki ritual monthly

# Lint del vault (verifica frontmatter, link rotti, file orfani)
wiki lint
# oppure: wiki lint --reparto commerciale per limitare al reparto

# Aggiungere una nuova persona (skill setup-wizard-persona)
wiki person add

# Aggiungere un nuovo oggetto di business (cliente, fornitore, commessa)
wiki object new --tipo cliente --slug acme-spa

# Cercare nel vault (ripiega su grep se serve)
wiki search "rivalutazione prezzi"

# Vedere salute del vault (numero file vivi, MOC mancanti, reparti silenti)
wiki status
```

*Se i comandi `wiki` non sono installati, ripiega sulla skill diretta: `claude code` e poi `Lancia skills/rituale-settimanale-custode/SKILL.md`.*

---

## I 6 layer di memoria (memorizza l'immagine, non i nomi)

```
                     STATICO (cambia mesi)     VIVO (cambia giorni)
                     ────────────────────      ────────────────────
AZIENDA (tutti)      L0 references/            L1 MEMORY.md
REPARTO (team)       L2 procedure/             L3 reparti/<X>/MEMORY.md
OGGETTO (1 cosa)     L4 clienti/<X>/           L5 Daily/<XX>/
```

**Regola della promozione**: una cosa nasce in L5 (idea di un singolo). Se utile al reparto sale a L3 o L2. Se utile a tutta l'azienda sale a L1. Se identità aziendale stabile sale a L0 (raro). **Le promozioni le fai tu nei rituali — non sono automatiche.**

---

## Le 4 regole non-negoziabili

1. **Bozza prima, binario dopo.** Si scrive `.md` con `stato: bozza`, si fa review, poi si esporta il binario finale con naming convenzionale `[cliente]_[tipo]_v[n]_YYYY-MM-DD.[ext]`.
2. **Regola 01-PMI (5 file per oggetto).** Ogni cliente/fornitore/commessa ha: MOC + `CLAUDE.md` + `MEMORY.md` + `tasks.md` + `persone.md`. Sempre 5, sempre stessi nomi.
3. **Verify-or-redo.** Dopo ogni modifica, fai il check che farebbe l'utente finale. Se fallisce, non chiudere: loop fino a OK.
4. **SSOT per oggetto.** Una sola pagina di verità per ogni cliente/fornitore/persona. Mai due posti per la stessa cosa.

---

## Cosa fare quando…

| Situazione | Cosa fai |
|---|---|
| **Un collega ti chiede "dov'è il file di X"** | Aprigli la scheda nel vault. Se non c'è, è un'occasione: aggiungila tu in 5 minuti, lui guarda |
| **Un collega scrive male / non scrive** | Mostragli il manuale persone ([`07-manuale-persone.md`](../07-manuale-persone.md)) — è 1 pagina. Se persiste, parlane all'Owner nel rituale mensile |
| **`vault-lint` segnala 30 errori** | Pulisci uno alla volta, parti dai link rotti. Se sono troppi, segnala a Valentino nel check-up mensile |
| **Una decisione importante è stata presa fuori dal vault** | Apri `vault/decisioni/YYYY-MM-DD_titolo.md`, scrivi come ADR, linka dai MOC coinvolti |
| **Entra un nuovo collega in azienda** | Apri `reparti/<X>/onboarding/<ruolo>.md`. Se non c'è, la prossima persona ti ringrazia se la scrivi tu adesso |
| **Esce un collega dall'azienda** | Verifica che le sue schede vive (clienti, commesse, post-mortem) non siano orfane. Riassegna nel frontmatter `owner` |
| **Hai dubbi su una promozione** | Lasciala come `candidata-L1` nel `_proposte-promozione.md`. Si decide nel rituale mensile con l'Owner |
| **Una cartella `_pending/da-chiarire.md` cresce oltre 10 voci** | Blocco. Schedula 1 ora con te stesso fuori rituale, smaltisci |
| **Devi aggiungere un nuovo reparto** | Non da solo. Riconvoca Valentino (è una sessione di 2-3 ore, costo 2-4k €) |
| **Claude risponde male, dice cose che il vault non dice** | Verifica `CLAUDE.md` del kernel + `CLAUDE.md` dell'oggetto. 9/10 volte è frontmatter sbagliato o `MEMORY.md` non aggiornato |

---

## FAQ rapide

**Quanto tempo perdo davvero alla settimana?**
30 min rituale settimanale + 30-60 min di sparse "aggiungo questa cosa nel vault" durante la settimana. Totale: 1-2 ore/settimana a regime. **Tre volte tanto** nei primi 3 mesi.

**Devo essere io a scrivere tutti i contenuti?**
No. Tu **mantieni il sistema**. I contenuti li scrivono gli Editor e i Contributor del reparto — tu li guidi, promuovi, pulisci. Se ti ritrovi a scrivere tu il 100%, qualcosa non funziona nei ruoli: parlane all'Owner.

**Cosa succede se salto un rituale settimanale?**
Una volta non succede nulla. Due volte di fila: le proposte si accumulano, il rituale dopo dura 1h invece di 30 min. Tre volte: cominci a perdere la sensazione del polso del vault. Quattro volte: stai andando incontro alla morte della wiki, riconvoca Valentino.

**E se cambio azienda / ruolo?**
Il manuale custode è il riferimento per il tuo sostituto. Affiancalo 2-3 settimane sui rituali settimanali, fai un rituale mensile insieme, poi passi le consegne. Se serve, Valentino può fare una sessione di formazione del sostituto (1.500-2.500 €).

**Quando chiamare Valentino?**
- Nei 3 check-up mensili gratuiti post-handover (programmati)
- Se hai un contratto di manutenzione: secondo SLA (Light 48h, Premium con call mensile)
- In emergenza: blocco totale del vault, perdita di dati. Email a `valentino@cassettadegliaitrezzi.it` *(placeholder)*

---

## Link rapidi

- **Manuale completo del Custode** → [`docs/05-manuale-custode.md`](../05-manuale-custode.md)
- **Framework e teoria** → [`docs/06-framework-pmi.md`](../06-framework-pmi.md)
- **Manuale per gli altri colleghi (Editor e Contributor)** → [`docs/07-manuale-persone.md`](../07-manuale-persone.md)
- **Checklist dell'handover (cosa è successo in Atto 3)** → [`docs/04-handover-checklist.md`](../04-handover-checklist.md)
- **Skill da invocare** → `skills/session-lifecycle/SKILL.md`, `skills/rituale-settimanale-custode/SKILL.md`, `skills/rituale-mensile-owner/SKILL.md`, `skills/vault-lint/SKILL.md`

---

*Cheatsheet stampabile fronte/retro A4. Versione 1.0 per delivery Custodia. Sostituisci `XX` con le tue iniziali e `<X>` con il nome del tuo reparto.*
