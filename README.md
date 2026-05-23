# Claude Second Brain — Toolkit Wiki PMI

**Una wiki aziendale costruita per una PMI di 30-50 persone, in 4 settimane, con Valentino al fianco del cliente.**

Non è un'app, non è un SaaS, non è un abbonamento. È un toolkit consulenziale: un repo da clonare sui sistemi del cliente + 3 atti di delivery presidiati + un manuale operativo per il Custode interno.

---

## A chi serve

Una PMI italiana, **30-50 dipendenti**, manifatturiera o servizi B2B, con 5-15 anni di patrimonio documentale sparso tra Drive condivisi, NAS, caselle email, portatili. Riconoscibile da due segnali:

1. **Un dolore quotidiano**: il commerciale risponde citando offerte vecchie, l'amministrazione cerca il contratto firmato e trova tre versioni, ogni nuovo assunto passa 3 settimane a chiedere "dove sta...".
2. **Un IT/Office manager interno** — la persona che già gestisce account, accessi, NAS. È il candidato naturale a diventare **Custode** della wiki.

Se non c'è il Custode, il prodotto non funziona. Se ci sono entrambi i segnali, sì.

---

## Cosa cambia nella giornata di un dipendente

### Prima

Maria (commerciale, MR) il lunedì mattina alle 9. Cerca il contratto Rossi Srl in 3 Drive diversi (uno è quello "vecchio", uno "nuovo definitivo", uno "definitivo_v2"). Trova due versioni datate diversamente, non sa quale sia firmata. Chiede a Mario in chat. Mario le dice di chiedere a Giulia in amministrazione. Giulia non c'è. Maria intanto risponde al cliente con quello che ricorda. **15 minuti persi, risposta approssimativa.**

La sera, una decisione presa in call ("a Rossi anticipiamo la consegna al 15 giugno") resta nella sua testa e in uno scambio WhatsApp. Domani non se la ricorda nessun altro.

### Dopo

Maria apre Cowork sul vault aziendale. Scrive *"Buongiorno Claude, sono MR"*. Claude legge memoria aziendale + memoria reparto Commerciale + suo daily personale. Risponde:

> *Sessione 47 aperta. Hai 3 clienti attivi questa settimana: Rossi Srl (anticipo consegna), Bianchi Forniture (rinnovo annuale), Verdi Costruzioni (offerta nuova commessa). Ieri avevi annotato che oggi vai a chiudere l'offerta Verdi. Procediamo?*

Maria lavora. A sera scrive *"Buonanotte Claude"*. Claude propone: *"Da oggi: salvo la decisione 'a Rossi anticipiamo al 15 giugno' nella memoria del cliente? E la lezione 'Verdi vuole offerte sempre via PEC, mai email' nelle procedure del reparto?"*. Maria risponde `sì, sì`. 60 secondi. Fine.

Il giorno dopo, quando Luca apre il cliente Rossi, quelle decisioni sono lì.

---

## Come funziona

Il vault è una cartella di file `.md` sui sistemi del cliente. Strutturata in 6 layer di memoria (azienda, reparto, oggetto) con 4 ruoli operativi (Owner, Custode, Editor, Contributor) e 3 rituali (giornaliero personale, settimanale di reparto, mensile aziendale).

Claude legge i file giusti al momento giusto. I dipendenti scrivono solo dove possono scrivere. Il Custode tiene pulito. L'Owner approva le promozioni a memoria aziendale.

Nessuna magia. Nessun server intermedio. I dati restano sui sistemi del cliente.

Per la teoria completa: [`docs/06-framework-pmi.md`](docs/06-framework-pmi.md).

---

## Come si compra

Si contatta Valentino. Una prima call di 30 minuti per verificare se sei dentro l'ICP e se hai il Custode disponibile. Se sì, parte la delivery in 3 atti:

| Atto | Quando | Cosa succede |
|---|---|---|
| **1. Kick-off** | Giorno 1, on-site, ½ giornata | Wizard azienda, connessione MCP, perimetro privacy firmato, vault scheletro |
| **2. Scandagliamento** | Settimana 1-2, remoto + call settimanale | Si popola il vault con i contenuti vivi del reparto pilota, batch supervisionati |
| **3. Handover** | Giorno finale, on-site, ½ giornata | Training Custode sui 3 rituali, primo rituale fatto insieme, consegna manuale custode |

**Investimento indicativo**: 8.000-15.000 € setup una tantum, opzionale 800-1.500 €/mese di manutenzione. Da validare in trattativa (vedi [`docs/01-cosa-vendi.md`](docs/01-cosa-vendi.md) per il dettaglio).

**Esclusioni esplicite v1**: connettori a gestionali italiani senza API (TeamSystem, Zucchetti, Danea, Mexal), modalità on-premise per settori regolamentati. Verranno in v1.5 o su quotazione separata.

---

## Documentazione

Sette documenti, indirizzati a chi legge in un dato momento.

### Per Valentino (chi vende e consegna)

| | |
|---|---|
| [**01 — Cosa vendi**](docs/01-cosa-vendi.md) | Playbook commerciale: ICP, pricing, esclusioni, struttura della demo, 4 casi in cui non vendere |
| [**02 — Kick-off checklist**](docs/02-kickoff-checklist.md) | Atto 1, mezza giornata on-site. Test idoneità, wizard, perimetro privacy, MCP, inventario |
| [**03 — Scandagliamento**](docs/03-scandagliamento.md) | Atto 2, 1-2 settimane supervisionate. Workflow batch, errori comuni, costi Claude, privacy |
| [**04 — Handover checklist**](docs/04-handover-checklist.md) | Atto 3, mezza giornata on-site. Training Custode, primo rituale, mail decommissioning, contratto manutenzione |

### Per il cliente (Custode, Owner, dipendenti)

| | |
|---|---|
| [**05 — Manuale custode**](docs/05-manuale-custode.md) | Il manuale operativo del Custode. 6 fasi, 5 categorie, 6 trappole, 3 rituali a regime |
| [**06 — Il framework PMI**](docs/06-framework-pmi.md) | La teoria: 6 layer di memoria, 4 ruoli, 4 regole, 3 livelli di protocollo, 8 pattern di scrittura |
| [**07 — Manuale persone**](docs/07-manuale-persone.md) | 1 pagina per chiunque in azienda. Cosa puoi fare, cosa non devi fare, a chi chiedere |

### Punto d'ingresso al repo

| | |
|---|---|
| [**INIZIA-QUI**](INIZIA-QUI.md) | Per chi ha appena clonato il repo: 3 percorsi di lettura a seconda del ruolo |

---

## Licenza

MIT — [Valentino Grossi](https://lacassettadegliaitrezzi.substack.com)
