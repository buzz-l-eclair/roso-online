# Python 3.12+ requis par theHarvester (dépôt upstream a bougé vers uv/pyproject).
FROM python:3.12-slim

# --- Dépendances système ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Go (nécessaire pour Subfinder et Amass) ---
ENV GOLANG_VERSION=1.22.5
RUN curl -sL https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

# --- Subfinder (binaire Go) ---
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# --- Amass (binaire Go) ---
RUN go install -v github.com/owasp-amass/amass/v4/...@master

# --- Outils Python (pip) ---
RUN pip install --no-cache-dir \
    sherlock-project \
    maigret \
    holehe

# --- uv (gestionnaire de paquets requis par theHarvester depuis sa migration
#     vers pyproject.toml + uv.lock -- pip install -r requirements/... ne
#     fonctionne plus, le dépôt ne fournit plus ce fichier) ---
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# --- theHarvester (clone + environnement uv dédié, isolé du reste) ---
RUN git clone --depth 1 https://github.com/laramies/theHarvester.git /opt/theHarvester
WORKDIR /opt/theHarvester
RUN uv sync --frozen --no-dev

# Wrapper shell : notre backend appelle `theHarvester -d ... -b ...` comme un
# binaire classique. On l'expose sous ce nom en délégant à `uv run` dans le
# bon projet, pour ne pas avoir à changer runner.py / registry.py.
RUN printf '#!/bin/sh\ncd /opt/theHarvester && uv run theHarvester "$@"\n' > /usr/local/bin/theHarvester \
    && chmod +x /usr/local/bin/theHarvester

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
