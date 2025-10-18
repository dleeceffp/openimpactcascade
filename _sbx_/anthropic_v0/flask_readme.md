# OpenImpactCascade - Flask Web Application

AI-powered risk assessment questionnaire generator with FAIR methodology and MITRE ATT&CK integration.

## Features

- 🤖 **AI-Generated Questionnaires** - Custom risk assessments based on industry and region
- 📊 **Authoritative Sources** - Grounded in MITRE ATT&CK, CISA, Verizon DBIR, and threat intelligence
- 🎯 **FAIR Methodology** - Quantitative risk analysis with Monte Carlo simulation
- 🔍 **Real-Time Research** - Searches current threat intelligence during generation
- ✅ **Source Verification** - All advisories and statistics verified through web search

## Project Structure

```
OIC_SBX/
├── flask_app.py                    # Flask web application
├── ai_question_generator.py        # AI questionnaire generator (command-line version)
├── simulation.py                   # Monte Carlo simulation engine
├── templates/
│   ├── home.html                   # Landing page
│   ├── generate.html               # Question generation form
│   ├── questionnaire.html          # Interactive questionnaire
│   ├── results.html                # Analysis results (reuse from main.py)
│   └── error.html                  # Error page
├── generated/                      # Generated questionnaires saved here
└── requirements.txt                # Python dependencies
```

## Installation

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

### 2. Set Up Anthropic API Key

Get your API key from https://console.anthropic.com

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY='your-api-key-here'

# Option 2: .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env
```

### 3. Create Required Directories

```bash
mkdir -p templates generated
```

## Running the Application

### Development Mode

```bash
export FLASK_ENV=development
python flask_app.py
```

The application will be available at `http://localhost:8080`

### Production Mode

```bash
export FLASK_ENV=production
export SECRET_KEY='your-secure-secret-key'
gunicorn -w 4 -b 0.0.0.0:8080 flask_app:app
```

## Usage Flow

1. **Home Page** (`/`)
   - Choose AI-generated questionnaire option

2. **Generate Questionnaire** (`/generate`)
   - Select industry (Healthcare, Financial Services, etc.)
   - Select region (Canada, United States, etc.)
   - Optionally provide organization size
   - Click "Generate Questionnaire"
   - Wait 20-40 seconds while AI researches threats

3. **Complete Questionnaire** (`/questionnaire`)
   - Answer tree-based questions
   - Provide PERT estimates for frequency and magnitude
   - Submit for analysis

4. **View Results** (`/analyze`)
   - Monte Carlo simulation results
   - Risk distribution visualizations
   - MITRE ATT&CK techniques referenced
   - Adjust controls to see impact

## API Endpoints

### `GET /`
Home page with option selection

### `GET /generate`
Display questionnaire generation form

### `POST /generate`
Generate AI questionnaire
- **Form Data:**
  - `industry` (required): Industry sector
  - `region` (required): Geographic region
  - `organization_size` (optional): Organization size
- **Returns:** Redirect to `/questionnaire`

### `GET /questionnaire`
Display generated questionnaire (from session)

### `POST /analyze`
Run Monte Carlo simulation
- **Form Data:**
  - `lef_min`, `lef_mle`, `lef_max`: Loss Event Frequency estimates
  - `lm_min`, `lm_mle`, `lm_max`: Loss Magnitude estimates
  - `n_simulations`: Number of simulations (default: 10000)
- **Returns:** Results page with risk analysis

### `POST /recalculate`
Recalculate with adjusted controls (AJAX endpoint)
- **JSON Body:**
  - `original_inputs`: Original PERT values
  - `likelihood_reduction`: Percentage reduction in likelihood
  - `impact_reduction`: Percentage reduction in impact
  - `n_simulations`: Number of simulations
- **Returns:** JSON with new simulation results

### `GET /health`
Health check endpoint
- **Returns:** `{"status": "healthy", "ai_enabled": true/false}`

## Key Features

### AI Question Generation

The AI generator:
1. **Searches** for current threat intelligence (CISA, ACSC, Verizon DBIR)
2. **Verifies** all advisories and statistics through web search
3. **Cites** specific MITRE ATT&CK techniques with IDs
4. **Documents** all sources in metadata
5. **Acknowledges** limitations when data is unavailable

### Verification Requirements

To ensure factual accuracy:
- ✅ All CISA/CERT advisories verified before citation
- ✅ Advisory content checked for industry/region relevance  
- ✅ Statistics traced to authoritative sources
- ✅ MITRE ATT&CK technique IDs validated
- ✅ URLs only included if verified
- ✅ Transparent about data limitations

### Questionnaire Structure

Generated questionnaires follow this tree:

```
Industry/Region Selection
  ├─ Threat Selection (3-5 documented threats)
  │   ├─ Asset Identification
  │   ├─ Current Controls Assessment
  │   ├─ Loss Event Frequency (PERT estimate)
  │   └─ Loss Magnitude (PERT estimate)
  └─ Monte Carlo Analysis
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | API key from Anthropic Console | Yes |
| `SECRET_KEY` | Flask session secret key | Yes (prod) |
| `FLASK_ENV` | `development` or `production` | No |
| `PORT` | Port to run on (default: 8080) | No |

### Session Storage

Questionnaires are stored in Flask sessions during the user's interaction and saved to the `generated/` directory with timestamped filenames:

```
generated/questions_Healthcare_Canada_20241219_143022.json
```

## Troubleshooting

### "ANTHROPIC_API_KEY environment variable must be set"

Set your API key:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### JSON Parsing Errors

The AI may occasionally generate invalid JSON. The app includes:
- Automatic retry (up to 3 attempts)
- Temperature adjustment on retries
- Detailed error logging to `json_error_debug.json`

If errors persist:
1. Check the industry/region combination isn't too obscure
2. Review `json_error_debug.json` for the parsing issue
3. Try a different industry/region combination

### Long Generation Times

Questionnaire generation takes 20-40 seconds because:
- Searches multiple threat intelligence sources
- Verifies advisory content
- Researches industry-specific incidents
- Cross-references MITRE ATT&CK techniques

This is normal and ensures high-quality, verified output.

## Deployment

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "flask_app:app"]
```

Build and run:
```bash
docker build -t openimpactcascade .
docker run -p 8080:8080 -e ANTHROPIC_API_KEY='your-key' openimpactcascade
```

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/openimpactcascade
gcloud run deploy openimpactcascade \
  --image gcr.io/$PROJECT_ID/openimpactcascade \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY='your-key'
```

## Security Considerations

1. **API Key Protection**: Never commit API keys to version control
2. **Secret Key**: Use strong random secret key in production
3. **Input Validation**: All form inputs are validated
4. **Session Security**: Sessions are server-side only
5. **HTTPS**: Always use HTTPS in production
6. **Rate Limiting**: Consider adding rate limiting for production

## Cost Considerations

### Anthropic API Costs

For Claude Sonnet 4 (as of 2025):
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Per questionnaire generation:**
- Typical cost: $0.05 - $0.15
- With retries: Up to $0.30 (if all 3 attempts used)

**Monthly estimates:**
- 100 questionnaires/month: ~$10-15
- 500 questionnaires/month: ~$50-75
- 1000 questionnaires/month: ~$100-150

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Adding New Industries

Edit the `generate.html` template to add more industry options:

```html
<option value="New Industry">New Industry Sector</option>
```

### Customizing Questions

The AI generates questions based on the system prompt in `ai_question_generator.py`. To customize:

1. Edit `_build_system_prompt()` method
2. Modify authoritative sources list
3. Adjust verification requirements
4. Update JSON schema requirements

## License

[Your License Here]

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review generated `json_error_debug.json` for errors
3. Check application logs for detailed error traces
