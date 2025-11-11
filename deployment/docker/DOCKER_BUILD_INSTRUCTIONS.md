# Docker Build Instructions - OpenImpactCascade v2-rag-enhanced

## Quick Start

### Build Image
```bash
cd c:\projects\oicdevanthropic\OIC_SBX
docker build -t oic-v2-rag:latest .
```

### Run Container
```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  oic-v2-rag:latest
```

### Access Application
```
http://localhost:8080
```

---

## Detailed Instructions

### Prerequisites

**Required:**
- Docker Desktop or Docker Engine installed
- Anthropic API key (for AI features)
- 2GB free disk space
- 512MB free RAM

**Optional:**
- Google Cloud credentials (for Vertex AI RAG)

---

## Build Process

### Step 1: Verify Files

Ensure all required files exist:

```bash
# Core chat history files
ls app/static/js/chat_sidebar.js
ls app/static/css/chat_sidebar.css
ls app/templates/partials/chat_sidebar.html

# Modified templates
ls app/templates/home.html
ls app/templates/generate_custom.html
ls app/templates/questionnaire_chat_rationale.html
ls app/templates/results.html

# Python application
ls app/flask_oic_v211.py
ls app/requirements.txt
```

### Step 2: Build Docker Image

**Basic build:**
```bash
docker build -t oic-v2-rag:latest .
```

**Build with no cache (clean build):**
```bash
docker build --no-cache -t oic-v2-rag:latest .
```

**Build with custom tag:**
```bash
docker build -t oic-v2-rag:v2.1.1 .
```

**Build with progress output:**
```bash
docker build --progress=plain -t oic-v2-rag:latest .
```

### Step 3: Verify Build

```bash
# Check image exists
docker images | grep oic-v2-rag

# Check image size (should be ~500-800MB)
docker images oic-v2-rag:latest

# Inspect image
docker inspect oic-v2-rag:latest
```

---

## Run Container

### Basic Run (Development)

```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  oic-v2-rag:latest
```

### Run with Environment File

Create `.env` file:
```env
ANTHROPIC_API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here
```

Run with env file:
```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  --env-file .env \
  oic-v2-rag:latest
```

### Run with Volume Mount (Development)

```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  -v $(pwd)/app/generated:/app/generated \
  oic-v2-rag:latest
```

### Run with Health Check

```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  --health-cmd="python -c 'import requests; requests.get(\"http://localhost:8080/\", timeout=5)'" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  oic-v2-rag:latest
```

### Run with Resource Limits

```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  --memory="1g" \
  --cpus="1.0" \
  oic-v2-rag:latest
```

---

## Verification

### Check Container Status

```bash
# Check if running
docker ps | grep oic-app

# Check logs
docker logs oic-app

# Follow logs
docker logs -f oic-app

# Check health status
docker inspect --format='{{.State.Health.Status}}' oic-app
```

### Test Application

```bash
# Test home page
curl http://localhost:8080/

# Test health endpoint (if implemented)
curl http://localhost:8080/health

# Check in browser
# Open: http://localhost:8080
```

### Verify Chat History Files

```bash
# Check files exist in container
docker exec oic-app ls -lh /app/static/js/chat_sidebar.js
docker exec oic-app ls -lh /app/static/css/chat_sidebar.css
docker exec oic-app ls -lh /app/templates/partials/chat_sidebar.html

# Check file sizes
docker exec oic-app du -h /app/static/js/chat_sidebar.js
docker exec oic-app du -h /app/static/css/chat_sidebar.css

# View file contents (first 20 lines)
docker exec oic-app head -20 /app/static/js/chat_sidebar.js
```

### Test Chat History Functionality

1. **Access application:** http://localhost:8080
2. **Open browser console:** Press F12
3. **Navigate to questionnaire**
4. **Send chat message**
5. **Check console for:**
   ```
   [ChatHistory] Initialized with 0 entries
   [ChatHistory] Added entry. Total: 1 | Page: questionnaire
   [ChatHistory] Current breakdown: {questionnaire: 1}
   ```
6. **Navigate to results page**
7. **Check console for:**
   ```
   [ChatHistory] Initialized with 1 entries
   [ChatHistory] Loaded breakdown: {questionnaire: 1}
   [Results Page] ChatHistory on load: 1 entries
   ```
8. **Run in console:**
   ```javascript
   viewChatHistory();
   getChatStats();
   ```

---

## Container Management

### Stop Container
```bash
docker stop oic-app
```

### Start Container
```bash
docker start oic-app
```

### Restart Container
```bash
docker restart oic-app
```

### Remove Container
```bash
docker stop oic-app
docker rm oic-app
```

### View Container Logs
```bash
# Last 100 lines
docker logs --tail 100 oic-app

# Follow logs
docker logs -f oic-app

# Logs since specific time
docker logs --since 10m oic-app
```

### Execute Commands in Container
```bash
# Interactive shell
docker exec -it oic-app /bin/bash

# Run Python command
docker exec oic-app python -c "print('Hello from container')"

# Check Python version
docker exec oic-app python --version

# List installed packages
docker exec oic-app pip list
```

---

## Troubleshooting

### Build Fails

**Issue:** `COPY failed: no such file or directory`

**Solution:**
```bash
# Verify you're in correct directory
pwd  # Should show: c:\projects\oicdevanthropic\OIC_SBX

# Check file exists
ls app/static/js/chat_sidebar.js

# Try absolute path in Dockerfile
COPY ./app/static/js/chat_sidebar.js /app/static/js/
```

### Container Won't Start

**Issue:** Container exits immediately

**Solution:**
```bash
# Check logs
docker logs oic-app

# Check for port conflicts
netstat -an | findstr 8080

# Try different port
docker run -d --name oic-app -p 8081:8080 -e ANTHROPIC_API_KEY="key" oic-v2-rag:latest
```

### Chat History Not Working

**Issue:** Console shows errors or history not persisting

**Solution:**
```bash
# Verify files in container
docker exec oic-app ls -la /app/static/js/
docker exec oic-app ls -la /app/static/css/
docker exec oic-app ls -la /app/templates/partials/

# Check file contents
docker exec oic-app cat /app/static/js/chat_sidebar.js | head -50

# Rebuild with no cache
docker build --no-cache -t oic-v2-rag:latest .
```

### API Key Issues

**Issue:** AI features not working

**Solution:**
```bash
# Check environment variable is set
docker exec oic-app printenv | grep ANTHROPIC

# Restart with correct key
docker stop oic-app
docker rm oic-app
docker run -d --name oic-app -p 8080:8080 -e ANTHROPIC_API_KEY="your-correct-key" oic-v2-rag:latest
```

---

## Production Deployment

### Build for Production

```bash
# Tag with version
docker build -t oic-v2-rag:v2.1.1 -t oic-v2-rag:latest .

# Push to registry (if using)
docker tag oic-v2-rag:latest your-registry/oic-v2-rag:v2.1.1
docker push your-registry/oic-v2-rag:v2.1.1
```

### Run in Production

```bash
docker run -d \
  --name oic-app \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key" \
  -e SECRET_KEY="production-secret-key" \
  --restart unless-stopped \
  --memory="2g" \
  --cpus="2.0" \
  --health-cmd="python -c 'import requests; requests.get(\"http://localhost:8080/\", timeout=5)'" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  oic-v2-rag:latest
```

### Docker Compose (Optional)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  oic-app:
    build: .
    image: oic-v2-rag:latest
    container_name: oic-app
    ports:
      - "8080:8080"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

Run with Docker Compose:
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## File Manifest Verification

### Pre-Build Checklist

```bash
# Core chat history files (REQUIRED)
[ ] app/static/js/chat_sidebar.js
[ ] app/static/css/chat_sidebar.css
[ ] app/templates/partials/chat_sidebar.html

# Modified templates (REQUIRED)
[ ] app/templates/home.html
[ ] app/templates/generate_custom.html
[ ] app/templates/questionnaire_chat_rationale.html
[ ] app/templates/results.html

# Python application (REQUIRED)
[ ] app/flask_oic_v211.py
[ ] app/ai_question_generator_v211.py
[ ] app/simulation_v211.py
[ ] app/vertex_rag_v211.py
[ ] app/user_tracking.py
[ ] app/requirements.txt

# Documentation (OPTIONAL)
[ ] app/static/js/CHAT_HISTORY_USAGE.md
[ ] app/static/js/CHAT_HISTORY_IMPLEMENTATION.md
[ ] app/static/js/CHAT_HISTORY_QUICK_REFERENCE.md
[ ] app/templates/partials/CHAT_SIDEBAR_USAGE.md
```

### Post-Build Verification Script

```bash
#!/bin/bash
# verify-build.sh

echo "Verifying Docker build..."

# Check image exists
if docker images | grep -q "oic-v2-rag"; then
    echo "✅ Image exists"
else
    echo "❌ Image not found"
    exit 1
fi

# Start container
docker run -d --name oic-test -p 8081:8080 -e ANTHROPIC_API_KEY="test" oic-v2-rag:latest

# Wait for startup
sleep 5

# Check files
echo "Checking files in container..."
docker exec oic-test ls /app/static/js/chat_sidebar.js || echo "❌ chat_sidebar.js missing"
docker exec oic-test ls /app/static/css/chat_sidebar.css || echo "❌ chat_sidebar.css missing"
docker exec oic-test ls /app/templates/partials/chat_sidebar.html || echo "❌ chat_sidebar.html missing"

# Cleanup
docker stop oic-test
docker rm oic-test

echo "✅ Verification complete"
```

---

## Summary

**Build Command:**
```bash
docker build -t oic-v2-rag:latest .
```

**Run Command:**
```bash
docker run -d --name oic-app -p 8080:8080 -e ANTHROPIC_API_KEY="your-key" oic-v2-rag:latest
```

**Access:**
```
http://localhost:8080
```

**Verify Chat History:**
```javascript
// In browser console
viewChatHistory();
getChatStats();
```

---

**Status:** ✅ Ready for Docker Build  
**Version:** v2-rag-enhanced  
**Last Updated:** November 11, 2025
