"""
Flask web application for AI-powered risk assessment questionnaire generation.
VERSION 1: LLM with Web Search Only (No RAG)

Port: 8000
Code Generator ID: v1-web
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from ai_question_generator import AIQuestionGenerator
from user_tracking import get_tracker, create_api_metadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Version identifier
VERSION = "v1-websearch"
PORT = 8000

# Create required directories
os.makedirs('./generated', exist_ok=True)

# Initialize AI generator with version-specific tracker
ai_generator = None
try:
    ai_generator = AIQuestionGenerator()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (Web Search Only)")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")

@app.route('/')
def home():
    """Home page - choose between static or AI-generated questionnaire."""
    return render_template('home.html', 
                         ai_available=ai_generator is not None,
                         version=VERSION,
                         port=PORT,
                         description="LLM with Web Search Only")

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate a new questionnaire using AI."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    if request.method == 'GET':
        # Show the generation form
        return render_template('generate.html', version=VERSION)
    
    # POST - generate the questionnaire
    try:
        # Get form data
        industry = request.form.get('industry', '').strip()
        region = request.form.get('region', '').strip()
        org_size = request.form.get('organization_size', '').strip()
        
        # Validate required fields
        if not industry or not region:
            return render_template('error.html', 
                error="Industry and Region are required fields"), 400
        
        # Sanitize organization size
        if org_size:
            org_size = org_size.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', '')
            org_size = org_size[:100]
            logger.info(f"[{VERSION}] Sanitized organization size: '{org_size}'")
        
        logger.info(f"[{VERSION}] Generating questionnaire for {industry} in {region}" + 
                   (f" (org size: {org_size})" if org_size else ""))
        
        # Get tracker with version-specific code generator ID
        tracker = get_tracker(session_based=True, code_generator="v1-web")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] User ID: {user_id}")
        
        # Generate questionnaire
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            user_id=user_id,
            max_retries=2
        )
        
        # Save to file
        filename = save_questionnaire(questions, industry, region, VERSION)
        
        # Store in session
        session['questionnaire_filename'] = filename
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'organization_size': org_size,
            'generated_at': datetime.now().isoformat(),
            'version': VERSION
        }
        
        logger.info(f"[{VERSION}] Successfully generated questionnaire, saved to {filename}")
        
        return redirect(url_for('questionnaire'))
        
    except Exception as e:
        logger.error(f"[{VERSION}] Error generating questionnaire: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"Failed to generate questionnaire: {str(e)}"), 500

@app.route('/questionnaire')
def questionnaire():
    """Display the generated questionnaire with chat interface."""
    filename = session.get('questionnaire_filename')
    params = session.get('generation_params', {})
    
    if not filename:
        return redirect(url_for('home'))
    
    try:
        # Load questionnaire from file
        with open(f'./generated/{filename}', 'r') as f:
            questions = json.load(f)
        
        return render_template('questionnaire_chat.html',
                             questions=questions,
                             params=params,
                             version=VERSION)
    except FileNotFoundError:
        logger.error(f"[{VERSION}] Questionnaire file not found: {filename}")
        return render_template('error.html',
            error="Questionnaire not found. Please generate a new one."), 404
    except json.JSONDecodeError:
        logger.error(f"[{VERSION}] Invalid JSON in questionnaire file: {filename}")
        return render_template('error.html',
            error="Questionnaire file is corrupted. Please generate a new one."), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages for coaching assistance."""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get tracker with version-specific code generator ID
        tracker = get_tracker(session_based=True, code_generator="v1-web")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] Chat request from {user_id}: {user_message[:50]}...")
        
        # Generate response using Claude (no RAG in this version)
        response = generate_chat_response(user_message, context, user_id)
        
        return jsonify({
            'response': response,
            'version': VERSION
        })
        
    except Exception as e:
        logger.error(f"[{VERSION}] Error in chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def generate_chat_response(user_message: str, context: Dict, user_id: str) -> str:
    """Generate chat response using Claude (no RAG)."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    # Build context-aware prompt
    system_prompt = """You are a cybersecurity risk assessment coach helping users complete FAIR-based risk assessments.
    
Your role:
- Help users understand FAIR methodology (Loss Event Frequency and Loss Magnitude)
- Guide them in making realistic estimates based on their industry and organization
- Provide context about relevant threats and controls
- Use web search to find current, factual information when needed

Be concise, practical, and supportive."""
    
    # Build user prompt with context
    prompt_parts = [f"User question: {user_message}"]
    
    if context.get('industry'):
        prompt_parts.append(f"\nIndustry: {context['industry']}")
    if context.get('region'):
        prompt_parts.append(f"Region: {context['region']}")
    if context.get('current_question'):
        prompt_parts.append(f"Current question context: {context['current_question']}")
    
    user_prompt = "\n".join(prompt_parts)
    
    # Create API metadata with hashed user_id
    api_metadata = create_api_metadata(user_id)
    original_user_id = api_metadata.pop('_original_user_id')
    
    # Call Claude
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        temperature=0.3,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        metadata=api_metadata
    )
    
    # Log the API call
    tracker = get_tracker(session_based=True, code_generator="v1-web")
    tracker.log_api_call(
        user_id=original_user_id,
        hashed_user_id=api_metadata['user_id'],
        api_type='chat_assist',
        model='claude-sonnet-4-20250514',
        request_id=message.id,
        metadata={
            'version': VERSION,
            'has_context': bool(context)
        }
    )
    
    return message.content[0].text

def save_questionnaire(questions: Dict, industry: str, region: str, version: str) -> str:
    """Save questionnaire to file and return filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_industry = industry.replace(' ', '_').replace('/', '_')[:30]
    safe_region = region.replace(' ', '_').replace('/', '_')[:30]
    filename = f"{version}_{safe_industry}_{safe_region}_{timestamp}.json"
    
    with open(f'./generated/{filename}', 'w') as f:
        json.dump(questions, f, indent=2)
    
    return filename

@app.route('/api/download')
def download():
    """Download the current questionnaire as JSON."""
    filename = session.get('questionnaire_filename')
    if not filename:
        return jsonify({'error': 'No questionnaire available'}), 404
    
    try:
        return send_file(
            f'./generated/{filename}',
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return jsonify({'error': 'Questionnaire file not found'}), 404

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'port': PORT,
        'ai_available': ai_generator is not None,
        'approach': 'LLM with Web Search Only'
    })

if __name__ == '__main__':
    print("="*60)
    print(f"Starting Flask App - {VERSION}")
    print("="*60)
    print(f"Approach: LLM with Web Search Only (No RAG)")
    print(f"Port: {PORT}")
    print(f"Code Generator ID: v1-web")
    print(f"User ID Format: eval-v1-web-XXXXXXXXXXXX")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=PORT)
