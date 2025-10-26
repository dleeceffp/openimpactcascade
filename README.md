# OpenImpactCascade - AI-Powered Risk Assessment Platform

AI-powered risk assessment questionnaire generator with FAIR methodology, MITRE ATT&CK integration, and comprehensive safety safeguards.

---

## 🎯 Overview

OpenImpactCascade is a Flask-based web application that generates custom cybersecurity risk assessments tailored to specific industries and regions. It combines:

- **AI-generated questionnaires** based on verified threat intelligence
- **FAIR methodology** for quantitative risk analysis
- **Monte Carlo simulation** for risk distribution modeling
- **Real-time chat assistance** to guide users through assessments
- **API safeguards** for abuse prevention and compliance

---

## ✨ Key Features

### 🤖 AI-Generated Questionnaires
- Custom risk assessments based on industry and region
- Grounded in authoritative sources (MITRE ATT&CK, CISA, Verizon DBIR)
- Real-time web search for current threat intelligence
- Source verification before citation
- Transparent about data limitations

### 📊 FAIR Risk Analysis
- Loss Event Frequency (LEF) estimation
- Loss Magnitude (LM) estimation
- Three-point PERT estimates (min, most likely, max)
- Monte Carlo simulation (10,000+ iterations)
- Risk distribution visualization
- Percentile-based risk reporting

### 💬 Interactive Chat Assistant
- Context-aware help for each question
- Industry and region-specific guidance
- Practical examples and explanations
- Conversational interface using Claude Sonnet 4
- Remembers conversation history

### 🛡️ Safety & Compliance
- User tracking with cryptographic hashing
- API call logging for abuse investigation
- Anthropic safeguards compliance
- Privacy-preserving minimal logging
- See **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)** for details

### 🎨 Responsive Design
- Desktop: Persistent chat sidebar
- Mobile: Collapsible assistant with floating button
- Professional risk assessment interface
- Real-time validation and feedback

---

## 📁 Project Structure

```
OpenImpactCascade/
├── flask_app_chat.py              # Main Flask application with chat
├── ai_question_generator.py       # AI questionnaire generator (CLI version)
├── simulation.py                  # Monte Carlo simulation engine
├── user_tracking.py               # User tracking & API safeguards
├── investigate_abuse.py           # Abuse investigation utility
├── templates/
│   ├── home.html                  # Landing page
│   ├── generate.html              # Question generation form
│   ├── questionnaire_chat.html    # Interactive questionnaire with chat
│   ├── results.html               # Analysis results
│   └── error.html                 # Error page
├── generated/                     # Generated questionnaires saved here
├── logs/
│   └── api_calls/                 # API call logs (JSONL format)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── SAFEGUARDS_README.md          # Detailed safeguards documentation
└── flask_readme.md                # Additional Flask documentation
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
flask>=3.0.0
anthropic>=0.18.0
numpy>=1.24.0
scipy>=1.11.0
python-dotenv>=1.0.0
```

### 2. Set Up API Key

Get your API key from https://console.anthropic.com

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY='your-api-key-here'

# Option 2: .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env
```

### 3. Create Directories

```bash
mkdir -p templates generated logs/api_calls
```

### 4. Run the Application

**Development:**
```bash
export FLASK_ENV=development
python flask_app_chat.py
```

**Production:**
```bash
export FLASK_ENV=production
export SECRET_KEY='your-secure-secret-key'
gunicorn -w 4 -b 0.0.0.0:8080 flask_app_chat:app
```

Access at: **http://localhost:8080**

---

## 📖 User Guide

### Workflow

1. **Home** → Select "AI-Generated Questionnaire"
2. **Generate** → Choose industry and region (20-40 seconds)
3. **Complete** → Answer questions with AI chat assistance
4. **Analyze** → View Monte Carlo simulation results
5. **Adjust** → Modify controls to see risk reduction impact

### Example Session

```
1. Select: Healthcare / Canada
   ↓
2. AI generates questionnaire based on:
   - Canadian threat landscape
   - Healthcare-specific attacks
   - Verified CISA/ACSC advisories
   - MITRE ATT&CK techniques
   ↓
3. Answer questions with chat help:
   - "How to estimate ransomware frequency?"
   - "What costs to include in data breach?"
   ↓
4. View results:
   - Expected Annual Loss: $1,250,000
   - 90th percentile: $3,500,000
   - Risk reduction scenarios
```

### Chat Assistant Usage

**Quick Help Buttons** (context-aware):
- For frequency questions: "How to estimate frequency?"
- For magnitude questions: "What costs to include?"
- For controls: "How to improve security?"

**Chat Examples:**
```
You: "What's a typical ransomware frequency for hospitals?"
AI: For Canadian healthcare organizations with moderate security...

You: "Should I include reputation damage in the cost?"
AI: Yes! Reputation costs for healthcare breaches typically include...

You: "How does MFA reduce my risk?"
AI: Multi-factor authentication reduces likelihood by preventing...
```

---

## 🔧 API Endpoints

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| GET | `/generate` | Questionnaire generation form |
| POST | `/generate` | Generate questionnaire (requires industry, region) |
| GET | `/questionnaire` | Display generated questionnaire |
| POST | `/analyze` | Run Monte Carlo simulation |
| POST | `/chat/assist` | AI chat assistance (AJAX) |
| POST | `/recalculate` | Recalculate with adjusted controls (AJAX) |
| GET | `/download/<filename>` | Download questionnaire JSON |
| GET | `/health` | Health check |

### Request Examples

**Generate Questionnaire:**
```bash
curl -X POST http://localhost:8080/generate \
  -F "industry=Healthcare" \
  -F "region=Canada" \
  -F "organization_size=500 employees"
```

**Chat Assistance:**
```bash
curl -X POST http://localhost:8080/chat/assist \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How to estimate ransomware frequency?",
    "context": {
      "question_type": "pert_estimate",
      "fair_component": "LEF",
      "industry": "Healthcare",
      "region": "Canada"
    },
    "history": []
  }'
```

---

## 🛡️ Safety & Safeguards

### User Tracking (Implemented)

The application implements Anthropic's recommended safeguards:

**What's Tracked:**
- ✅ Session-based user IDs (evaluation mode)
- ✅ Cryptographically hashed IDs (SHA-256)
- ✅ API call logs (timestamp, type, model)
- ✅ Minimal metadata (industry, region)

**What's NOT Tracked:**
- ❌ Prompts or responses
- ❌ User account information
- ❌ Personal identifiable information (PII)

**Benefits:**
- Respond to Anthropic abuse complaints
- Investigate violations without storing user data
- Maintain privacy while enabling accountability

**For Details:** See **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)**

### Current Mode: Evaluation

The system generates random session-based user IDs:
- Format: `eval-user-{random-12-chars}`
- New ID per application start
- Allows testing without real user accounts

### Production Ready

When integrating with user registration:
1. Update `flask_app_chat.py` to use real user IDs
2. Pass IDs from your auth system
3. Maintain hashing and logging
4. See SAFEGUARDS_README for migration guide

---

## 💰 Cost Analysis

### Anthropic API Costs (Claude Sonnet 4)

**Per Request:**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Typical Usage:**

| Action | Tokens | Cost |
|--------|--------|------|
| Questionnaire Generation | ~5,600 | $0.05-0.15 |
| Chat Message | ~1,200 | $0.01-0.02 |
| Analysis (local) | 0 | $0.00 |

**Monthly Estimates:**

| Volume | Questionnaires | Chat | Total/Month |
|--------|---------------|------|-------------|
| Small | 10 | 100 | $1.50-2.50 |
| Medium | 100 | 1,000 | $15-25 |
| Large | 1,000 | 10,000 | $150-250 |

**Notes:**
- Monte Carlo simulation runs locally (no API cost)
- User tracking adds minimal API overhead (~0.1%)
- Web search for verification included in generation time
- Retries (if needed) may increase costs by 2-3x

### Cost Optimization Tips

1. **Cache questionnaires**: Store generated questions for common industry/region combinations
2. **Batch generation**: Pre-generate popular combinations during off-peak hours
3. **Rate limiting**: Limit free users to prevent abuse
4. **Session management**: Clean up old sessions to reduce storage

---

## 🔐 Security Best Practices

### API Key Protection
- ✅ Never commit API keys to version control
- ✅ Use environment variables or `.env` files
- ✅ Rotate keys periodically
- ✅ Use different keys for dev/staging/prod

### Session Security
- ✅ Strong random secret key in production
- ✅ HTTPS only (never HTTP)
- ✅ Secure cookie flags (HttpOnly, Secure, SameSite)
- ✅ Session timeout (30-60 minutes)

### Input Validation
- ✅ All form inputs validated
- ✅ Industry/region whitelisted
- ✅ PERT values range-checked
- ✅ XSS protection via template escaping

### API Safeguards
- ✅ User tracking enabled
- ✅ API call logging active
- ✅ Hashed IDs passed to Anthropic
- ✅ Investigation tools ready

### Log Security
- ✅ Restrict log file access
- ✅ No PII in logs
- ✅ Regular log rotation
- ✅ Encrypted at rest (recommended)

---

## 📊 Monitoring & Operations

### Health Monitoring

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "ai_enabled": true
}
```

### Log Locations

| Log Type | Location | Format |
|----------|----------|--------|
| API calls | `./logs/api_calls/YYYY-MM-DD_api_calls.jsonl` | JSONL |
| Application | stdout/stderr | Text |
| Flask | Flask console | Text |

### Investigating Issues

**Check API call logs:**
```bash
# View today's API calls
tail -f ./logs/api_calls/$(date +%Y-%m-%d)_api_calls.jsonl

# Search by user ID
python investigate_abuse.py --user-id eval-user-abc123

# Get user statistics
python investigate_abuse.py --user-id eval-user-abc123 --stats
```

**Check for errors:**
```bash
# If JSON parsing fails, check debug file
cat json_error_debug.json

# Check Flask logs
tail -f /path/to/flask.log
```

---

## 🚀 Deployment

### Docker

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p generated logs/api_calls

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "flask_app_chat:app"]
```

**Build and run:**
```bash
docker build -t openimpactcascade .
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY='your-key' \
  -e SECRET_KEY='your-secret' \
  -v $(pwd)/logs:/app/logs \
  openimpactcascade
```

### Google Cloud Run

```bash
# Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/openimpactcascade

# Deploy
gcloud run deploy openimpactcascade \
  --image gcr.io/$PROJECT_ID/openimpactcascade \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY='your-key',SECRET_KEY='your-secret' \
  --memory 1Gi \
  --timeout 300
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | API key from console.anthropic.com |
| `SECRET_KEY` | Yes (prod) | - | Flask session secret (generate with `openssl rand -hex 32`) |
| `FLASK_ENV` | No | production | `development` or `production` |
| `PORT` | No | 8080 | Port to run application on |

---

## 🧪 Testing

### Manual Testing

```bash
# Test questionnaire generation
python ai_question_generator.py

# Test user tracking
python user_tracking.py

# Test abuse investigation
python investigate_abuse.py --user-id eval-user-test
```

### Integration Testing

```bash
# Start the app
python flask_app_chat.py

# In another terminal:
# Test health endpoint
curl http://localhost:8080/health

# Test questionnaire generation
curl -X POST http://localhost:8080/generate \
  -F "industry=Healthcare" \
  -F "region=Canada"

# Check logs
ls -la ./logs/api_calls/
```

---

## 🐛 Troubleshooting

### Common Issues

**"ANTHROPIC_API_KEY environment variable must be set"**
```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set it
export ANTHROPIC_API_KEY='your-key-here'
```

**JSON Parsing Errors**
- The AI occasionally generates invalid JSON
- App retries up to 3 times with adjusted parameters
- Check `json_error_debug.json` for details
- Try a different industry/region combination

**Long Generation Times (20-40 seconds)**
- **This is normal!** The AI is:
  - Searching threat intelligence sources
  - Verifying advisory content
  - Cross-referencing MITRE ATT&CK
  - Researching documented incidents
- Shows progress messages during generation

**Chat Assistant Not Working**
```bash
# Check if AI is enabled
curl http://localhost:8080/health

# Check browser console for errors
# Verify API key is set
# Check Flask logs for exceptions
```

**Session Cookie Warnings**
- Set `SECRET_KEY` in production:
  ```bash
  export SECRET_KEY=$(openssl rand -hex 32)
  ```

**Log Files Not Created**
```bash
# Ensure directory exists
mkdir -p ./logs/api_calls

# Check permissions
chmod 755 ./logs/api_calls
```

---

## 🔄 Roadmap & Future Enhancements

### Planned Features

1. **User Authentication**
   - Registration and login system
   - Multi-tenant support
   - Team collaboration

2. **Enhanced Analytics**
   - Historical risk tracking
   - Trend analysis
   - Benchmarking against industry

3. **Advanced Controls**
   - Control effectiveness scoring
   - ROI calculations
   - Control recommendation engine

4. **Reporting**
   - PDF report generation
   - Executive summaries
   - Custom report templates

5. **API Enhancements**
   - RESTful API for integrations
   - Webhook support
   - Batch processing

6. **Performance**
   - Questionnaire caching (future optimization)
   - Faster generation with optimized prompts
   - Background processing for large analyses

---

## 📚 Documentation

### Core Documentation
- **README.md** (this file) - Main application documentation
- **SAFEGUARDS_README.md** - API safeguards and abuse prevention
- **flask_readme.md** - Additional Flask implementation details

### Code Documentation
- `ai_question_generator.py` - See docstrings for AI generation
- `simulation.py` - See docstrings for Monte Carlo analysis
- `user_tracking.py` - See docstrings for tracking system

### External Resources
- [Anthropic API Documentation](https://docs.anthropic.com)
- [FAIR Methodology](https://www.fairinstitute.org)
- [MITRE ATT&CK](https://attack.mitre.org)
- [Anthropic API Safeguards](https://support.claude.com/en/articles/9199617-api-safeguards-tools)

---

## 🤝 Contributing

### Development Setup

1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up API key: `export ANTHROPIC_API_KEY='your-key'`
6. Run tests: `python -m pytest tests/`
7. Start app: `python flask_app_chat.py`

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to all functions
- Keep functions focused and small

### Submitting Changes

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes with clear commits
3. Test thoroughly
4. Update documentation
5. Submit pull request

---

## 📄 License

[Your License Here]

---

## 📞 Support

### Getting Help

1. **Documentation**: Check this README and SAFEGUARDS_README.md
2. **Logs**: Review application and API call logs
3. **Health Check**: `curl http://localhost:8080/health`
4. **Debug File**: Check `json_error_debug.json` for parsing errors

### Reporting Issues

When reporting issues, include:
- Application version
- Environment (dev/prod)
- Steps to reproduce
- Error messages from logs
- Browser console errors (if UI issue)

### Contact

For questions about:
- **Application**: Review documentation
- **API Safeguards**: See SAFEGUARDS_README.md
- **Anthropic API**: Contact [email protected]
- **Security Issues**: Report privately to maintainers

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Start application
python flask_app_chat.py

# Check health
curl http://localhost:8080/health

# View API logs
tail -f ./logs/api_calls/$(date +%Y-%m-%d)_api_calls.jsonl

# Test user tracking
python user_tracking.py

# Investigate user
python investigate_abuse.py --user-id <user-id>

# Generate requirements
pip freeze > requirements.txt
```

### Key Files

| File | Purpose |
|------|---------|
| `flask_app_chat.py` | Main application |
| `ai_question_generator.py` | AI question generation |
| `simulation.py` | Monte Carlo simulation |
| `user_tracking.py` | User tracking & safeguards |
| `templates/questionnaire_chat.html` | Main UI |
| `SAFEGUARDS_README.md` | Abuse prevention docs |

### Important URLs

| URL | Purpose |
|-----|---------|
| http://localhost:8080 | Application home |
| http://localhost:8080/health | Health check |
| http://localhost:8080/generate | Generate questionnaire |
| https://console.anthropic.com | API key management |

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Set `ANTHROPIC_API_KEY`
- [ ] Set `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Set `FLASK_ENV=production`
- [ ] Enable HTTPS only
- [ ] Configure secure session cookies
- [ ] Set up log rotation
- [ ] Enable rate limiting
- [ ] Configure user authentication (if needed)
- [ ] Test health endpoint
- [ ] Test questionnaire generation
- [ ] Test chat assistant
- [ ] Verify user tracking logs
- [ ] Document abuse response procedure
- [ ] Update privacy policy
- [ ] Train support team

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**Status**: Production Ready (Evaluation Mode)

For detailed safeguards implementation, see **[SAFEGUARDS_README.md](SAFEGUARDS_README.md)**
