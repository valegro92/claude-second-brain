# 08 — Modalità on-premise (Step 3)

Per Valentino + Custode di clienti regolamentati. Spiega quando passare al
binario on-premise, le tre opzioni disponibili, come configurarle e come
dimostrare al DPO del cliente che il dato non esce dall'azienda.

Pre-letture:

- `_brief/04-step-2-tech-plan.md` §8 ("Privacy e modalità on-premise")
- `_brief/06-cost-and-risk.md` §B.1 (GDPR), §B.2 (Compliance settoriale)
- `docs/05-manuale-custode.md` (per spiegare al Custode cosa cambia per lui)

---

## 1. Quando serve la modalità on-premise

Lo scenario standard (Step 2) usa l'API Anthropic in modalità `safe` o `full`,
con `redact_pii: false`. Va bene per la stragrande maggioranza delle PMI B2B
servizi/agenzie e per il manifatturiero light.

Serve uscire da quel default quando una di queste condizioni è vera:

| Trigger | Cosa fare |
|---|---|
| Cliente regolamentato (sanitario, finanziario, legale grosso, PA) | **Bedrock account cliente** o aspettare deploy locale |
| Cliente con DPO interno che vieta sub-trattamento extra-UE | **Bedrock region EU** del cliente |
| Cliente con NDA esterni che vietano cloud terzi | **Docker isolato** + Bedrock cliente |
| Dati con PII concentrate (es. anagrafiche clienti finali) | **safe-mode + `redact_pii: true`** anche senza cambiare provider |
| Cliente "spaventato da AI in azienda" ma non regolamentato | API standard + `redact_pii: true` + verifica DPO leggera (vedi §5) |

Settori dove **non vendere** la v1 cloud-based:

- Sanitario (cliniche, RSA, ambulatori): aspetta Bedrock + DPA cliente.
- Finanziario sotto vigilanza Banca d'Italia/IVASS.
- PA / partecipate.

Eccezione: amministrazione/contabilità di una struttura sanitaria, con
perimetro che esclude rigorosamente le cartelle cliniche e Bedrock attivo.

---

## 2. Le tre opzioni operative

### Opzione A — Bedrock nell'account cliente

Claude gira su AWS Bedrock dentro l'account AWS del cliente. La chiamata
parte dal toolkit (sul Mac di Valentino o sull'host on-premise), arriva
all'endpoint Bedrock regionale (es. `bedrock-runtime.eu-west-1.amazonaws.com`),
firmata con le credenziali del cliente. **Il dato non esce dall'account AWS
del cliente** e dalla region scelta.

Quando: cliente ha già un account AWS o è disposto ad aprirlo, vuole una
compliance posture chiara (data residency EU, DPA AWS + Anthropic via
Bedrock, fatturazione su AWS bill cliente).

Pro:
- Data residency garantita dalla region AWS.
- Una singola fattura cloud lato cliente (no relazione contrattuale diretta
  cliente ↔ Anthropic).
- Modelli identici (qualità) a quelli dell'API standard.

Contro:
- Costo Bedrock ~10-20% più alto dell'API standard.
- Modelli abilitabili variano per region (verifica prima del kick-off:
  i model id Bedrock cambiano spesso).
- Setup AWS iniziale (15-30 min).

### Opzione B — anthropic API standard + `redact_pii: true`

API Anthropic standard di sempre, ma con safe-mode wrapper attivo: le PII
(email, CF, IBAN, telefono) vengono mascherate in placeholder
(`<email-1>`, `<cf-2>`, ...) prima di ogni chiamata. Il modello non vede mai
il valore reale.

Quando: cliente non regolamentato ma sensibile alle PII (es. agenzia che
gestisce DB clienti finali), o cliente con DPO che vuole una mitigazione
tecnica documentabile senza cambiare infrastruttura.

Pro:
- Zero cambio di provider, setup invariato.
- Mappa redact persistita e ispezionabile: dimostrabile al DPO.
- Funziona da subito.

Contro:
- Le PII restano scritte sul portatile / host del toolkit (la mappa redact è
  in chiaro). Vanno protette come ogni altro dato cliente.
- I dati NON-PII (testi liberi, oggetto, contenuto file) continuano a
  passare ad Anthropic.
- Riduzione qualità trascurabile su categorizer e schede; possibile su
  reconciler persone (è proprio sulle PII).

### Opzione C — Docker fully isolated

Immagine Docker (vedi `Dockerfile`) con tutto incluso (Pandoc, Tesseract,
Poppler, codice toolkit). Gira sull'host del cliente, mai sul portatile di
Valentino. Combinata con Bedrock raggiunto via VPC endpoint cliente, può
essere fully air-gapped.

Quando: cliente vuole zero presenza del consulente sui propri dati. Tipico
nel finanziario o quando il cliente ha già un IT severo.

Pro:
- Il dato non lascia mai l'host del cliente (a parte la chiamata Bedrock,
  che resta dentro l'AWS del cliente se VPC endpoint).
- Audit semplice: cosa gira è quello che è scritto nel Dockerfile.
- Replicabile (più clienti = più container).

Contro:
- Valentino deve avere SSH/RDP per fare il kick-off remoto, o trasferta
  estesa.
- Custode deve avere familiarità con Docker (o ti devi appoggiare al loro IT).
- Debug più complesso (log accessibili via volume montato).

---

## 3. Setup Opzione A — Bedrock

### 3.1 Prerequisiti AWS lato cliente

Da concordare nel kick-off (`docs/02-kickoff-checklist.md`):

1. Account AWS attivo con admin disposto a creare IAM e abilitare modelli.
2. Region scelta in base alla compliance (EU: `eu-west-1` Irlanda,
   `eu-central-1` Francoforte; US: solo se ammissibile).
3. **Modelli Anthropic abilitati nella region**:
   - Aprire AWS Console → Bedrock → Model access → richiedere accesso a
     "Anthropic Claude Haiku 4.5" e "Anthropic Claude Sonnet 4.5".
   - L'abilitazione è quasi istantanea per gli account standard. Per
     account con AWS Organizations centralizzato può richiedere ticket
     all'admin.
4. IAM role o profilo con policy minima:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
       "Resource": [
         "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-haiku-4-5-*",
         "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-sonnet-4-5-*"
       ]
     }]
   }
   ```

5. Credenziali esposte al toolkit via uno tra:
   - `~/.aws/credentials` + `AWS_PROFILE=<nome>` (preferito, no segreti in env).
   - Variabili `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.
   - IAM role se il toolkit gira su EC2 / ECS del cliente.

### 3.2 Configurazione toolkit

In `bootstrap/clients/<slug>/config.yml`:

```yaml
llm:
  provider: bedrock
  redact_pii: false      # opzionale: combinabile con Bedrock per layer extra
  bedrock:
    region: eu-west-1
    aws_profile: cliente-bedrock
    model_overrides:
      fast: anthropic.claude-haiku-4-5-20251001-v1:0
      smart: anthropic.claude-sonnet-4-5-20251022-v2:0
```

**Verifica i model id reali** sulla console Bedrock del cliente prima di
fissarli: AWS rinomina i modelli con suffisso versione, e i default in
`wiki/llm/bedrock.py` sono solo placeholder.

### 3.3 Smoke test

```bash
AWS_PROFILE=cliente-bedrock wiki test-llm --client <slug>
```

(Se questo comando non esiste ancora, fa lo stesso un piccolo script Python:
istanziare `get_llm_client(config)` con `provider: bedrock`, chiamare
`client.complete(messages=[{"role":"user","content":"ping"}], model="fast")`
e stampare la response.)

---

## 4. Setup Opzione B — safe-mode + `redact_pii: true`

### 4.1 Cosa viene mascherato

| Tipo | Pattern | Esempio | Placeholder |
|---|---|---|---|
| Email | regex RFC-light | `m.rossi@bianchi.it` | `<email-1>` |
| Codice fiscale | 16 char (LLLLLL DD L DD L LLL L) | `RSSMRA80A01H501U` | `<cf-1>` |
| IBAN | LL DD + 11-30 alfanum (con spazi tollerati) | `IT60X0542811101000000123456` | `<iban-1>` |
| Telefono italiano | con/senza +39, separatori | `+39 02 1234567` | `<phone-1>` |

I placeholder sono **stabili** tra chiamate e tra rerun (la mappa è
persistita): la stessa email genererà sempre `<email-1>`. Questo serve a
mantenere la coerenza nei reconciler che processano lo stesso dato più volte.

### 4.2 Configurazione

```yaml
llm:
  provider: anthropic_api
  redact_pii: true
```

Va anche bene combinare con `provider: bedrock` per Layer-2.

### 4.3 Dove vive la mappa redact

`_status/audit/redact-map.json`. Struttura:

```json
{
  "_format_version": 1,
  "forward": {
    "m.rossi@bianchi.it": "<email-1>",
    "+39 02 1234567": "<phone-1>",
    "IT60X0542811101000000123456": "<iban-1>"
  },
  "counters": {"email": 1, "cf": 0, "iban": 1, "phone": 1}
}
```

Considera questa mappa **dato sensibile equivalente al vault stesso**:
deve restare sul host del cliente (è in `_status/`, già gitignored e
mountato come volume nel container). Non spostarla mai fuori.

### 4.4 Limiti dichiarati al DPO

Cosa il safe-mode NON copre:

- Nomi di persona scritti in chiaro (es. "Mario Rossi" nel corpo di una mail).
- Numeri di partita IVA aziendali (sono dati pubblici, ma il DPO potrebbe
  considerarli sensibili in combinazione).
- Indirizzi fisici, dati medici, contenuti di contratti.
- Le immagini (la vision pipeline non maschera i volti).

Per quegli scenari, vedi l'esclusione perimetrale (brief 06 §B.1.5):
si lavora a monte, escludendo cartelle/etichette dal kick-off.

---

## 5. Setup Opzione C — Docker

### 5.1 Build dell'immagine

Dalla root del repo (sul Mac di Valentino o sull'host del cliente):

```bash
docker build -t wiki-toolkit:latest .
```

Build atteso: 4-8 min la prima volta (Tesseract italiano è ~150 MB).
Successivi rebuild: <1 min grazie alla cache layer.

### 5.2 Run via compose

`docker-compose.yml` è già pronto con i volumi corretti. Avvio:

```bash
# Variabili d'ambiente per il provider scelto (.env locale).
cp .env.example .env  # se esiste, altrimenti crearlo
# Modificare:
#   ANTHROPIC_API_KEY=...     se provider = anthropic_api
#   AWS_PROFILE=...           se provider = bedrock

# Lancio di un comando del toolkit
docker compose run --rm wiki-toolkit scan --client <slug>
docker compose run --rm wiki-toolkit categorize --client <slug>
docker compose run --rm wiki-toolkit approve --client <slug>    # apre batch UI su :7423
```

I volumi sono:

- `bootstrap/clients/` → config + auth (mai in image)
- `_status/` → output runtime (mai in image)
- `_inbox/` → drop zone watcher
- `vault/` → vault del cliente (target del flush)

### 5.3 Network isolato

Default: `docker-compose.yml` usa un bridge `isolated`. Per cliente fully
air-gapped (Bedrock via VPC endpoint, niente Internet):

1. Decommentare `internal: true` nella sezione `networks.isolated`.
2. Assicurarsi che l'host abbia un VPC endpoint AWS configurato per
   raggiungere Bedrock senza passare per Internet.
3. Verificare che `provider: bedrock` sia configurato (Internet completo è
   richiesto da `provider: anthropic_api`).

### 5.4 Hardening minimi già applicati

L'immagine in `Dockerfile`:

- gira come utente non-root (`uid 1000`),
- non installa pacchetti dev,
- ha `tini` come PID 1 (gestione segnali corretta).

`docker-compose.yml`:

- `cap_drop: ALL` + `no-new-privileges`,
- batch UI esposta solo su `127.0.0.1:7423` (no LAN),
- `restart: "no"` (toolkit batch-oriented, non daemon).

Per produzione cliente: aggiungere `read_only: true` sul container e dei
`tmpfs` per `/tmp`, e firmare l'immagine con cosign se il cliente richiede
supply chain attestation.

---

## 6. Verifica privacy: come dimostrare al DPO

Il DPO del cliente vuole sapere: "X dato esce dalla mia azienda? Se sì,
verso chi?". Risposta strutturata da fornire per ciascuna opzione:

### Opzione A — Bedrock account cliente

| Domanda DPO | Risposta |
|---|---|
| Dove arriva la chiamata LLM? | `bedrock-runtime.<region>.amazonaws.com`, endpoint dentro l'AWS del cliente |
| Chi vede il payload? | Anthropic via Bedrock (sub-processor del cliente AWS, DPA AWS + DPA Anthropic via Bedrock) |
| Persistenza? | Nessuna: Bedrock processa e scarta. Verificabile via AWS CloudTrail (`bedrock:InvokeModel` log) |
| Data residency? | Garantita dalla region scelta |
| Come bloccare l'egress? | Network policy lato VPC: solo `bedrock-runtime.<region>.amazonaws.com` |

Documentazione da consegnare:

- Estratto config `llm.provider: bedrock` + region.
- CloudTrail report di un sample di chiamate (ts, ARN modello, IP sorgente).
- DPA AWS firmato.

### Opzione B — safe-mode + `redact_pii: true`

| Domanda DPO | Risposta |
|---|---|
| Dove arriva la chiamata? | `api.anthropic.com` (USA, SCC firmate) |
| Cosa vede Anthropic? | Tutto MENO email/CF/IBAN/telefono (vedi tabella §4.1) |
| Come verifico? | Sample dei messaggi inviati: log con il payload redacted in `_status/audit/llm-payloads.jsonl` se attivato, oppure ispezione live in dry-run |
| Persistenza? | Cache temporanea Anthropic (vedi termini), no training (DPA Anthropic standard) |
| Mappa PII? | Resta sul host del cliente in `_status/audit/redact-map.json` |

Documentazione:

- Estratto config `llm.redact_pii: true`.
- Sample di 3 prompt redacted (dimostrazione visiva che `m.rossi@x.it`
  diventa `<email-1>`).
- File `redact-map.json` mostrato live (non consegnato — è il dato).
- DPA Anthropic firmato + lista sub-processor.

### Opzione C — Docker isolato + Bedrock cliente

Combina le evidenze di Opzione A con in più:

- Hash dell'immagine Docker (`docker image inspect`).
- Docker compose con `network internal: true` (se applicabile).
- IP/route table dell'host che dimostra niente egress verso `api.anthropic.com`.
- Audit periodico: il cliente può confrontare gli hash a sorpresa.

---

## 7. Cosa fare al kick-off

Per ognuna delle 3 opzioni, ecco la patch operativa al kick-off
(`docs/02-kickoff-checklist.md`):

1. **Identificare il trigger** (vedi §1): è cliente regolamentato?
   è cliente sensibile a PII? è cliente air-gapped?
2. **Scegliere l'opzione** con cliente + Custode + (se presente) DPO.
3. **Scrivere il `config.yml`** del cliente (vedi `bootstrap/config.template.yml`
   sezione `llm:`).
4. **Smoke test** dal terminale di Valentino (poi, se Docker, dall'host).
5. **Mettere agli atti** del DPA cliente: provider scelto + region (se
   Bedrock) + safe-mode on/off + lista sub-processor.

Se il cliente non sa rispondere a "sei regolamentato?" → non vendere
ancora: rimanda all'avvocato GDPR del cliente. È un caso da brief 06 §A.3
"warning, non vendere".

---

## 8. Cosa NON fa la modalità on-premise (limiti dichiarati)

- **Non sostituisce l'esclusione perimetrale**. Anche con Bedrock + safe-mode,
  i dati delle categorie particolari (art. 9 GDPR — salute, opinioni, ecc.)
  vanno **comunque esclusi a monte** dal kick-off. Il safe-mode è un layer
  di mitigazione, non di liceità.
- **Non rende il toolkit certificato HIPAA / ISO 27001**. Per quelle
  certificazioni serve un audit formale separato; on-premise rimuove uno
  dei requisiti (perimetro) ma non basta da solo.
- **Non protegge da un Custode malevolo**. Chi ha accesso al vault e a
  `_status/` ha accesso a tutto. Restano necessari NDA + access control
  lato cliente.
- **Non protegge le immagini da Claude vision** quando attiva
  (`extractors/pdf_ocr.py` con backend vision). Per quel caso, valuta blur
  pre-OCR fuori dal toolkit.

---

## 9. Riferimenti

- Codice: `wiki/llm/` (astrazione provider), `wiki/llm/safe_mode.py` (redact).
- Config: `bootstrap/config.template.yml` sezione `llm:`.
- Test: `tests/test_llm.py`.
- Brief: `_brief/04-step-2-tech-plan.md` §8, `_brief/06-cost-and-risk.md` §B.
- Docker: `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
