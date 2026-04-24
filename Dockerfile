# Multi-stage build: Python backend + React frontend

# Stage 1: Python backend
FROM python:3.11-slim as backend-builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Node.js for React build
FROM node:18-alpine as frontend-builder

WORKDIR /app
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 3: Final image (both backend + frontend)
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy Python source
COPY src/ src/
COPY prompts/ prompts/
COPY requirements.txt .

# Copy built React frontend
COPY --from=frontend-builder /app/build web/build

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start backend (frontend served by backend in production)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
