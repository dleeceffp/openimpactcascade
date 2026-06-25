# OpenImpactCascade v221-context-aware
# Flask-based AI-powered risk assessment platform with SQLite context storage
# Features: Chat assistant, FAIR methodology, layered controls toggle
# Port: 8080

FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies and apply security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application files
COPY app/main.py /app/
COPY app/config.py /app/
COPY app/ai_question_generator.py /app/
COPY app/simulation.py /app/
COPY app/user_tracking.py /app/
COPY app/context_storage.py /app/

# Copy shared OIC modules (oic_search — pluggable search/grounding layer)
COPY src/oic_search/ /app/lib/oic_search/

# Copy corpus module
COPY app/corpus/ /app/corpus/

# Copy cascade-archetype card library module
COPY app/cards/ /app/cards/

# Copy ONLY the compressed cascade-archetype cards (not other generated artifacts).
# Cards now live at the repo root generated/cascade_archetypes/ (moved from app/generated/).
# Detailed source flows (attack_flows/, fair_reports/) are gitignored and never shipped.
COPY generated/cascade_archetypes/ /app/generated/cascade_archetypes/

# Copy static assets directory structure
COPY app/static/ /app/static/

# Copy template files directory structure
COPY app/templates/ /app/templates/

# Create necessary directories
RUN mkdir -p /app/generated \
    && mkdir -p /app/static/js \
    && mkdir -p /app/static/css \
    && mkdir -p /app/templates/partials \
    && mkdir -p /tmp \
    && chmod 1777 /tmp

# Set environment variables
ENV FLASK_APP=main.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
# Make the shared oic_search package importable without a pip install.
# /app/lib sits alongside the app code; both are on the path.
ENV PYTHONPATH=/app/lib

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/', timeout=5)"

# Run the application using gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
