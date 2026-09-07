# Lightweight Perchance proxy: camoufox (Firefox) solves Cloudflare briefly,
# hrequests handles the rest. Aimed at Render free tier.
FROM python:3.11-slim

# System libs needed by Firefox/camoufox headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libx11-xcb1 libasound2 libdbus-glib-1-2 libxt6 \
    libxtst6 libxrender1 libxi6 libgl1 libegl1 fonts-liberation \
    ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the camoufox browser at build time (so first request is faster).
RUN python -m camoufox fetch || true

COPY . .

ENV PORT=8000
EXPOSE 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
