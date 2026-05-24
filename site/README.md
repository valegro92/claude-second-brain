# site/ — Landing page Custodia

Sito statico pronto al deploy. Solo HTML/CSS, niente build step, niente JS framework.

## Deploy su Vercel (raccomandato, 2 minuti)

### Opzione 1 — Da terminale

```bash
npm i -g vercel
cd site/
vercel              # primo deploy, segui prompt: scope + nome progetto
vercel --prod       # deploy in produzione
```

### Opzione 2 — Da Web

1. Vai su https://vercel.com/new
2. Importa il repo `valegro92/claude-second-brain`
3. **Root Directory**: imposta a `site` (importante)
4. **Framework Preset**: lascia "Other" (è puro HTML)
5. Deploy

### Dominio custom

Una volta deployato, in Vercel Project → Settings → Domains:
1. Aggiungi `custodia.tools` (o il dominio scelto)
2. Vercel mostra i record DNS da configurare sul registrar (CNAME / A record)
3. SSL automatico, ~1-2 minuti

## Deploy alternativi

- **Netlify**: drag&drop della cartella `site/` su https://app.netlify.com/drop
- **GitHub Pages**: settings → Pages → branch `main` → folder `/site` → enable
- **Cloudflare Pages**: Connect Git → root directory `site` → no build command

## Struttura

```
site/
├── index.html      # landing page completa, single-page
├── style.css       # CSS, no framework, ~350 righe
├── favicon.svg     # favicon SVG
├── vercel.json     # config Vercel (security headers + clean URLs)
└── README.md       # questo file
```

## Modifiche al contenuto

Tutto il copy è in `index.html` direttamente (no CMS). Pricing in sezione `.pricing`, FAQ in sezione `#faq`, contatti in sezione `#contatti`.

Per cambi sostanziali, riferimento al file sorgente è `docs/commerciale/landing-page.md`.

## Verifica locale prima di deploy

```bash
# Apri il file direttamente nel browser
open site/index.html   # macOS
xdg-open site/index.html   # Linux

# Oppure server statico veloce
python3 -m http.server 8000 --directory site
# poi vai a http://localhost:8000
```

## Cosa manca per produzione

- [ ] Verifica EUIPO/UIBM marchio "Custodia" (200-500€ con consulente)
- [ ] Logo definitivo (placeholder "Custodia" wordmark in topbar — sostituire con SVG/PNG quando pronto)
- [ ] Foto/screenshot demo (oggi nessuna immagine, solo testo)
- [ ] Form di contatto vero (oggi mailto: — va bene per partire)
- [ ] OG image per condivisione social (1200x630px)
- [ ] Privacy policy + cookie policy (Iubenda 50€/anno o template free)
- [ ] Google Analytics o Plausible (opzionale)
