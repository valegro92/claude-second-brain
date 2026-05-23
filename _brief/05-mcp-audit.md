# Audit MCP per le 5 fonti

Documento di lavoro temporaneo per lo Step 1. Decisioni di fattibilita tecnica
sui connettori MCP che il toolkit usera nella fase di scandagliamento (Step 2).
Sara rimosso o assorbito in `docs/` a fine Step 1.

Data audit: 2026-05-23. Fonti: ricerca su modelcontextprotocol.io, github.com,
learn.microsoft.com, developers.google.com. Le info su "ultima attivita" sono
una fotografia: vanno riverificate prima di mettere in produzione presso un
cliente.

## Sintesi

Su 5 fonti, **nessuna ha un MCP server "enterprise-grade ufficiale a costo
zero"** utilizzabile out-of-the-box per una PMI di 30-50 persone. Il quadro
reale:

- **2 fonti** (Google Drive, Microsoft 365) hanno **fork community maturi** che
  reggono per la v1, ma richiedono comunque setup non banale lato IT cliente
  (app registration Azure AD, OAuth client GCP) e nessuno e ufficiale.
- **1 fonte** (Microsoft 365) ha anche un **canale ufficiale Microsoft** (Agent
  365 / Work IQ) ma richiede licenza Microsoft 365 Copilot per ogni utente che
  consuma — fuori budget per PMI v1.
- **1 fonte** (Email) ha **MCP server community frammentati**, alcuni gia
  archiviati. Il piu maturo (GongRzhe) e stato archiviato a marzo 2026.
- **1 fonte** (NAS/SMB) ha **MCP server prototipali** (1 commit, 1 star). Per
  la v1 conviene montare la share localmente e usare il Filesystem MCP
  ufficiale di Anthropic.
- **1 fonte** (Server SSH/SFTP) ha **MCP community decenti** (classfang con
  ~470 star, mixelpixx, veithly) ma il caso d'uso "scandagliare file" e mal
  servito: gli SSH MCP sono pensati per esecuzione comandi remoti, non per
  enumerare e leggere documenti.

Conclusione operativa: la v1 del toolkit deve includere **3 MCP riusati**
(Google Drive fork piotr-agier, Microsoft 365 Softeria, Filesystem ufficiale)
e **2 script custom** (estrattore email via Gmail/Graph SDK, estrattore SSH/SFTP
via libreria standard). Investire ora in adapter custom per email e SSH paga,
perche tanto i clienti reali avranno casistiche che gli MCP community non
coprono.

## Tabella riassuntiva

| Fonte | MCP disponibile | Maturita (1-5) | Raccomandazione v1 | Setup cliente |
|---|---|---|---|---|
| 1. Google Drive / Workspace | piotr-agier/google-drive-mcp (fork community attivo) | 3.5 | Incluso (con fallback script) | Medio: OAuth client GCP, scope review, eventuale verifica app |
| 2. Microsoft 365 / OneDrive / SharePoint | Softeria/ms-365-mcp-server (200+ tool Graph) | 3.5 | Incluso (con caveat) | Alto: app registration Azure AD, consenso admin per scope org |
| 3. Email (Gmail + Outlook) | Frammentato; GongRzhe archiviato a mar 2026; marlinjai/email-mcp unificato ma piccolo (11 star) | 2 | Parziale: script custom + MCP solo come fallback | Medio (Gmail) / Alto (Outlook con OAuth aziendale) |
| 4. NAS / cartelle di rete (SMB/NFS) | Filesystem MCP ufficiale Anthropic su path montato; natan04/mcp-smb-server prototipale | 4 (via mount) / 1.5 (SMB nativo) | Incluso via mount locale | Basso: mount SMB/NFS su workstation del consulente |
| 5. Server interno (SSH/SFTP) | classfang/ssh-mcp-server (~470 star); altri 3-4 alternative; tutti orientati a "esegui comandi" | 2.5 | Script custom (SFTP + paramiko/ssh2); MCP solo per validazione manuale | Basso/Medio: account read-only su server, eventuale jump host |

Legenda maturita:
- 1 = prototipo/proof of concept, non production-ready
- 2 = community minimale, manutenzione incerta
- 3 = community attiva, copre l'80% dei casi
- 4 = solido, mantenuto da team o azienda
- 5 = ufficiale del vendor, supporto enterprise

## Dettaglio per fonte

### 1. Google Drive / Google Workspace

**MCP server di riferimento**

Anthropic aveva un `mcp-server-gdrive` ufficiale che pero e stato **archiviato
nel maggio 2025** insieme a molti altri reference server (GitHub, Slack,
PostgreSQL, ecc.). Vive ora in `modelcontextprotocol/servers-archived` come
"historical reference, no longer maintained". Non e una scelta valida per la
v1.

**Migliore alternativa community oggi**: `piotr-agier/google-drive-mcp`

- URL: https://github.com/piotr-agier/google-drive-mcp
- ~155 stelle, ~86 fork, ultimo release v2.2.0 del 21 aprile 2026
- TypeScript, MIT
- Copre **Drive + Docs + Sheets + Slides + Calendar** in un solo server
- Supporta **Shared Drives** (ex Team Drives), permessi (share/unshare/role
  update), revisioni file, conversione PDF -> Google Doc

**Funzionalita**

- Lettura: ricerca file, list cartelle, download contenuto, leggi sheet/doc
- Scrittura: create/update/delete/rename/move/copy/upload
- Watch real-time: **non supportato** (niente changes feed API)
- Batch: si, ma operazioni una alla volta (no bulk transactional)

**Auth**

Tre modalita:
1. OAuth 2.0 browser-based locale (default) — l'utente fa il consenso una
   volta, token cached
2. Service account con domain-wide delegation (Workspace) — adatto a impieghi
   server-side ma richiede admin Workspace
3. Token esterni (access + refresh forniti)

**Limiti noti**

- Drive API: 20.000 chiamate / 100s per utente e per progetto (quota nuova dal
  1 maggio 2026); write sostenute max 3 req/s per account; upload limite 750
  GB/giorno per utente
- OAuth in "testing" status: refresh token scade dopo 7 giorni. Per produzione
  serve **OAuth app verification** (gratuita per scope non-sensitive, ma se si
  usa `drive.readonly` o simili scope sensibili la verifica puo richiedere
  settimane; gli scope restricted possono richiedere security assessment a
  pagamento)
- Container Docker richiedono pre-autenticazione (no browser nel container)
- Non supporta watch/changes feed: per rilevare modifiche serve polling

**Costo**

- API Drive: gratuita fino alle quote standard. Da fine 2026 Google ha
  annunciato billing per overage (almeno 90gg di preavviso prima
  dell'attivazione). Per PMI tipiche del nostro target le quote default sono
  abbondanti.
- OAuth verification: gratuita per scope non-sensitive; processo manuale per
  sensitive (settimane); security assessment per restricted (a pagamento, ~15-75k
  USD se serve Tier 2/3 — non applicabile al nostro caso d'uso atteso)

**Setup tipico per il cliente**

1. IT cliente crea un progetto su Google Cloud Console
2. Abilita Drive API + Docs/Sheets/Slides API
3. Configura OAuth consent screen (interno se Workspace, external se Gmail
   misti)
4. Crea OAuth Client ID di tipo "Desktop App"
5. Scarica `credentials.json`, lo passa a Valentino
6. Valentino fa il primo login OAuth dalla propria workstation, token cached

Tempo realistico: 30-60 min con un IT che non l'ha mai fatto. Documentare con
screenshot per ridurre.

**Alternative se l'MCP non basta**

- Google Drive Python/Node SDK ufficiali: stabili, ben documentati, da usare
  per scraper custom (es. estrarre tutti i Google Docs di una cartella in
  Markdown rispettando i permessi)
- `rclone` per backup/mirror cartella Drive su locale, poi Filesystem MCP
- Export manuale via Google Takeout (last resort se l'IT non vuole concedere
  OAuth)

**Verdetto v1**: **Incluso**. Fork piotr-agier come default, con script
fallback per estrazione massiva (Google Drive SDK) gia previsto. Documentare
chiaramente il rischio "OAuth verification" per clienti con scope sensitive.

---

### 2. Microsoft 365 / OneDrive / SharePoint / Teams

**Quadro generale**

Tre famiglie di opzioni:

1. **MCP ufficiali Microsoft** (Agent 365 / Work IQ): remoti, hosted da
   Microsoft, accessibili su endpoint tipo
   `https://agent365.svc.cloud.microsoft/agents/tenants/{tenant_id}/servers/...`.
   **Richiedono licenza Microsoft 365 Copilot per ogni utente che consuma il
   server** (confermato da blog ufficiali Microsoft di nov 2025). Una licenza
   Copilot costa ~30 EUR/utente/mese. Per una PMI di 50 persone significa
   ~1500 EUR/mese aggiuntivi — **fuori budget v1**.
2. **OneDrive/SharePoint Remote MCP Server (ODSP)**: deprecato a marzo 2026,
   rimpiazzato dai nuovi Microsoft SharePoint/OneDrive MCP Server (sempre
   sotto Agent 365 con licenza Copilot).
3. **MCP community** che parlano direttamente con Microsoft Graph API.

**Migliore alternativa community oggi**: `Softeria/ms-365-mcp-server`

- URL: https://github.com/Softeria/ms-365-mcp-server
- v0.113.0 al 23 maggio 2026, 228 release, 427 commit, sviluppo molto attivo
- ~200 tool che mappano 1:1 endpoint Graph
- Copre: Outlook (mail), Calendar, OneDrive (file), Excel, OneNote, tasks,
  planner, contatti, profili, Teams, SharePoint, meeting, user management
- Supporto multi-account in singola istanza

**Auth**

- Delegated permissions via MSAL (Microsoft Authentication Library)
- Device code flow (Valentino sulla workstation), OAuth authorization code
  flow (in modalita HTTP server), bring-your-own-token
- Flag `--org-mode` per abilitare scope Teams/SharePoint organizativi

**Altre alternative community degne di nota**

- `ftaricano/mcp-onedrive-sharepoint`: focus su OneDrive/SharePoint, 33 tool,
  delegated o client credentials, supporto permissions e Excel. Piu specifico
  ma meno completo
- `pnp/cli-microsoft365-mcp-server`: wrapper sul CLI PnP Microsoft365, utile
  per scenari amministrativi
- `SwamiRama/m365-mcp-server`: OAuth 2.1 + PKCE, focus mail+SharePoint+OneDrive
- `mpalermiti/outlook-mcp`: solo Outlook account personali, 54 tool. Non
  copre account org

**Limiti noti**

- Microsoft Graph throttling: **cap globale ~130.000 richieste / 10s per app
  cross-tenant**; limiti service-specific (SharePoint/OneDrive) si attivano
  prima. Throttle restituisce 429 + `Retry-After` header. Operazioni write
  costano 2 RU (resource unit) ciascuna
- Limite isolato per app per tenant (no impatto cross-tenant)
- Upload OneDrive: file >4 MB richiedono upload session (multipart), gestito
  dal MCP ma occhio a file di Office grossi
- Pagination obbligatoria su list grossi (`@odata.nextLink`) — alcuni MCP
  community la gestiscono male
- Refresh token Azure AD: di default 90 giorni di inattivita prima della
  scadenza, ma la sessione richiede re-login periodico

**Costo**

- Graph API: gratuita
- Azure AD app registration: gratuita
- Se si va su Agent 365 ufficiale: licenza M365 Copilot ~30 EUR/utente/mese —
  prohibitivo
- Eventuale Premium P1/P2 per scenari di Conditional Access avanzati: opzionale

**Setup tipico per il cliente**

1. IT cliente / admin Entra (ex Azure AD) crea un'app registration in Azure
   Portal
2. Configura scope/permessi necessari: minimo `Files.Read.All`,
   `Sites.Read.All`, `Mail.Read`, `User.Read`, `offline_access`
3. **Admin consent obbligatorio** per scope con `.All` (richiede ruolo Global
   Admin o Application Admin)
4. Configura redirect URI (per device code flow basta
   `https://login.microsoftonline.com/common/oauth2/nativeclient`)
5. Fornisce a Valentino: tenant ID, client ID, eventuale client secret
6. Primo login device-code da Valentino

Tempo realistico: 1-2 ore con un IT che non l'ha mai fatto, di piu se serve
un security/compliance review interno per il consenso scope.

**Alternative se l'MCP community ha problemi**

- Microsoft Graph SDK ufficiali (Python `msgraph-sdk`, .NET, JS): rock solid
- PowerShell `Microsoft.Graph` per script one-shot
- SharePoint REST API legacy per casi edge non coperti da Graph

**Verdetto v1**: **Incluso, con caveat**. Default Softeria, fallback script
custom basati su Graph SDK Python per estrazioni massive (rispetto delle
quote, retry su 429). Documentare per il cliente che il setup Azure AD non e
banale e che il consenso admin e bloccante.

---

### 3. Email — Gmail e Outlook

**Quadro generale**

Questa e la fonte **piu rischiosa**. Il panorama MCP email e affollato di
progetti piccoli, spesso single-developer, e il piu noto e stato archiviato.

**Candidati esaminati**

- `GongRzhe/Gmail-MCP-Server`: era il piu popolare. **Archiviato il 3 marzo
  2026, repository read-only**. Era anche il piu completo (send/draft/read/
  search/label/filter/batch). Inutilizzabile per nuova produzione, nessun
  successore ufficiale dell'autore.
- `marlinjai/email-mcp`: unificato Gmail+Outlook+iCloud+IMAP, OAuth2 per
  Gmail/Outlook, app-password per iCloud. Solo 11 stelle, 8 fork, ultimo
  release v1.2.7 marzo 2026. Promettente ma molto piccolo — rischio bus
  factor 1.
- `codefuturist/email-mcp`: IMAP+SMTP generico, no API native. Funziona ma
  perde feature (label Gmail, cartelle Outlook con regole)
- `mpalermiti/outlook-mcp`: solo Outlook personali, no account aziendali
  Microsoft 365 Business
- `Abhishek-Aditya-bs/Outlook-MCP-Server`: usa `pywin32` e Outlook desktop,
  richiede Windows e Outlook installato. Non scala
- Outlook aziendale e gia coperto da `Softeria/ms-365-mcp-server` (fonte 2) —
  da preferire per quel canale

**Funzionalita realisticamente disponibili**

- Lettura messaggi: si (tutti i candidati)
- Allegati: download base64 — funziona ma su mailbox grosse e lento
- Etichette/cartelle: parziale (Gmail label OK, Outlook folder OK ma regole
  no)
- Ricerca: Gmail API e Graph hanno operatori potenti, IMAP search e poverissimo
- Send/reply/forward: tecnicamente possibile ma fuori scope per noi (siamo in
  lettura)
- Watch real-time: nessuno lo implementa decentemente

**Auth**

- Gmail: OAuth 2.0 con consent del singolo utente. Per scope `gmail.readonly`
  serve verifica app Google se >100 utenti
- Outlook personale: OAuth Microsoft account personale
- Outlook 365 Business: OAuth Azure AD (stesso flow della fonte 2)
- IMAP fallback: user/password o app-password (Gmail richiede app-password
  con 2FA, iCloud uguale)

**Limiti noti**

- Gmail API quota: 1 miliardo di unita/giorno per progetto, 250 unita/sec per
  utente. Una `messages.get` costa 5 unita, quindi ~50 msg/sec/utente. Per
  scandagliare una mailbox di 50.000 messaggi servono ~17 min — accettabile
- Allegati 25 MB max per messaggio Gmail
- Graph email: cap globali della fonte 2
- Mailbox grosse (>100.000 messaggi): paginazione lenta, alto rischio di
  throttle a meta scansione
- IMAP: nessuna garanzia di ordine stabile, nessun cursor incrementale
  affidabile

**Costo**

- Gmail API: gratuita
- Graph API: gratuita
- Verifiche OAuth Google: gratuita per non-sensitive; gli scope email sono
  spesso classificati sensitive

**Setup tipico per il cliente**

- Gmail: come fonte 1 ma con scope diversi. **Probabile necessita di
  verifica OAuth** se Workspace > qualche decina utenti e si vogliono scope
  email
- Outlook 365: come fonte 2, ma con scope `Mail.Read` aggiunti
- Outlook personali / IMAP: app-password per ogni utente — gestionalmente
  insostenibile su 30-50 utenti

**Alternative**

- Gmail API Python SDK + script custom: l'approccio piu robusto. Permette
  paginazione incrementale, retry intelligenti, throttle awareness
- Microsoft Graph SDK per Outlook 365 (gia richiesto dalla fonte 2)
- Export `.mbox` (Gmail Takeout) o `.pst` (Outlook export) come last resort
  per scandagliamento one-shot

**Verdetto v1**: **Parziale**. Non ci affidiamo a un singolo MCP email
community. Per la v1:

- **Outlook 365 aziendale**: passa per `Softeria/ms-365-mcp-server` (gia
  presente per fonte 2). Niente MCP email separato
- **Gmail aziendale (Workspace)**: script custom basato su Gmail API SDK,
  esposto come MCP minimale interno se serve. Non riusiamo `GongRzhe`
  (archiviato) ne `marlinjai` (troppo piccolo)
- **Mailbox personali / IMAP misto**: escluso dalla v1, documentare il
  vincolo nel manuale Custode

---

### 4. NAS / cartelle di rete locali (SMB/NFS, percorsi montati)

**Quadro generale**

Due approcci possibili:

**Approccio A — Filesystem MCP ufficiale su path montato (raccomandato)**

- URL: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- **MCP reference ufficiale, mantenuto da Anthropic** (uno dei 7 server
  attualmente attivi)
- Read, write, edit, move, search ricorsivo glob, list directory, metadata,
  tree JSON
- Access control: directory consentite via CLI o protocol Roots
- Multi-piattaforma (Windows/macOS/Linux), via NPX o Docker
- **Limite**: non e file watcher, e snapshot-based. Per "rilevare modifiche"
  serve poll
- Funziona perfettamente su path montati: `/Volumes/NAS/`, `/mnt/share/`,
  `Z:\` — il MCP non sa che sotto c'e SMB/NFS
- Permessi: il MCP rispetta i permessi dell'OS sottostante. Se il consulente
  monta come `valentino`, vede quello che vede `valentino`

**Approccio B — MCP SMB nativo**

- `natan04/mcp-smb-server`: **1 commit, 1 star, 1 fork, no release**. Solo
  read (`list_directory`, `read_file` con max 8KB per default). Non
  production-ready.
- "SMB Server" su mcpmarket / lobehub: progetti commerciali/prototipali, no
  community verificabile
- Nessun MCP NFS dedicato trovato

**Auth (approccio A)**

- Demandata al sistema operativo: il consulente fa `mount.cifs` o
  `mount_smbfs` o mappa drive in Finder/Esplora Risorse fornendo
  user/password Active Directory o credenziali NAS
- Il MCP non vede credenziali

**Auth (approccio B, se mai serve)**

- Credenziali SMB via env var (NTLM)
- Nessuna gestione Kerberos
- Limite NFS: nessuno

**Limiti noti**

Approccio A:
- File grossi (>100 MB) sono pesanti da leggere completamente — usare
  `head`/`tail` o saltare in scansione (gestito a livello agente)
- Latenza SMB su WAN: scansionare un NAS da casa via VPN e lento
- Caratteri speciali e nomi file con encoding strani: gestiti, ma testare su
  cartelle "anziane"
- Path piu lunghi di 260 char su Windows: storico mal di testa

Approccio B:
- Vedi sopra: prototipale, no write, no search ricorsivo decente

**Costo**

- Zero. Sia il Filesystem MCP ufficiale sia mount SMB/NFS sono gratis.

**Setup tipico per il cliente**

1. Cliente fornisce a Valentino: indirizzo NAS, share name, credenziali
   read-only dedicate (es. `consulenza-readonly`)
2. Valentino monta la share sulla sua workstation:
   - macOS: `mount_smbfs //user:pass@nas/share /Volumes/NAS-Cliente`
   - Windows: `net use Z: \\nas\share /user:user pass`
   - Linux: `mount -t cifs //nas/share /mnt/nas-cliente -o
     username=user,password=pass`
3. Filesystem MCP avviato con `/Volumes/NAS-Cliente` (o equivalente) come
   directory consentita

Tempo realistico: 15-30 min se l'IT cliente fornisce credenziali dedicate;
zero se il NAS e gia accessibile via VPN/LAN.

**Alternative**

- `rclone` per copia locale read-only (mirroring incrementale), poi
  Filesystem MCP sulla copia. Utile per NAS lenti o instabili
- `rsync` snapshot
- Script Python con `smbprotocol` se serve programmaticamente

**Verdetto v1**: **Incluso via mount locale + Filesystem MCP ufficiale**.
Esplicitamente **escludere MCP SMB nativi** dalla v1: troppo immaturi.
Documentare nel manuale Custode quali credenziali fornire al consulente.

---

### 5. Server interno (SSH / SFTP / condivisione di rete LAN)

**Quadro generale**

I MCP SSH esistenti sono pensati per **esecuzione comandi remoti** (devops,
amministrazione sistemi), non per "scansiona tutti i documenti su questo
file server". Funzionano per il caso "leggi `/etc/nginx/sites-enabled/`" ma
non per "estrai i 5.000 PDF nella cartella `/srv/documenti/`".

**Candidati esaminati**

- `classfang/ssh-mcp-server` (`@fangjunjie/ssh-mcp-server` su NPM):
  - ~470 stelle, 64 fork, ultimo release v1.8.0 a maggio 2026
  - Tool: execute-command, upload, download, list-servers
  - Auth: password, private key (con passphrase), SSH agent,
    keyboard-interactive (2FA)
  - Whitelist/blacklist comandi via regex
  - Riutilizza `~/.ssh/config`
  - Modalita exec (con SFTP) e shell (per bastion host)
  - **Limite chiave**: no enumeration ricorsiva intelligente, no streaming
    file grossi, no rate limit interno
- `veithly/ssh-client-mcp`, `mixelpixx/SSH-MCP`, `tufantunc/ssh-mcp`,
  `gradyyoung/sftp-ssh-mcp`, `mcp-server-ssh` su npm (Feb 2026): tutti simili,
  varianti per Windows / serial / jump host / port forwarding. Nessuno
  chiaramente superiore a classfang

**Funzionalita realisticamente disponibili**

- Lettura: esegui `find /srv/docs -type f` e poi `cat`/SFTP download uno per
  uno — funziona ma e lento e fragile su volumi >qualche centinaio di file
- Scrittura: si ma fuori scope
- Watch: no
- Batch: no (un comando alla volta)

**Auth**

- Tutta lato consulente: chiave SSH dedicata, eventualmente passphrase in
  agent
- Niente OAuth, niente service account "cloud"

**Limiti noti**

- Modello "exec command" e mal adatto a scansione file: ogni `cat` apre una
  connessione, latenza alta su WAN
- SFTP funziona ma i MCP non lo usano in modo intelligente (no resume, no
  parallelo per default)
- Nessun rate limit interno: rischio di saturare il server (e.g. find
  ricorsivo su FS con milioni di inode)
- Whitelist comandi: utile per sicurezza ma deve essere configurata bene per
  non bloccare la scansione

**Costo**

- Zero

**Setup tipico per il cliente**

1. IT cliente crea account read-only sul server (es. `audit-consulenza`)
2. Genera coppia chiavi, aggiunge la public key a `~audit-consulenza/.ssh/
   authorized_keys`
3. Apre porta 22 verso Valentino (o richiede VPN gia in essere)
4. Fornisce a Valentino: hostname, username, private key, eventuale jump
   host
5. Valentino configura `~/.ssh/config`, il MCP la riusa

Tempo realistico: 20-40 min. Spesso il blocker e politica firewall, non il
setup tecnico.

**Alternative (raccomandate per la v1)**

- **Script custom Python `paramiko` o `asyncssh`**:
  - Enumerazione ricorsiva veloce (un `find` + parsing in streaming)
  - SFTP download parallelo con throttle
  - Resume su errori
  - Logging strutturato
- `rsync` over SSH per sync incrementale di una cartella documenti su locale,
  poi Filesystem MCP sulla copia (stesso pattern della fonte 4)
- `sshfs` per montare il filesystem remoto e poi Filesystem MCP: comodo ma
  lento e fragile su WAN

**Verdetto v1**: **Script custom raccomandato come default**. Gli MCP SSH
esistenti vanno bene per "guarda questo singolo file di config" ma non per
scandagliare un file server con migliaia di documenti. Pattern raccomandato:

1. Script Python che fa enumeration + SFTP download verso cartella locale di
   staging
2. Filesystem MCP sulla cartella di staging

Eventualmente `classfang/ssh-mcp-server` come strumento secondario per
ispezioni puntuali fatte dal consulente.

## Raccomandazioni implementative

Ordine di priorita per Step 2:

1. **Filesystem MCP ufficiale Anthropic** — adottare as-is. Zero lavoro di
   adapter. Copre fonte 4 (NAS via mount) e cartelle locali generiche.
2. **Wrapper script `rclone`/`rsync`/`sftp`** per portare contenuti remoti in
   staging locale, poi delegare al Filesystem MCP. Copre fonte 5 (server
   SSH/SFTP) e fonte 4 in modalita "snapshot incrementale" per NAS lenti o
   instabili.
3. **Adapter `piotr-agier/google-drive-mcp` con config wrapper nostra**.
   Vendoring opzionale (pin di versione) per evitare breakage upstream.
   Wizard CLI per il setup OAuth client GCP guidato.
4. **Adapter `Softeria/ms-365-mcp-server` con config wrapper nostra**. Stesso
   pattern. Wizard CLI per il setup Azure AD app registration. Documentare
   chiaramente cosa serve dall'admin del cliente.
5. **Script custom Gmail** (Gmail API SDK) per fonte 3 Gmail. Mailbox scan
   con cursor, batch retrieval, throttle aware. Esposto come MCP minimale
   interno con interfaccia stabile per l'agente.
6. **Outlook 365 aziendale via Softeria**: nessuno sviluppo dedicato, riusa
   adapter del punto 4.

Cosa NON scrivere noi nella v1:

- MCP SMB nativo (mount funziona, evitare reinventare la ruota)
- MCP Gmail completo (lo script copre il caso d'uso)
- MCP per gestionali italiani (escluso dalla v1 per decisione di prodotto)

## Rischi noti

Cose che probabilmente si romperanno con clienti reali. Da gestire nei
runbook del Custode e nella checklist di kick-off:

1. **OAuth verification Google e Microsoft**: per i clienti il cui IT richiede
   un'app interna con consent flow, la verifica puo richiedere settimane.
   Mitigazione: usare l'OAuth client del consulente (Valentino) registrato
   come app "internal" con scope appropriati, evitando di chiedere al cliente
   di creare la propria app.
2. **Admin consent Microsoft 365**: scope `Files.Read.All`, `Sites.Read.All`,
   `Mail.Read` richiedono Global Admin. Spesso il Custode non lo e e deve
   passare per il super-admin (consulente IT esterno del cliente). Tempo
   morto di giorni. Mitigazione: includere nel pre-kickoff la richiesta
   esplicita di chi ha il ruolo Global Admin.
3. **Throttling Microsoft Graph**: scandagliare un SharePoint con migliaia di
   documenti genera burst di chiamate. Senza retry con backoff esponenziale,
   il MCP si pianta a meta scansione. Verificare che Softeria gestisca 429 +
   `Retry-After`; se no, wrappare.
4. **Fork community che muore**: e successo a GongRzhe (archiviato). Puo
   succedere a piotr-agier o Softeria. Mitigazione: pin di versione,
   vendoring del codice del MCP nel nostro repo per i clienti production,
   monitoraggio attivita repo trimestrale.
5. **NAS con encoding nomi file legacy** (latin1, cp1252, nomi con `:` o `/`
   su SMB Windows): il Filesystem MCP gestisce UTF-8, ma su path provenienti
   da NAS vecchi puo emettere errori. Mitigazione: pre-scansione con script
   che normalizza/log degli errori prima di avviare l'agente.
6. **SSH bastion host / VPN del cliente con MFA**: il MCP SSH community
   gestisce keyboard-interactive 2FA ma in modo manuale. Per scansioni di
   ore non e accettabile. Mitigazione: chiedere al cliente un account
   dedicato senza MFA su jump host interno, oppure usare port forwarding
   stabile via VPN.
7. **Volumi grossi (>10 GB) di documenti**: nessuna fonte gestisce
   streaming efficiente. Tempi di scansione e storage staging vanno
   stimati in pre-kickoff (audit sizing). Mitigazione: documentare nel
   manuale Custode che oltre una certa dimensione serve un secondo round.
8. **Mailbox personali miste**: tipico delle PMI italiane (info@,
   amministrazione@, gmail personali del titolare). Non c'e modo pulito di
   scandagliarle tutte uniformemente. **Decisione di prodotto**: v1 copre
   solo mail aziendali ufficiali (Gmail Workspace o Outlook 365). Tutto il
   resto e Step 3 o v1.5.
9. **Compliance privacy (GDPR)**: tutti questi connettori toccano dati
   personali. Il perimetro privacy concordato in kick-off deve essere
   tradotto in filtri concreti a livello scanner (Step 2). Se il MCP non
   permette di limitare per cartella/etichetta, il filtro va a livello
   agente — peggio.
10. **Token refresh in scadenza durante una scansione lunga**: se il refresh
    token scade a meta di una scansione di 8 ore, l'agente fallisce. Tutti i
    MCP esaminati gestiscono il refresh automatico, ma ci sono edge case
    (OAuth in testing status su Google = 7 gg). Mitigazione: portare l'app
    OAuth Google in "published" anche se solo per uso interno consulenziale.

## Note finali

Questo audit copre lo stato a maggio 2026. Lo spazio MCP cambia velocemente:
re-audit ogni 3-6 mesi prima di proporre un nuovo cliente. Tutti i MCP
community vanno letti almeno superficialmente prima dell'adozione (TODO,
FIXME, issue aperte da mesi). Per ogni cliente production conviene vendorare
la versione esatta del MCP usato cosi un upstream breakage non blocca la
consegna.
