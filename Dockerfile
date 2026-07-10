FROM python:3.11-slim

# --- Dépendances système ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Go (nécessaire pour Subfinder) ---
ENV GOLANG_VERSION=1.22.5
RUN curl -sL https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

# --- Subfinder (binaire Go) ---
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# --- Outils Python (pip) ---
RUN pip install --no-cache-dir \
    sherlock-project \
    maigret \
    holehe

# --- theHarvester (pas de package pip fiable -> clone + venv dédié) ---
RUN git clone --depth 1 https://github.com/laramies/theHarvester.git /opt/theHarvester \
    && pip install --no-cache-dir -r /opt/theHarvester/requirements/base.txt \
    && ln -s /opt/theHarvester/theHarvester.py /usr/local/bin/theHarvester \
    && chmod +x /usr/local/bin/theHarvester

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
