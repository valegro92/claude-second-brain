# Brief — Cost model & Risk/Legal audit (Step 1)

Documento di supporto alle decisioni commerciali e legali per la v1 del toolkit consulenziale. Stime ragionate, non garanzie. Tutti i numeri vanno verificati sul primo cliente reale e ricalibrati a partire dal 3° delivery.

Convenzioni:
- Tariffa di riferimento Valentino: 80 €/h (consulenza senior italiana, in linea con freelance tech 2025-2026). Sostituire con la tariffa reale.
- Cliente di riferimento: PMI 35-40 persone, ~500 GB distribuiti su 4-5 sorgenti, ~5.000 file rilevanti dopo filtro perimetro.
- Periodo di delivery: 3-4 settimane dal kick-off all'handover.
- Valuta: euro, IVA esclusa.

---

## PARTE A — Cost model & pricing

### A.1 Cost model lato Valentino (per cliente)

#### A.1.1 Ore Valentino dirette

| Voce | Ore | Note |
|---|---|---|
| Pre-vendita (call commerciale, sopralluogo doc, preventivo) | 4-6 | Non recuperabili se il deal salta. Considerare 50% rate di conversione |
| Atto 1 — Kick-off on-site (½ giornata) | 4 | On-site, wizard azienda, connettori MCP, scoping perimetro privacy |
| Viaggio Atto 1 (a/r) | 2-6 | Dipende dalla distanza. Assumi media 4h per cliente lombardo/veneto, fino a 8h per cliente lontano |
| Atto 2 — Setup ambiente post kick-off | 4-6 | Configurazione skill custom per il cliente, test connettori, primo dry-run |
| Atto 2 — Supervisione scandagliamento (10 gg lavorativi) | 15-25 | Approvazione batch da 50 bozze. Stima: 4-8 batch/giorno × 5-10 min/batch × 10 gg. Media: 2h/giorno |
| Atto 2 — Call settimanale col Custode (2 call) | 2 | 30 min × 2, sincronia su criticità |
| Atto 2 — Risoluzione blocchi (imprevisti) | 3-8 | Buffer realistico: file corrotti, permessi mancanti, file fuori perimetro |
| Atto 3 — Handover on-site (½ giornata) | 4 | Training Custode, primo rituale settimanale, mail decommissioning |
| Viaggio Atto 3 (a/r) | 2-6 | Come Atto 1 |
| Post-handover — 3 check-up mensili (1h ciascuno) | 3 | Remoto, verifica adozione, micro-fix |
| Amministrazione, fatturazione, redazione contratto | 2-3 | Per cliente |
| **Totale ore Valentino** | **45-73** | **Stima centrale: 55-60 ore** |

Costo Valentino (a 80 €/h): **3.600 - 5.840 €**, centrale ~**4.500 €**.

#### A.1.2 Ore Custode lato cliente (informativa, non costo Valentino)

Importante per vendere: il cliente paga anche il tempo del proprio Custode. Se non lo dici, è la sorpresa che ammazza il deal al secondo mese.

| Voce | Ore Custode | Quando |
|---|---|---|
| Kick-off (presenza on-site) | 4 | Atto 1 |
| Raccolta credenziali, accessi, perimetro | 2-4 | Prima settimana |
| Disponibilità per call/Slack durante scandagliamento | 8-12 | 2 settimane × ~1h/giorno per domande |
| Handover (presenza on-site + assimilazione) | 4-6 | Atto 3 |
| Rituale settimanale post-handover (Fase di rodaggio, primi 3 mesi) | 24-36 | 2-3h/sett × 12 sett |
| **Totale ore Custode primi 3 mesi** | **42-62** | **Da dichiarare in pre-vendita** |

Costo opportunità per il cliente: se il Custode costa 35 €/h fully loaded, sono **1.470-2.170 €** di tempo interno. Lo cito in trattativa per spiegare perché il setup vale: "il tuo tempo interno è 2k, il mio servizio è 10k, ti consegno un asset che il tuo Custode da solo non avrebbe mai costruito".

#### A.1.3 Costo Claude (token)

Assunzioni:
- Scandagliamento + categorizzazione: ~5.000 file rilevanti, ~2-5 KB di testo estratto per file in media (post-OCR/parsing) = 10-25 MB di input testuale = ~3-8 milioni di token input.
- Bozzatura schede vault: ~300-500 schede generate (clienti, fornitori, commesse, SOP, MOC) × ~2k token output ciascuna = ~600k-1M token output.
- Categorizzazione + decisioni di routing: chiamate corte ad alta frequenza, ~500k token input + 200k token output.
- Iterazioni e batch ri-approvati: aggiungi +30% di overhead.

Prezzi di riferimento (verificare prima di ogni preventivo, cambiano):
- **Claude Sonnet 4.6**: ordine di grandezza ~3 $/M token input, ~15 $/M token output (con prompt caching che taglia significativamente l'input ripetuto).
- **Claude Opus 4.7**: ordine di grandezza ~15 $/M token input, ~75 $/M token output.

> Nota: i prezzi esatti vanno verificati su `anthropic.com/pricing` al momento del preventivo. I numeri sopra sono ordine di grandezza per dimensionare il modello economico, non per fatturare.

Stima per cliente medio (uso misto: Sonnet per il 90% dei batch, Opus per i casi complessi tipo estrazione contratti articolati o cruscotti decisionali):

| Scenario | Token input | Token output | Costo USD | Costo EUR (~0.92) |
|---|---|---|---|---|
| Basso (cliente facile, Sonnet only, caching efficace) | 4M | 600k | ~25 $ | ~23 € |
| Atteso (mix Sonnet/Opus 90/10) | 6M | 1M | ~70-100 $ | ~65-90 € |
| Alto (cliente difficile, molti retry, Opus pesante) | 10M | 1.5M | ~200-300 $ | ~185-275 € |

**Stima centrale: 80-120 € di token per cliente**. È trascurabile rispetto alle ore Valentino, ma va monitorato: se la v1 esplode per qualche pattern (es. estrazione completa di mail di 15 anni), può triplicare.

> Assunzione critica: il toolkit usa caching aggressivo del prompt di sistema (CLAUDE.md del vault, frontmatter standard) e batching. Senza queste due ottimizzazioni, i token raddoppiano facilmente.

#### A.1.4 Costi infrastruttura una tantum + ricorrenti

| Voce | Costo | Tipo |
|---|---|---|
| Subscription Anthropic dev (Claude Code Pro/Max o credito API) | 100-200 €/mese | Ricorrente |
| MCP server custom (Drive, M365, Gmail/Outlook, NAS) | 0-50 €/mese | Open source + qualche hosting |
| Storage temporaneo cifrato (worktree delivery in cloud) | 10-30 €/mese | Ricorrente |
| Account dev M365 / Google Workspace per testing connettori | 15-30 €/mese | Ricorrente |
| Notarile / template contratto + DPA + revisione legale iniziale | 800-2.000 € | Una tantum |
| RC professionale (consulenza IT/data) | 400-800 €/anno | Annuo |
| Commercialista, partita IVA, gestione | 1.200-2.500 €/anno | Annuo |

**Fissi annui**: ~3.500-6.500 €. Spalmati su 10 clienti/anno = 350-650 €/cliente.

#### A.1.5 Costi vivi della delivery

| Voce | Costo per cliente |
|---|---|
| Trasferta a/r (treno + eventuale notte) | 100-400 € |
| Pranzo on-site (auto-pagato) | 30-50 € |
| Materiale stampato (manuale Custode in copia fisica, eventuale gadget) | 30-80 € |
| Subtotale | **160-530 €** (centrale ~300 €) |

#### A.1.6 Sintesi costo per cliente

| Voce | Centrale (€) |
|---|---|
| Ore Valentino (55h × 80€) | 4.400 |
| Costo Claude token | 100 |
| Quota fissi annui (1/10) | 500 |
| Costi vivi delivery | 300 |
| **Totale costo Valentino per cliente** | **~5.300 €** |
| Range plausibile | 4.000 - 7.500 € |

Questo è il numero su cui costruire il pricing.

#### A.1.7 Note sulle stime — cosa è solido e cosa va verificato

**Ragionevolmente solido** (basato su benchmark consulenza italiana freelance):
- Tariffa oraria 80 €/h (range freelance senior 70-100 €/h).
- Quota fissi annui ~5k €/anno per partita IVA singola con commercialista, RC, formazione.
- Ore di trasferta e logistica.

**Da validare sul 1° cliente reale** (stime educate ma possono essere sbagliate del 30-50%):
- Le 15-25h di supervisione dello scandagliamento — dipende molto dall'efficacia del batch-approval e dalla qualità dei dati del cliente. Potrebbero essere 10h (cliente facile, batch grandi) o 35h (cliente difficile, molti rework).
- I 80-120 € di token. Se il caching del prompt funziona bene, può scendere a 30-50 €. Se i file richiedono molti retry su Opus, può salire a 300 €.
- Le 3 ore di check-up post-handover — alcuni clienti chiamano 10 volte in un mese, altri zero.

**Da rinegoziare a partire dal 3° cliente** quando hai dati veri.

---

### A.2 Pricing model

Per ognuno: euro, pro/contro, target margine, come si presenta in trattativa.

Premessa: per un servizio consulenziale italiano B2B che produce un asset duraturo (la wiki resta del cliente), il margine sano è 60-70% sul costo Valentino. Sotto il 50% non vale la pena rispetto a tariffa a giornata pura. Sopra l'80% serve un brand già fatto.

#### Modello 1 — Flat setup una-tantum (8.500 - 14.000 €)

**Range proposto**: 8.500 € (entry) — 11.000 € (standard) — 14.000 € (premium, cliente complesso).

**Margine**: a 11.000 € su costo 5.300 = **52% margine**, ovvero ~5.700 € di utile lordo per cliente. Su 10 clienti/anno = 57k € margine. Da qui togli tasse personali, fissi, ed eventuali periodi senza vendita.

**Pro**:
- Semplice da vendere ("una cifra, sai cosa spendi").
- Semplice da contrattualizzare.
- Nessun lock-in percepito dal cliente.

**Contro**:
- Margine modesto per un servizio così personalizzato.
- Una volta consegnato sei fuori, perdi visibilità su adozione.
- Se il cliente non mantiene il Custode, la wiki muore in 6 mesi e il passaparola si avvelena.

**Quando usarlo**: primi 3-5 clienti per costruire portfolio rapidamente. Cliente che esplicita "non vogliamo manutenzione, ce la gestiamo".

**In trattativa**: "11.000 € chiavi in mano, 3 settimane, output garantito (vault + manuale + Custode formato). Niente ricorrenti. Dopo 3 check-up mensili gratuiti, sei autonomo."

#### Modello 2 — Setup + manutenzione opzionale mensile (8.000 € + 700-1.500 €/mese)

**Setup**: 8.000 € (più aggressivo del Modello 1, perché vuoi entrare in manutenzione).
**Manutenzione mensile**: 700 € base (1.5h/mese, check rituale Custode, micro-fix), 1.500 € premium (4h/mese, evolutive + onboarding nuovi colleghi + tuning skill).

**Margine**:
- Setup a 8.000 € su 5.300 € costo = **34% margine setup** (≈2.700 €). Bassissimo.
- Manutenzione: a 700 €/mese × 1.5h consumate = ~580 €/mese di costo Valentino = **17% margine**. Trascurabile.
- Manutenzione premium: 1.500 € / (4h × 80€ = 320€) = **78% margine**. Qui inizia a tirare.

Il modello funziona economicamente solo se almeno il 50% dei clienti sale a manutenzione e di questi una metà va in premium. Da modellare con scenari.

**Pro**:
- Ricavi ricorrenti = pianificabilità.
- Resti dentro l'azienda, raccogli use case per evolvere il prodotto.
- Differenzia da "consulente che spara e sparisce".

**Contro**:
- Più complesso da chiudere (cliente teme lock-in).
- Devi servire davvero, non puoi vendere e ignorare.
- Se hai 20 clienti in manutenzione, hai un job, non un business scalabile.

**Quando usarlo**: cliente che lo chiede ("vorremmo sapere che ci sei se succede qualcosa"). PMI con turnover medio-alto dove devi onboardare nuove persone spesso. Settori regolamentati che vogliono SLA.

**In trattativa**: "8.000 € setup + scegli post-handover: niente (sei autonomo, ti faccio i 3 check-up), Light a 700/mese (ti garantisco un'ora e mezza al mese), Premium a 1.500/mese (sono il tuo team wiki esterno)."

#### Modello 3 — A consumo (€/persona o €/GB)

**Esempio €/persona**: 280 €/persona × N dipendenti = per PMI 35 persone, 9.800 €. Per 50 persone, 14.000 €.
**Esempio €/GB**: 25 €/GB scandagliato × 500 GB = 12.500 €. Difficile da prevedere prima del kick-off.

**Margine**: dipende dalla taglia. Convergente al Modello 1 nei casi medi.

**Pro**:
- Sembra "equo" al cliente piccolo (paga meno).
- Posizionamento meno arbitrario in negoziazione.

**Contro**:
- €/persona penalizza PMI con dipendenti che usano poco gli strumenti digitali (manifatturiero: 40 operai + 5 ufficio).
- €/GB è una pessima proxy: 100 GB di video sono triviali, 10 GB di Excel articolati richiedono settimane.
- Difficile preventivare prima di vedere i dati = pre-vendita più lenta.

**Quando usarlo**: mai come modello principale. Eventualmente come "ancora" in trattativa per giustificare il flat ("vedi, se andassimo a persona sarebbe 14k, ti faccio flat 11k").

#### Raccomandazione finale

**Primi 5 clienti**: **Modello 1 flat a 8.500-11.000 €** in base alla complessità rilevata in pre-vendita. Margine basso (~50%), ma serve a:
- Costruire portfolio
- Raccogliere case study
- Stress-testare il cost model (i numeri di cui sopra sono stime, vanno verificati)
- Imparare a rifiutare i clienti sbagliati (vedi A.3)

**Dal 6° al 10° cliente**: introduci **Modello 2** come opzione. Setup a 9.500-11.000 € + manutenzione opzionale. Punta a chiudere almeno 3 contratti di manutenzione, anche light, per validare il modello ricorrente.

**Dall'11° cliente**: hai dati per capire quale modello regge. Possibili evoluzioni:
- Se hai 5+ manutenzioni attive: spingi Modello 2 e alza setup a 12-15k €.
- Se i clienti non comprano la manutenzione: tieni Modello 1 ma alza a 12-14k € e crea un upsell "evoluzione" semestrale a progetto.
- Se la domanda satura le ore: assumi/appalti il Custode-coach e spingi il prezzo a 18-25k € posizionandoti premium.

---

### A.3 Sensitivity / scenari

Cliente "medio" è il caso di riferimento (A.1). I costi sono ore × 80 €/h + token + vivi + quota fissi.

#### Scenario "facile" — 40 persone, dati ordinati, IT presente

Caratteristiche: organigramma chiaro, Drive già strutturato a clienti, NAS con permessi puliti, IT manager interno che fa anche da Custode con motivazione vera, ~300 file rilevanti effettivi.

| Voce | Stima |
|---|---|
| Ore Valentino | 35-40 |
| Token Claude | 50-80 € |
| Vivi | 250 € |
| **Costo Valentino** | **~3.300 €** |
| Pricing Modello 1 | 8.500 € → **margine 61%** |

Lo riconosci in pre-vendita perché: il referente porta in call un PDF dell'organigramma, parla di "Custode" usando il termine giusto già al primo incontro, ha già letto la pagina prodotto.

#### Scenario "medio" — 35 persone, dati misti, Custode part-time

È il caso A.1. 55 ore, ~5.300 € costo, pricing 11.000 € → margine 52%.

#### Scenario "difficile" — 50 persone, dati caotici, NAS legacy, Custode poco motivato

Caratteristiche: 800 GB-1.5 TB, NAS Synology di 8 anni con permessi pasticciati, Drive senza shared drives (solo "I miei drive" di 30 persone), email è l'unico archivio per metà dei contratti, il Custode è "il tipo di sistemi" che ha già 50 cose in mano e non vuole questa.

| Voce | Stima |
|---|---|
| Ore Valentino | 80-110 |
| Token Claude | 200-400 € |
| Vivi (probabili trasferte aggiuntive) | 500-700 € |
| **Costo Valentino** | **~8.500-11.000 €** |
| Pricing Modello 1 a 14.000 € | margine 21-39% |
| Pricing Modello 1 a 11.000 € | **margine negativo o nullo** |

**Warning — segnali per NON vendere (o vendere a 18k+ €)**:

1. Il titolare risponde "vediamo poi" quando chiedi chi sarà il Custode in pre-vendita.
2. In azienda non esiste già un'abitudine minima a documentare (intranet morta, niente onboarding scritto).
3. Il referente principale non è in direzione e dice "devo chiedere".
4. Il NAS è "gestito da Mario che è andato in pensione".
5. Il Drive è personale (ognuno il suo) invece di shared drive.
6. Più di 3 persone con diritto di veto sull'iniziativa.
7. Turnover annuo dichiarato sopra il 30%.
8. Pre-vendita richiede più di 3 call per arrivare al preventivo (segno di indecisione strutturale).

Se 3+ segnali presenti, l'opzione corretta è: **non vendere il pacchetto pieno**. Proponi una **fase 0 a pagamento (1.500-2.500 €)** in cui fai un assessment scritto e dici onestamente se ha senso procedere. Eviti di bruciare reputazione su una delivery che fallirà.

---

### A.4 Soglia di break-even

Assunzione di costi fissi personali + business: 50.000 €/anno (a Milano/Brescia/Verona, freelance senior con famiglia: affitto/mutuo, tasse stimate al 40-50% sul lordo, fissi business 5k). Adatta al caso reale.

#### Scenario base — Modello 1 a 11.000 €, margine ~5.700 €/cliente

| Obiettivo | Clienti/anno | Note |
|---|---|---|
| (a) Coprire costi fissi (50k €) | **9 clienti** | Già con questi sei in pari ma senza riserve |
| (b) Full-time confortevole (80k € netti) | **14 clienti** | Ai limiti della capacità solo di Valentino: 14 × 55h = 770h di delivery + 200-300h di pre-vendita, gestione, sviluppo prodotto = ~1000-1100h/anno. Compatibile con un anno pieno solista. |
| (c) Decidere di assumere/appaltare | **18-20+ clienti** | Sopra le 1.200h annue di delivery. A 16 clienti già sei stressato. A 20 devi delegare o l'Atto 2 (più ore-intensive: ~50% del lavoro) o pre-vendita |

#### Scenario evoluto — Modello 2 con 6 clienti/anno in setup + 12 manutenzioni light + 4 premium

- Setup: 6 × 9.500 = 57.000 €/anno
- Manutenzione light: 12 × 700 × 12 = 100.800 €/anno (ma con 12 × 1.5h × 12 = 216h annue di delivery manutenzione)
- Manutenzione premium: 4 × 1.500 × 12 = 72.000 €/anno (con 4 × 4h × 12 = 192h)

Ricavi: ~230k €. Ore totali delivery: 6 × 55 + 216 + 192 = ~740h. Compatibile, alti margini sui ricorrenti. Ma serve **costruire il portafoglio di manutenzioni gradualmente** (1-2 anni).

#### Trigger di assunzione/appalto

- **>12 manutenzioni attive**: appalta un junior part-time per il rituale settimanale (10-15 €/h) o un Custode-coach freelance.
- **>2 nuovi clienti/mese**: pre-vendita inizia a mangiare il tempo. Considera un setter commerciale a commissione.
- **Inizia a saltare check-up**: campanello d'allarme — qualcosa va appaltato prima che la qualità scada.

#### A.4.1 Evoluzione del costo per cliente nel tempo

Una nota importante: i costi della prima delivery saranno **più alti** della stima centrale. Calcola almeno +30-50% sulle ore per i primi 2-3 clienti, perché:

- Stai costruendo skill e prompt mai usati prima.
- Ogni cliente ti insegna pattern nuovi (es. M365 di un'azienda particolare ha permessi inattesi).
- La fase di pre-vendita è lenta perché non hai case study.

Curva attesa:

| Cliente n. | Ore Valentino attese | Note |
|---|---|---|
| 1° | 80-100 | Tutto da scoprire, accetta margine basso o negativo, è R&D |
| 2°-3° | 65-75 | Pattern emerge, prompt si stabilizzano |
| 4°-6° | 55-60 | Stima centrale del A.1 |
| 7°-10° | 45-55 | Skill maturate, automazione interna del Valentino-workflow |
| Oltre il 10° | 40-50 | Se non sale: indica saturazione del modello, vedi A.4 trigger assunzione |

Implicazione: il **vero** costo di delivery del 1° cliente sarà ~7-9k €. Non vendere il 1° cliente sotto i 9.500 € a meno che non sia un partner amico disposto a essere case study.

---

## PARTE B — Risk & legal audit

> **Disclaimer importante**: questo è un brief di lavoro, non un parere legale. Prima di firmare il primo contratto cliente, **consulta un avvocato GDPR italiano** (specializzato in trattamento dati B2B SaaS/consulenza, costo indicativo 800-1.500 € per setup contrattualistica base + DPA template). Per i settori regolamentati (B.2), oltre all'avvocato serve confronto col DPO del cliente.

### B.1 GDPR e trattamento dati

#### B.1.1 Ruoli GDPR

Il modello standard nella delivery del toolkit:

| Ruolo GDPR | Chi | Cosa fa |
|---|---|---|
| **Titolare del trattamento** | La PMI cliente | Definisce le finalità del trattamento (avere una wiki aziendale), decide quali dati far scandagliare, mantiene il controllo |
| **Responsabile del trattamento (esterno)** | Valentino (o la sua società/ditta) | Tratta i dati per conto del Titolare, secondo istruzioni documentate (= il DPA) |
| **Sub-responsabili** | Anthropic (Claude API), eventuali provider di MCP cloud, hosting del worktree | Trattano dati per conto di Valentino. Devono essere autorizzati nel DPA |
| **Interessati** | Dipendenti, clienti, fornitori, partner della PMI i cui dati personali compaiono nei file scandagliati | Hanno diritti GDPR (accesso, rettifica, cancellazione) verso il Titolare |

#### B.1.2 Atti richiesti

1. **Informativa privacy aggiornata del cliente**: la PMI deve aver informato i propri dipendenti/clienti che i loro dati possono essere trattati anche da fornitori esterni per finalità di organizzazione documentale. Verifica che la sua informativa attuale sia compatibile, altrimenti va integrata prima del kick-off.
2. **DPA (Data Processing Agreement) Valentino ↔ Cliente**: contratto separato o allegato al contratto principale, ex art. 28 GDPR.
3. **Autorizzazione ai sub-responsabili**: lista Anthropic, eventuali altri provider. Il cliente la firma una volta, Valentino la aggiorna se cambia (con preavviso).
4. **Eventuale DPIA (Data Protection Impact Assessment)**: necessaria se il trattamento è "ad alto rischio" — per la v1 con dati di una PMI generalista, non standard ma da valutare caso per caso. Per sanitario/finanziario è quasi certamente richiesta.
5. **Registro dei trattamenti**: la PMI dovrebbe averlo e aggiornarlo per includere questo trattamento (è suo obbligo, ma è bene ricordarglielo).

#### B.1.3 DPA tipo — cosa deve contenere (checklist)

Ex art. 28 par. 3 GDPR:

- [ ] Oggetto, durata, natura e finalità del trattamento
- [ ] Tipi di dati personali trattati (categorie) e categorie di interessati
- [ ] Obblighi e diritti del Titolare
- [ ] Istruzioni documentate del Titolare (cosa Valentino può e non può fare)
- [ ] Vincolo di riservatezza per chiunque tratti i dati (Valentino + eventuali collaboratori)
- [ ] Misure di sicurezza ex art. 32 (cifratura at-rest e in-transit, controllo accessi, MFA, audit log)
- [ ] Disciplina sub-responsabili (Anthropic, MCP provider): autorizzazione preventiva, lista mantenuta, preavviso per cambi
- [ ] Assistenza al Titolare per: risposte a richieste degli interessati, notifica data breach (entro 24h verso il Titolare, che a sua volta ha 72h verso il Garante), DPIA su richiesta
- [ ] Cancellazione/restituzione dati a fine servizio (vedi B.1.5)
- [ ] Audit right del Titolare (Valentino deve poter dimostrare la conformità)

> Esiste un template ICO/EDPB ragionevole online ma **NON va adottato senza adattarlo al contesto italiano e al servizio specifico**. Affidalo all'avvocato.

#### B.1.4 Trattamento durante lo scandagliamento

Domande critiche da risolvere e documentare:

| Domanda | Risposta proposta (v1) |
|---|---|
| Dove vengono memorizzati i dati durante l'elaborazione? | Worktree locale sul portatile di Valentino + cache temporanea Anthropic (durata limitata, vedi termini Anthropic) |
| Quanto a lungo restano sul portatile? | Solo per la durata della delivery + max 30 giorni post-handover per supporto. Poi cancellazione documentata |
| Il portatile è cifrato? | Sì obbligatorio (FileVault Mac / BitLocker Win). Documentare nel DPA |
| Chi altro accede oltre Valentino? | Nessuno per la v1. Quando ci saranno collaboratori → NDA + accesso limitato + log |
| I dati transitano fuori UE? | Sì — Anthropic è statunitense. Va dichiarato. Vedi B.3 |
| Backup dei worktree? | Solo cifrati, solo su provider con SCC firmate (es. Hetzner DE, scelte EU-only se possibile) |

#### B.1.5 Categorie particolari (art. 9 GDPR) — strategia di esclusione perimetrale

Categorie particolari = dati sensibili: salute, opinioni politiche/religiose/sindacali, orientamento sessuale, dati genetici/biometrici, dati giudiziari (art. 10).

**Strategia v1: esclusione perimetrale a monte, non filtro a valle.**

Significa: prima del kick-off, in fase di scoping del perimetro, Valentino e il Custode definiscono **quali cartelle/etichette NON vengono mai scandagliate**. Esempi tipici:

- `/Personale/`, `/HR/Cartelle-dipendenti/`, `/Medicina-del-lavoro/`
- Cartelle del DPO se presente
- Etichette mail "Riservato HR", "Medicina del lavoro"
- Cartelle sindacali

Documenta nel DPA: "Sono esclusi dal perimetro le seguenti location: [lista]. Valentino non vi accederà e Claude non vi sarà mai esposto."

**Cosa fare se Claude vede comunque dati sensibili (sbavatura del perimetro)**:

1. Lo skill di scandagliamento deve avere un filtro keyword (parole-spia: "diagnosi", "certificato medico", "104", "maternità", ecc.) → quando matcha, mette il file in quarantena e chiede revisione umana prima di processarlo.
2. Se confermato sensibile: skip + log + notifica al Custode che verifica il perimetro.
3. Mai includere queste informazioni in note del vault, anche derivate.

> Per i settori sanitari, il filtro keyword non basta — vedi B.2.

#### B.1.6 Cancellazione a fine delivery

A 30 giorni dall'handover (o termine concordato), Valentino esegue:

1. Cancellazione cifrata dei worktree locali (eraser tool tipo `srm` o equivalente Win).
2. Richiesta ad Anthropic di flush di eventuali cache (verifica nei termini Anthropic la procedura — se non automatica, va richiesta esplicitamente).
3. Cancellazione storage temporaneo cloud.
4. Lettera/email al cliente che attesta avvenuta cancellazione, con data e descrizione di cosa è stato cancellato.

Il vault stesso **resta del cliente** (è sul suo Drive o sul suo server). Valentino non lo conserva.

---

### B.2 Compliance settoriale

| Settore | Rischio dominante | Raccomandazione v1 |
|---|---|---|
| **Manifatturiero** | IP industriale (disegni CAD, formule, BoM), NDA con fornitori che vietano sub-trattamenti | **Vendi** — escludi cartelle CAD/R&D dal perimetro, lavora su commerciale/amministrazione. NDA reciproco rafforzato |
| **Studi commercialisti/legali** | Segreto professionale (art. 622 c.p.), conflitto di interessi tra clienti dello studio | **Vendi con cautela** — il segreto professionale si estende ai collaboratori, quindi a Valentino. NDA rafforzato + DPO/DPA fa il giro completo. Sconsigliato per studi grandi (>20 prof.) per complessità conflitti |
| **Sanitario** (cliniche, RSA, ambulatori, studi medici) | Categorie particolari ex art. 9, DPIA quasi sempre richiesta, vigilanza Garante elevata | **NON vendere v1 cloud-based**. Aspetta Step 3 on-premise. Eccezione: amministrazione/contabilità di una struttura sanitaria, con DPO del cliente coinvolto e perimetro che esclude rigorosamente cartelle cliniche |
| **Finanziario / consulenza patrimoniale** | Segreto bancario, dati riservati clienti finali, vigilanza Banca d'Italia/IVASS | **NON vendere v1** se cliente è soggetto a vigilanza prudenziale. Vendi a consulenze finanziarie indipendenti piccole solo con DPO coinvolto e perimetro stretto |
| **PA / partecipate** | Codice contratti, trasparenza, AGID | **NON vendere v1** — richiede certificazioni e iter di gara fuori scala |
| **Educational / formazione** | Dati di minori (se scuole), GDPR particolare | **Vendi solo** scuole di formazione professionale per adulti. Mai scuole/dopo-scuola con minori |
| **E-commerce/retail** | Dati clienti consumatori in volumi alti | **Vendi con cautela** — verifica che il volume dati B2C non triggeri DPIA. Spesso ok se perimetro è back-office, non DB clienti |
| **B2B servizi/agenzie** | Standard | **Vendi** — caso d'uso ideale per v1 |

Regola generale: per i primi 5 clienti, **stai sul B2B servizi/agenzie e manifatturiero light**. Lascia stare regolamentato finché non hai (a) almeno 5 delivery riuscite alle spalle, (b) il livello on-premise pronto, (c) un avvocato di fiducia che ti segue.

#### B.2.1 Domande di screening da fare in pre-vendita (5 minuti)

Una checklist da girare al cliente prima del preventivo, per capire se il settore impone vincoli:

1. Qual è il codice ATECO primario e che tipo di vigilanza avete (Banca d'Italia, IVASS, AGCOM, ASL, AIFA, ANAC, nessuna)?
2. Avete un DPO designato? Interno o esterno?
3. Avete fatto una DPIA negli ultimi 24 mesi? Su quali trattamenti?
4. Avete contratti con i vostri clienti che includono clausole di non-sub-trattamento o approvazione esplicita dei vostri sub-fornitori?
5. Trattate dati di minori o categorie particolari (salute, opinioni politiche, sindacali, biometrici, giudiziari) come parte del business core?

Se le risposte sono "no/nessuna/non lo sappiamo/normale GDPR" → sei in v1 servibile. Se anche una sola risposta accende un campanello (es. "DPO esterno presente + contratti con clausole strette") → fai entrare l'avvocato GDPR prima del preventivo, non dopo.

---

### B.3 Anthropic Terms

> **Avviso onestà**: i termini Anthropic cambiano. Quanto segue è ricostruito dalla conoscenza generale dei loro framework (Commercial Terms, Usage Policy, Data Processing Addendum) ma **va verificato direttamente** su `anthropic.com/legal` prima di ogni contratto cliente. Cito i documenti da cercare, non le clausole letterali.

#### B.3.1 Documenti Anthropic da leggere

1. **Commercial Terms of Service** (anthropic.com/legal/commercial-terms) — termini generali API/Console.
2. **Usage Policy** (anthropic.com/legal/aup) — cosa puoi e non puoi fare con Claude.
3. **Data Processing Addendum (DPA)** — sottoscrivibile a richiesta per uso che tratta personal data nel quadro GDPR. **Questo è il documento chiave** per la conformità di Valentino.
4. **Trust Center / Compliance page** — certificazioni (SOC2 type II, ISO 27001, HIPAA per certi tier).
5. **Documentation: data retention and privacy** — quanto durano le cache, opt-out training, ecc.

#### B.3.2 "Customer Data" nei termini Anthropic — applicato al caso Valentino

Nello schema Anthropic-Valentino:
- Anthropic è **processor**.
- Valentino è **controller verso Anthropic** del trattamento (cioè decide cosa mandare).
- Ma nello schema Valentino-cliente PMI, Valentino è **processor del cliente PMI**.
- Quindi: Anthropic è **sub-processor** del cliente PMI.

Implicazioni:
- Valentino deve aver sottoscritto il **DPA Anthropic** (richiedibile via support).
- Valentino deve dichiarare Anthropic come sub-processor nel **proprio DPA col cliente** (B.1.3).
- Anthropic ospita negli USA → trasferimento extra-UE → si applicano le clausole contrattuali standard (SCC). Anthropic le ha (verifica nel loro DPA).
- Verifica esplicitamente che Anthropic abbia clausola di **no-training-on-customer-data per la API commerciale** (standard nei loro termini, ma confermalo).

#### B.3.3 Tier da considerare per clienti regolamentati

Se in futuro vendi a sanitario/finanziario:
- **Claude API standard via console** può non bastare per casi HIPAA-like.
- **Anthropic via AWS Bedrock o GCP Vertex** offre garanzie di location dei dati EU/USA con il DPA del cloud provider in aggiunta.
- **Claude Enterprise** (offerta business diretta) ha controlli avanzati ma costi/contratto Enterprise.

Per la v1 non urgente. Per Step 3 (on-premise) la situazione cambia: o si va su deploy locale di un modello open source, o su Bedrock in region EU con configurazione ad-hoc.

---

### B.4 Responsabilità del consulente

#### B.4.1 Errore di categorizzazione (es. contratto importante finisce in CESTINO)

**Mitigazioni di design** (riducono il rischio prima che la clausola contrattuale debba intervenire):
- La "Regola della Bozza" del framework: Claude **non cestina** nulla. Propone, il Custode approva.
- Il decommissioning del Drive vecchio (Fase 5) avviene **in sola lettura, non cancellazione**. Anche se qualcosa è classificato erroneamente, il file originale resta.
- Backup del Drive vecchio prima del decommissioning, conservato 12 mesi.

**Clausola contrattuale di limitazione**: in nessun caso Valentino risponde per più di un multiplo del corrispettivo pagato per la delivery (tipicamente 1x). Esclusione di responsabilità per: danni indiretti, perdita di chance, perdita di reputazione, danni a terzi del cliente. Validità in Italia: ammessa per dolo solo se entro i limiti dell'art. 1229 c.c. (no esclusione per dolo o colpa grave).

#### B.4.2 Vault abbandonato a 6 mesi dall'handover

Clausola tipo: "Valentino garantisce l'idoneità dell'output al momento della consegna. La manutenzione del vault dopo l'handover è responsabilità del Cliente attraverso il Custode designato. In assenza di sottoscrizione di un servizio di manutenzione, Valentino non risponde dello stato del vault successivamente alla data di handover."

Aggiungi: 3 check-up mensili gratuiti = momento in cui Valentino segnala scritto che l'adozione è a rischio. Se il cliente ignora, è la sua responsabilità documentata.

#### B.4.3 SLA durante la delivery

Proposta v1:

| Evento | Tempo risposta |
|---|---|
| Blocco totale (Claude down, MCP fail, vault inaccessibile) | 8h lavorative |
| Bug bloccante in un batch (richiede intervento) | 24h lavorative |
| Domanda non urgente del Custode | 48h lavorative |
| Modifica al perimetro o evolutiva | Concordata di volta in volta |

SLA solo durante delivery + 30 giorni post. Dopo, solo se contratto di manutenzione. Lavorativi = 9-18 lun-ven, no agosto/festivi.

---

### B.5 Contratto di delivery — struttura tipo (skeleton)

Indice del contratto di consulenza chiavi-in-mano:

1. **Premesse** — chi sono le parti, contesto, oggetto generale
2. **Oggetto della prestazione** — costruzione di una wiki aziendale tramite il toolkit, dettaglio output
3. **Modalità di esecuzione (i 3 Atti)** — Atto 1 kick-off, Atto 2 scandagliamento, Atto 3 handover, durate, on-site vs remoto
4. **Output e accettazione** — cosa il cliente riceve a fine delivery (vault, manuale, Custode formato), criteri di accettazione, procedura di collaudo
5. **Obblighi del Cliente** — designazione Custode, accessi, disponibilità, perimetro privacy approvato per iscritto
6. **Trattamento dati personali (rinvio al DPA allegato)**
7. **Riservatezza e NDA reciproci** — durata 5 anni post-contratto, eccezioni standard (informazioni pubbliche, ottenute da terzi legittimamente, ecc.)
8. **Corrispettivi e fatturazione** — importo, modalità (es. 30% alla firma, 40% all'avvio Atto 2, 30% all'accettazione finale), spese vive a rimborso o forfait
9. **Limitazioni di responsabilità** — cap a 1x corrispettivo, esclusione danni indiretti, esclusione per uso post-handover (vedi B.4)
10. **Proprietà intellettuale** — il vault generato è del Cliente. Il toolkit (skill, prompt, codice MCP) resta di Valentino, concesso in licenza d'uso al Cliente per il vault generato. Le bozze e i template sono parte del toolkit
11. **Garanzie e SLA** — di delivery e di assistenza nei 30 giorni post, niente garanzie su utilizzo post-handover
12. **Manutenzione opzionale** — se sottoscritta, allegato separato con termini specifici
13. **Subappalto e collaboratori** — Valentino può avvalersi di collaboratori sotto NDA equivalente, comunicandolo al Cliente
14. **Risoluzione e recesso** — recesso del Cliente in qualsiasi momento con riconoscimento delle ore svolte; risoluzione per inadempimento ex art. 1456 c.c.
15. **Foro competente, legge applicabile, miscellanea**

**Allegati**: A) DPA, B) Lista sub-responsabili, C) Perimetro privacy approvato, D) SLA detail, E) Listino servizi opzionali.

> Skeleton, non testo. Il testo definitivo va prodotto con avvocato.

---

### B.6 Cose che spaventano clienti seri e come affrontarle

#### B.6.1 "I miei dati passano per Anthropic / USA / cloud?"

**Risposta onesta**: "Sì, durante la delivery i contenuti dei tuoi documenti vengono inviati all'API di Anthropic, che è in USA. Anthropic ha SCC firmate (clausole standard UE) e nel suo DPA si impegna a non usare i tuoi dati per addestramento. Il dato non resta su Anthropic in modo persistente — è in cache temporanea per il tempo dell'elaborazione. Al termine della delivery cancelliamo tutto."

**Cosa offrire in più**:
- "Possiamo escludere dal perimetro qualunque cartella tu non voglia vedere passata da Claude — basta che me lo dici prima del kick-off."
- "Per i dati che decidi di lasciare fuori, costruiremo comunque uno scheletro di MOC e link manualmente."
- "Sappi che è in roadmap (Step 3) una modalità on-premise con modello locale, senza traffico verso USA. Se per te è bloccante, parliamo di tempi e prezzi e magari aspettiamo quella."

#### B.6.2 "Cosa succede se Anthropic cambia i prezzi o smette il servizio?"

**Risposta**: "Il vault che ti consegno è 100% tuo, in Markdown plain text. Funziona senza Claude, lo apri con Obsidian o qualunque editor. Anthropic è uno strumento di costruzione, non un fornitore continuativo. Se domani Anthropic chiude, hai comunque tutto. La manutenzione che fa il tuo Custode è 90% editoriale e 10% AI-assistita — funziona anche senza."

Mostra fisicamente il vault aperto su Obsidian in modo offline durante la demo. Riduce drasticamente l'obiezione.

#### B.6.3 "Voglio una garanzia che funzioni"

**Cosa garantire**:
- Output specifici al termine della delivery (vault con N schede, manuale custode, Custode formato e validato in handover).
- Bug fix entro 30 giorni dall'handover gratis.
- 3 check-up mensili.

**Cosa NON garantire**:
- Adozione del Custode oltre la delivery (è loro responsabilità).
- ROI quantificato ("vi farà risparmiare X ore/anno" — non puoi garantirlo, dipende da loro).
- Comportamento futuro di Claude se cambiano i modelli.

**Frase utile in trattativa**: "Garantisco che lo strumento funziona alla consegna e che il tuo Custode è formato. Non posso garantirti che lo usi — quella parte è cultura aziendale e dipende da voi. Per questo facciamo 3 check-up: se vedo derive, te lo dico per scritto."

#### B.6.4 "Mi state buttando dentro un'AI in azienda — io non ho mai usato ste cose"

**Tipico in PMI manifatturiere/tradizionali con titolare ultra-sessantenne.**

**Risposta**: "Tu non userai l'AI direttamente. L'AI è uno strumento che uso io, in fase di setup, per costruire la wiki più velocemente. Quello che resta a te è una raccolta di documenti normali — pagine Markdown — che il tuo Custode aggiorna a mano (con o senza assistente AI, decidi tu). Non stai mettendo un agente AI nella tua azienda. Stai mettendo una wiki ben fatta. L'AI sparisce al termine dei tre Atti."

Importante: questa è la **verità del prodotto v1**. Non barare: se in roadmap c'è l'agente persistente, non venderlo qui.

#### B.6.5 "Devo coinvolgere il mio DPO / legale?"

**Quando dire SÌ apertamente**:
- Settori regolamentati (B.2: sanitario, finanziario, legale, PA).
- Cliente sopra ~250 dipendenti (anche se v1 è 30-50, può capitare).
- Cliente con DPO interno o esterno designato.
- Cliente che processa dati di minori o categorie particolari come business core.

**Quando dire NO (con motivazione)**:
- PMI 30-50 persone B2B servizi senza DPO obbligatorio: "Il DPA che ti faccio firmare è standard GDPR ex art. 28. Se ti va, te lo manda l'avvocato a leggere, ma non è obbligatorio coinvolgere un DPO. Se ne hai uno, ben venga."

**Frase utile**: "Se hai un DPO, mandagli il DPA e la lista sub-responsabili prima di firmare. Se non lo hai, valuta col tuo commercialista. Io posso anche aspettare 1-2 settimane — è normale."

---

## Note conclusive

- **Aggiornamento**: questo documento va rivisto dopo il 1° cliente reale (cost model) e dopo il 3° cliente (pricing/risk pattern). Datalo, versionalo.
- **Verifica esperta richiesta prima del 1° contratto**: avvocato GDPR italiano per DPA + contratto base; commercialista per fatturazione e regime fiscale; eventualmente RC professionale (assicurazione 400-800 €/anno utile per dormire la notte).
- **Cosa non è in questo doc e va affrontato a parte**: piano commerciale (come trovare i primi 5 clienti), modello operativo (cosa fa Valentino quando ne ha 8 in parallelo), evoluzioni roadmap (Step 2 e 3 prodotto).

### Checklist pre-vendita rapida (per Valentino)

Prima di mandare il preventivo, controlla:

- [ ] Pre-vendita screening B.2.1 fatto, settore servibile in v1
- [ ] Custode identificato con nome e cognome + 4 sì del test Fase 0 (manuale custode)
- [ ] Perimetro privacy abbozzato (cartelle escluse, almeno macro-aree)
- [ ] Stima volume dati ottenuta (non importa se imprecisa, basta ordine di grandezza)
- [ ] Nessuno dei 3+ segnali "non vendere" di A.3 presente
- [ ] Stima ore basata su scenario corretto (facile/medio/difficile)
- [ ] Pricing scelto (Modello 1 per i primi 5) + range di +/-10% per negoziazione
- [ ] DPA + contratto pronti per la firma (template legali già revisionati una volta)
- [ ] Ore Custode dichiarate esplicitamente in preventivo

Se uno qualunque non è spuntato: non mandare il preventivo, sistema prima.
