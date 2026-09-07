# Lightweight Perchance proxy: camoufox (Firefox) solves Cloudflare briefly,
# hrequests handles the rest. Runs on Google Cloud Run (set memory to 2Gi).
FROM python:3.11-slim

# System libs needed by Firefox/camoufox. camoufox crashes in pure headless
# mode inside Docker, so we run it "headed" behind Xvfb (virtual display).
# xvfb + dbus + the extra GL/X libs fix the glxtest / mozalloc_abort crash.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libx11-xcb1 libasound2 libdbus-glib-1-2 libxt6 \
    libxtst6 libxrender1 libxi6 libgl1 libegl1 libgl1-mesa-dri \
    libgtk-3-0 libpango-1.0-0 libcairo2 libdbus-1-3 \
    fonts-liberation ca-certificates wget xvfb dbus dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Give camoufox a predictable, writable cache location.
ENV HOME=/app
ENV XDG_CACHE_HOME=/app/.cache
ENV DISPLAY=:99

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the camoufox browser at build time (so first request is faster).
RUN python -m camoufox fetch || true

COPY . .

# Start a virtual display, then the server. camoufox runs headed on :99.
COPY start.sh /app/start.sh
# Normalize line endings (file may be committed with CRLF from Windows) + exec bit.
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

ENV PORT=8080
EXPOSE 8080
CMD ["/app/start.sh"]
