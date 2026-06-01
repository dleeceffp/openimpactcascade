# OpenImpactCascade v221-context-aware
# Flask-based AI-powered risk assessment platform with SQLite context storage
# Features: Chat assistant, FAIR methodology, layered controls toggle
# Port: 8080

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application files
COPY app/main.py /app/
COPY app/ai_question_generator.py /app/
COPY app/simulation.py /app/
COPY app/vertex_rag.py /app/
COPY app/user_tracking.py /app/
COPY app/context_storage.py /app/

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

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/', timeout=5)"

# Run the application
CMD ["python", "main.py"]
