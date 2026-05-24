"""
Guide contestuali "Come trovo questo dato" per i form di Scan / Build / Settings.

Pensate per consulenti non-tech: linguaggio passo-passo, esempi concreti,
niente jargon. Ogni funzione renderizza un `st.expander` con la guida
specifica per uno dei dati richiesti dai connettori.

Tutti gli expander sono **chiusi di default**: l'utente esperto non li vede,
quello nuovo li scopre quando ha bisogno.
"""

from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------


def render_filesystem_help() -> None:
    """Guida: come trovare il path di una cartella locale."""
    with st.expander("💡 Come trovo il path della cartella del cliente?"):
        st.markdown(
            """
**Caso più comune — cartella sul tuo Mac**

1. Apri **Finder** (icona faccia blu nel Dock)
2. Naviga alla cartella documenti del cliente
   (es. `~/Documenti/Clienti/Rossetto Laminazioni`)
3. Tasto **destro** sulla cartella → tieni premuto **option (⌥)** →
   la voce "Copia" cambia in **"Copia 'NomeCartella' come pathname"** → clicca
4. Torna qui e incolla con **⌘V**

**Caso NAS aziendale**

1. Apri Finder → menu **Vai** → **Connetti al server** (⌘K)
2. Digita `smb://nas-azienda.local/share` (chiedi al cliente l'indirizzo)
3. Accedi con credenziali
4. La cartella appare sotto "Posizioni" → naviga e copia il path come sopra

**Cosa NON usare**

- Path tipo `/Users/me/Drive/...` se quello è Google Drive sincronizzato —
  meglio usare il connettore **Google Drive** nativo
- Path con permessi solo-Admin (es. `/Library/...`) — il CLI non li legge
- La root `/` o la tua Home `/Users/tuonome` — Custodia rifiuta per sicurezza
"""
        )


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------


def render_google_drive_folder_help() -> None:
    """Guida: come trovare un Folder ID di Google Drive."""
    with st.expander("💡 Come trovo il Folder ID di Google Drive?"):
        st.markdown(
            """
1. Apri https://drive.google.com nel browser
2. Accedi col tuo account (deve avere accesso al Drive del cliente —
   se il cliente ti ha invitato a una cartella condivisa, la trovi
   sotto "Condivisi con me")
3. Naviga alla cartella che vuoi scansionare
   (es. "Commerciale 2020-2025")
4. Guarda l'URL nel browser. Sarà qualcosa tipo:
   `drive.google.com/drive/folders/1a2b3C4d5E6F-_xYz789...`
5. Quel pezzo lungo dopo `/folders/` è il **folder ID**.
   Copialo e incolla qui sotto.

NON copiare tutto l'URL, solo il folder ID.
"""
        )


def render_google_drive_credentials_help() -> None:
    """Guida: come ottenere le credenziali OAuth Google."""
    with st.expander("💡 Come ottengo le credenziali Google (una tantum)?"):
        st.markdown(
            """
Custodia ha bisogno di un file `client_secrets.json` di Google Cloud
per accedere a Drive. Si crea **una volta sola** e funziona per tutti
i clienti.

**Passi:**

1. Vai su https://console.cloud.google.com
2. Crea un nuovo progetto (es. "Custodia Consulenza")
3. Menu in alto a sinistra → **API e servizi** → **Credenziali**
4. **+ CREA CREDENZIALI** → **ID client OAuth** →
   tipo **"Applicazione desktop"**
5. Dai un nome (es. "Custodia CLI") → **CREA**
6. Scarica il JSON
7. Salvalo in `~/.custodia/google-credentials.json`
   (cartella creabile a mano)
8. Imposta la variabile d'ambiente nel terminale:

```bash
export CUSTODIA_GOOGLE_CREDENTIALS_JSON="$HOME/.custodia/google-credentials.json"
```

9. Aggiungi anche allo `~/.zshrc` o `~/.bash_profile` per persistenza

Al primo Scan, Custodia ti aprirà il browser per il consenso OAuth.
Il token resta salvato in `~/.custodia/google-token.json` (chmod 600).

Guida video Google: https://developers.google.com/workspace/guides/create-credentials
"""
        )


# ---------------------------------------------------------------------------
# Outlook 365
# ---------------------------------------------------------------------------


def render_outlook_folder_help() -> None:
    """Guida: come identificare il folder Outlook."""
    with st.expander("💡 Quale folder Outlook devo indicare?"):
        st.markdown(
            """
1. Apri https://outlook.office.com (oppure outlook.live.com) col browser
2. Accedi con l'account email del cliente
3. La barra sinistra mostra le cartelle: Inbox, Posta inviata, Bozze,
   oltre alle cartelle custom che il cliente ha creato.
4. Per Custodia inserisci il NOME della cartella (es. "Inbox" o
   "Commerciale-Clienti" se ne ha una dedicata)

Default: se lasci `inbox`, scansiona l'Inbox principale.
"""
        )


def render_outlook_credentials_help() -> None:
    """Guida: come ottenere le credenziali Microsoft Graph."""
    with st.expander("💡 Come ottengo le credenziali Microsoft (una tantum)?"):
        st.markdown(
            """
Custodia usa **OAuth Microsoft Graph**. Va creato un client app
**una tantum** nel tenant Microsoft.

**Passi:**

1. Vai su https://entra.microsoft.com (o https://portal.azure.com)
2. **Microsoft Entra ID** → **Registrazioni app** → **+ Nuova registrazione**
3. Nome: "Custodia Consulenza"
4. Account types: **Account in qualsiasi directory aziendale e
   account Microsoft personali**
5. Redirect URI: tipo **"Public client/native (mobile & desktop)"** →
   URI `http://localhost`
6. **Registra**
7. Nella registrazione appena creata, **Autorizzazioni API** → **+ Aggiungi**:
   - Microsoft Graph → **Autorizzazioni delegate** → `Mail.Read`
8. Copia il **ID applicazione (client)** dall'Overview
9. Crea un file JSON in `~/.custodia/microsoft-credentials.json`:

```json
{
  "client_id": "12345678-1234-1234-1234-123456789abc",
  "tenant_id": "common",
  "authority": "https://login.microsoftonline.com/common"
}
```

10. Imposta la env var:

```bash
export CUSTODIA_MICROSOFT_CREDENTIALS_JSON="$HOME/.custodia/microsoft-credentials.json"
```

Se il cliente ha un tenant aziendale (non personale), usa il suo
Tenant ID specifico invece di "common".
"""
        )


# ---------------------------------------------------------------------------
# Fatture in Cloud
# ---------------------------------------------------------------------------


def render_fic_company_help() -> None:
    """Guida: come trovare il company ID di Fatture in Cloud."""
    with st.expander("💡 Come trovo il Company ID di Fatture in Cloud?"):
        st.markdown(
            """
1. Vai su https://app.fattureincloud.it
2. Accedi col tuo account (oppure quello del cliente se ti ha
   condiviso le credenziali — chiedi prima!)
3. Guarda l'URL del browser. Sarà tipo:
   `app.fattureincloud.it/c/12345/...`
4. Il numero dopo `/c/` è il **company ID**.
   In questo caso: **12345**
5. Incolla qui sotto.

Se il cliente ha più aziende in FIC, ognuna ha un company ID diverso.
Verifica di essere sull'azienda giusta.
"""
        )


def render_fic_credentials_help() -> None:
    """Guida: come ottenere le credenziali OAuth Fatture in Cloud."""
    with st.expander("💡 Come ottengo le credenziali FIC (una tantum)?"):
        st.markdown(
            """
**Passi:**

1. Vai su https://developers.fattureincloud.it
2. Accedi col tuo account FIC
3. **Crea una nuova app OAuth**:
   - Nome: "Custodia Consulenza"
   - Tipo: **Public Client (PKCE)**
   - Redirect URI: `http://127.0.0.1:8765/callback`
   - Scope richiesti: `entity.clients:r entity.suppliers:r issued_documents:r`
4. Salva → ottieni il **client_id**
5. Crea file `~/.custodia/fic-credentials.json`:

```json
{
  "client_id": "il-tuo-client-id",
  "client_secret": null,
  "redirect_uri_port": 8765
}
```

6. Imposta la env var:

```bash
export CUSTODIA_FIC_CREDENTIALS_JSON="$HOME/.custodia/fic-credentials.json"
```

Al primo Scan FIC, Custodia apre il browser per il consenso. Il cliente
(o tu se hai accesso) deve approvare. Token salvato in
`~/.custodia/fic-token.json`.
"""
        )


# ---------------------------------------------------------------------------
# Build / LLM provider
# ---------------------------------------------------------------------------


def render_llm_provider_help() -> None:
    """Guida: differenza tra provider anthropic e fake."""
    with st.expander("💡 Quale provider LLM scelgo?"):
        st.markdown(
            """
**Anthropic (cloud) — consigliato per uso reale**

- Costa pochi centesimi a cliente
- Estrazione di alta qualità (Claude Sonnet 4.6)
- Richiede una API key di Anthropic
- I dati passano dai server Anthropic (UE, DPA firmato, no-training)

**Passi per ottenere la API key:**

1. Vai su https://console.anthropic.com
2. Crea un account (o accedi)
3. Menu → **API Keys** → **+ Create Key**
4. Copia la chiave (formato `sk-ant-...`)
5. Nel terminale:

```bash
export CUSTODIA_ANTHROPIC_API_KEY="sk-ant-..."
```

6. Riavvia Custodia

**Fake (offline) — solo per test**

- Provider finto: legge risposte da un file YAML pre-registrato
- Utile per dimostrare il flow senza spendere API
- Non funziona su dati reali — restituisce sempre le stesse risposte
- Usato dalla demo automatica
"""
        )


# ---------------------------------------------------------------------------
# Settings — env vars setup
# ---------------------------------------------------------------------------


def render_env_vars_setup_help() -> None:
    """Guida: come impostare env vars persistenti nel terminale."""
    with st.expander("💡 Come imposto le variabili d'ambiente in modo persistente?"):
        st.markdown(
            """
Le env vars settate con `export` durano solo finché il terminale è aperto.
Per renderle persistenti, aggiungile al file di profilo della shell.

```bash
# Apri il terminale
nano ~/.zshrc   # oppure ~/.bash_profile se usi bash

# Aggiungi in fondo le righe che ti servono:
export CUSTODIA_ANTHROPIC_API_KEY="sk-ant-..."
export CUSTODIA_GOOGLE_CREDENTIALS_JSON="$HOME/.custodia/google-credentials.json"
export CUSTODIA_MICROSOFT_CREDENTIALS_JSON="$HOME/.custodia/microsoft-credentials.json"
export CUSTODIA_FIC_CREDENTIALS_JSON="$HOME/.custodia/fic-credentials.json"
export CUSTODIA_LLM_PROVIDER="anthropic"

# Salva (Ctrl+O, Invio, Ctrl+X)

# Ricarica il profilo nel terminale corrente:
source ~/.zshrc
```

Dopo questa operazione, riavvia Custodia per far rileggere le env vars.
"""
        )


__all__ = [
    "render_filesystem_help",
    "render_google_drive_folder_help",
    "render_google_drive_credentials_help",
    "render_outlook_folder_help",
    "render_outlook_credentials_help",
    "render_fic_company_help",
    "render_fic_credentials_help",
    "render_llm_provider_help",
    "render_env_vars_setup_help",
]
