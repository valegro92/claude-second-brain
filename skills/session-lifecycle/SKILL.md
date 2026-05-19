---
name: session-lifecycle
description: Gestisce apertura e chiusura sessione. Si attiva con "Buongiorno Claude" / "Buonanotte Claude" (o "Hello Claude", "Good morning", "Iniziamo", "Good night").
---

# session-lifecycle

## Apertura sessione

Trigger: "Buongiorno Claude", "Hello Claude", "Iniziamo", "Good morning Claude"

**Cosa fare:**

1. Leggi `MEMORY.md` (radice del vault)
2. Controlla la data di oggi
3. Crea il daily in `Daily/Journal/YYYY-MM/YYYY-MM-DD.md` se non esiste (usa il template in `Daily/templates/daily-template.md`)
4. Aggiungi una riga nel log del daily: `### Sessione aperta — HH:MM`
5. Rispondi: `Sessione N aperta. [una riga con cosa sai dalla MEMORY.md se c'è qualcosa di rilevante per oggi]. Cosa facciamo?`

**Non fare:**
- Non caricare references/ di default — solo su richiesta
- Non caricare i progetti — solo quando l'utente apre un progetto
- Non chiedere conferma — apri e basta

---

## Durante la sessione

Quando l'utente lavora:
- Ogni azione rilevante → aggiungi una riga nel log del daily con formato `- [azione]`
- Nuovi task → `progetti/[nome]/tasks.md` se c'è un progetto, altrimenti `Daily/Task/hub.md`
- Idee grezze → `Daily/Appunti/sparks.md` (crea il file se non esiste)
- Bozza contenuti → scrivi sempre prima nel vault, aspetta "ok produci" prima di creare binari

---

## Chiusura sessione

Trigger: "Buonanotte Claude", "Good night Claude", "Chiudiamo", "Fine sessione"

**Cosa fare:**

1. Scrivi un riassunto della sessione nel daily (sezione Log sessione)
2. Identifica 0-3 cose che vale la pena sedimentare in MEMORY.md — solo se ci sono decisioni, lezioni o preferenze rilevanti
3. Per ognuna, proponi la formulazione e chiedi conferma: "Vale la pena aggiungere questo in MEMORY.md? → [formulazione proposta]"
4. Scrivi solo le cose approvate dall'utente
5. Rispondi: `Sessione chiusa. [N] entry scritte. A domani.`

**Criteri per proporre una sedimentazione:**
- È una decisione che cambierà come lavori in futuro?
- È una preferenza scoperta che non vuoi rispiegare?
- È una lezione che si generalizza ad altri progetti?

Se no, non proporre. Meglio non scrivere niente che riempire MEMORY.md di rumore.
