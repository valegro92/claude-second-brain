# Claude Second Brain

**Dai a Claude una memoria persistente. Basata su file sul tuo computer, non su magia.**

Claude dimentica tutto a fine sessione. Se ci lavori ogni giorno — come consulente, formatore, freelancer — passi 10-15 minuti a ogni apertura a risbriefingare chi sei, su cosa stai lavorando, che decisioni hai preso.

Questo sistema risolve il problema: scrivi una volta le informazioni chiave in file di testo, Claude le legge ogni mattina.

---

## Prima e dopo

**Senza sistema** — ogni sessione apri Claude e scrivi:
> *"Sono Anna, consulente HR. Sto seguendo Rossi Srl per la selezione di 5 figure tecniche, abbiamo deciso di evitare i test psico-attitudinali, preferiamo colloqui strutturati. Aiutami a preparare la traccia per il colloquio di domani."*

10 minuti di briefing. Ogni volta.

**Con il sistema** — scrivi:
> *Buongiorno Claude*

Claude ha già letto i tuoi file. Risponde:
> *Sessione 47 aperta. Hai 3 progetti attivi: Rossi Srl (selezione), Bianchi (onboarding), Verdi (JD). Ieri avevi annotato che oggi tocca la traccia del colloquio Rossi. Procediamo da lì?*

Niente briefing. Solo lavoro.

---

## Come funziona

La tua conoscenza vive in file `.md` dentro una cartella sul tuo computer. Claude li legge all'apertura della sessione. Ogni sera propone cosa vale la pena ricordare — tu confermi in 60 secondi.

Non è un plugin. Non è un abbonamento. È una cartella di file che controlli tu.

---

## Inizia

```bash
git clone https://github.com/valegro92/claude-second-brain.git
```

Oppure: scarica lo ZIP dal pulsante **Code → Download ZIP** in alto a destra.

Poi apri la cartella in **Cowork** o **Claude Code** e incolla questo prompt:

```
Leggi skills/setup-wizard/SKILL.md e segui le istruzioni per configurare il mio secondo cervello.
```

**Tempo: ~15 minuti.** Funziona con qualsiasi piano Claude, anche gratuito.

---

## Documentazione

| | |
|---|---|
| [**Guida completa**](docs/guida-formazione.md) | Installazione passo-passo + spiegazione del sistema — inizia qui se è la prima volta |
| [**Come funziona il sistema**](docs/framework.md) | I 4 layer di memoria, le 3 regole, il protocollo di sessione |
| [**File `.md` e grafo Obsidian**](docs/guida-markdown-e-grafo.md) | Cos'è un file markdown, come si scrive, come si usa il grafo |
| [**Aggiungere un progetto**](docs/aggiungere-un-progetto.md) | Come strutturare un nuovo cliente, corso o idea |
| [**Installazione step-by-step**](docs/installazione-per-dummies.md) | Per chi non ha mai aperto un Terminal o usato Git |

---

## Licenza

MIT — [Valentino Grossi](https://lacassettadegliaitrezzi.substack.com)
