# wiki-toolkit — immagine on-premise per clienti regolamentati (Step 3).
#
# Build:
#   docker build -t wiki-toolkit:latest .
#
# Multi-stage:
#   * Stage 1 (builder): installa uv + dipendenze Python + costruisce wheel.
#   * Stage 2 (runtime): immagine slim con solo runtime + binari di sistema
#                        (Pandoc, Tesseract italiano, Poppler) e venv copiato.
#
# Dimensione attesa: ~600-800 MB (Tesseract con language pack pesa).
#
# Entry point: ``wiki`` (vedi pyproject.toml [project.scripts]).
# Volumi attesi (vedi docker-compose.yml):
#   /app/bootstrap/clients/   config + auth cliente
#   /app/_status/             output del pipeline (mai committato)
#   /app/_inbox/              drop zone del watcher
#   /app/vault/               vault del cliente (target del flush)

# ---------------------------------------------------------------- Stage 1
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# uv come package manager (Astral). Più veloce di pip, lockfile deterministico.
RUN pip install --no-cache-dir uv==0.5.*

WORKDIR /build

# Installa prima solo i metadati: maximizza la cache layer su rebuild.
COPY pyproject.toml uv.lock README.md ./

# Copia i sorgenti necessari al build del wheel (vedi
# [tool.hatch.build.targets.wheel].packages in pyproject.toml).
COPY wiki/ ./wiki/
COPY scanners/ ./scanners/
COPY extractors/ ./extractors/
COPY categorizers/ ./categorizers/
COPY reconcilers/ ./reconcilers/
COPY batch_ui/ ./batch_ui/
COPY bootstrap/ ./bootstrap/

# Crea il venv, installa dipendenze e il package stesso.
RUN uv venv /opt/venv \
    && uv sync --frozen --no-dev --extra ocr

# ---------------------------------------------------------------- Stage 2
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Pacchetti di sistema:
#   * pandoc: DOCX → markdown (extractors/docx.py)
#   * tesseract-ocr + ita: OCR italiano (extractors/pdf_ocr.py)
#   * poppler-utils: rasterizzazione PDF (pdf2image)
#   * libmagic1: python-magic per mime detection
#   * ghostscript: backup di rasterizzazione PDF
#   * ca-certificates: TLS verso API esterne (Anthropic, Bedrock)
# tini è entrypoint init minimale per gestire segnali correttamente.
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        tesseract-ocr \
        tesseract-ocr-ita \
        tesseract-ocr-eng \
        poppler-utils \
        libmagic1 \
        ghostscript \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Crea utente non-root per ridurre superficie d'attacco.
RUN useradd --create-home --shell /bin/bash --uid 1000 wiki

WORKDIR /app

# Venv del builder.
COPY --from=builder /opt/venv /opt/venv

# Sorgenti del toolkit. Copiamo tutto (no .dockerignore esclude tests/, _status/, ecc.).
COPY --chown=wiki:wiki . /app

# Crea le cartelle di runtime con i permessi giusti per l'utente non-root.
RUN mkdir -p /app/_status /app/_inbox /app/bootstrap/clients \
    && chown -R wiki:wiki /app/_status /app/_inbox /app/bootstrap/clients

USER wiki

# Entry point: tini → wiki CLI.
ENTRYPOINT ["/usr/bin/tini", "--", "wiki"]
CMD ["--help"]
