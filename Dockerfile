# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Runtime & Production Server
# ==========================================
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install system dependencies (for PyMuPDF & SQLite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY seed_demo.py ./

# Copy compiled frontend from Stage 1 into backend static mount
COPY --from=frontend-builder /app/frontend/dist ./backend/static

# Environment settings for Cloud Run
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

EXPOSE 8080

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
