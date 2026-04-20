# ─────────────────────────────────────────────────────────────────────────────
# WasteGuard Society AI — Dockerfile
# Multi-agent waste detection system: YOLOv5 + CrewAI + Groq + Twilio WhatsApp
# ─────────────────────────────────────────────────────────────────────────────

# Python 3.10 to match the conda environment used in development
FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# OpenCV requires libsm6, libxext6, libgl1 (headless rendering)
# git is needed by YOLOv5 internals (gitpython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt requirements_crew.txt ./

# Pin ultralytics to 8.0.20 — newer versions removed the ultralytics.yolo
# subpackage that YOLOv5 depends on. Override any broader spec in requirements.txt.
RUN pip install --no-cache-dir \
    "ultralytics==8.0.20" \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements_crew.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# Create the data directory for runtime image storage from Twilio
RUN mkdir -p data

# ── Environment variables ─────────────────────────────────────────────────────
# Do NOT hardcode secrets here. Pass them at runtime:
#   docker run -p 8080:8080 --env-file .env wasteguard
# Or use docker-compose with an env_file directive.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# ── Port ──────────────────────────────────────────────────────────────────────
# Flask app runs on 8080. Map to host with: docker run -p 8080:8080 ...
# For production behind a reverse proxy (nginx/traefik), expose 80/443 there.
EXPOSE 8080

# ── Health check ─────────────────────────────────────────────────────────────
# Checks the Flask app is responding every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["python3", "app.py"]