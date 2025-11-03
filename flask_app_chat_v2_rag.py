"""
Flask web application for AI-powered risk assessment questionnaire generation.
VERSION 2: RAG + LLM with Web Search

Port: 8080
Code Generator ID: v2-rag
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from ai_question_generator_with_rag import AIQuestionGeneratorWithRAG
from user_tracking import get_tracker, create_api_metadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Version identifier
VERSION = "v2-rag"
PORT = 8080

# Create required directories
os.makedirs('./generated', exist_ok=True)

# Initialize AI generator with version-specific tracker
ai_generator = None
try:
    ai_generator = AIQuestionGeneratorWithRAG()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Web Search)")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")

@app.route('/')
def home():
    """Home page - choose between static or AI-generated questionnaire."""
    return render_template('home.html', 
                         ai_available=ai_generator is not None,
                         version=VERSION,
                         port=PORT,
                         description="RAG + LLM with Web Search")

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
        tracker = get_tracker(session_based=True, code_generator="v2-rag")
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

@app.route('/generate-custom', methods=['GET', 'POST'])
def generate_custom():
    """Generate a questionnaire for a user-defined risk scenario."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    if request.method == 'GET':
        # Show the custom scenario generation form
        return render_template('generate_custom.html', version=VERSION)
    
    # POST - generate the custom scenario questionnaire
    try:
        # Get form data
        industry = request.form.get('industry', '').strip()
        region = request.form.get('region', '').strip()
        risk_scenario = request.form.get('risk_scenario', '').strip()
        scenario_description = request.form.get('scenario_description', '').strip()
        org_size = request.form.get('organization_size', '').strip()
        
        # Validate required fields
        if not industry or not region or not risk_scenario:
            return render_template('error.html', 
                error="Industry, Region, and Risk Scenario are required fields"), 400
        
        # Sanitize inputs to prevent JSON issues
        risk_scenario = risk_scenario.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', '')
        risk_scenario = risk_scenario[:200]  # Limit length
        
        if scenario_description:
            scenario_description = scenario_description.replace('"', '').replace('\n', ' ').replace('\r', '')
            scenario_description = scenario_description[:500]  # Limit length
        
        if org_size:
            org_size = org_size.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', '')
            org_size = org_size[:100]
        
        logger.info(f"[{VERSION}] Generating custom scenario questionnaire for {industry} in {region}: {risk_scenario}")
        
        # Get tracker with version-specific code generator ID
        tracker = get_tracker(session_based=True, code_generator="v2-rag")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] User ID: {user_id}")
        
        # Generate custom scenario questionnaire
        questions = ai_generator.generate_custom_scenario_questionnaire(
            industry=industry,
            region=region,
            risk_scenario=risk_scenario,
            scenario_description=scenario_description if scenario_description else None,
            organization_size=org_size if org_size else None,
            user_id=user_id,
            max_retries=2
        )
        
        # Save to file with custom scenario indicator
        filename = save_questionnaire(questions, industry, region, VERSION, custom_scenario=risk_scenario)
        
        # Store filename and params in session
        session['questionnaire_filename'] = filename
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'risk_scenario': risk_scenario,
            'scenario_description': scenario_description,
            'organization_size': org_size,
            'generation_mode': 'custom_scenario',
            'generated_at': datetime.now().isoformat(),
            'version': VERSION
        }
        
        logger.info(f"[{VERSION}] Successfully generated custom scenario questionnaire, saved to {filename}")
        
        # Redirect to the questionnaire page
        return redirect(url_for('questionnaire'))
        
    except json.JSONDecodeError as e:
        logger.error(f"[{VERSION}] JSON parsing error: {e}")
        return render_template('error.html', 
            error=f"Failed to generate valid questionnaire. The AI response could not be parsed. Please try again."), 500
    
    except Exception as e:
        logger.error(f"[{VERSION}] Generation error: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"An error occurred while generating the questionnaire: {str(e)}"), 500

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
        tracker = get_tracker(session_based=True, code_generator="v2-rag")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] Chat request from {user_id}: {user_message[:50]}...")
        
        # Generate response using Claude with RAG grounding
        response = generate_chat_response(user_message, context, user_id)
        
        return jsonify({
            'response': response,
            'version': VERSION
        })
        
    except Exception as e:
        logger.error(f"[{VERSION}] Error in chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def generate_chat_response(user_message: str, context: Dict, user_id: str) -> str:
    """Generate chat response using Claude with RAG grounding."""
    import anthropic
    from vertex_rag_complete import get_rag_engine
    
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    # Get RAG engine and retrieve grounding context
    rag_engine = get_rag_engine(enable_fallback=True)
    rag_contexts = []
    
    if rag_engine.enabled:
        try:
            rag_contexts = rag_engine.retrieve_coaching_context(
                user_question=user_message,
                industry=context.get('industry', 'General'),
                region=context.get('region', 'Global'),
                fair_component=context.get('fair_component'),
                max_results=3
            )
            logger.info(f"[{VERSION}] Retrieved {len(rag_contexts)} RAG contexts")
        except Exception as e:
            logger.warning(f"[{VERSION}] RAG retrieval failed: {e}")
    
    # Build system prompt with RAG grounding
    system_prompt = """You are a cybersecurity risk assessment coach helping users complete FAIR-based risk assessments.

Your role:
- Help users understand FAIR methodology (Loss Event Frequency and Loss Magnitude)
- Guide them in making realistic estimates based on their industry and organization
- Provide context about relevant threats and controls
- Use both the grounding context provided AND web search for current information

When grounding context is provided, prioritize it as authoritative but supplement with web search for current events.

Be concise, practical, and supportive."""
    
    # Build user prompt with RAG context
    prompt_parts = []
    
    # Add RAG grounding context if available
    if rag_contexts:
        formatted_context = rag_engine.format_context_for_prompt(rag_contexts, max_length=3000)
        prompt_parts.append(formatted_context)
        prompt_parts.append("\n---\n")
    
    prompt_parts.append(f"User question: {user_message}")
    
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
    tracker = get_tracker(session_based=True, code_generator="v2-rag")
    tracker.log_api_call(
        user_id=original_user_id,
        hashed_user_id=api_metadata['user_id'],
        api_type='chat_assist',
        model='claude-sonnet-4-20250514',
        request_id=message.id,
        metadata={
            'version': VERSION,
            'has_context': bool(context),
            'rag_contexts_retrieved': len(rag_contexts),
            'rag_enabled': rag_engine.enabled
        }
    )
    
    return message.content[0].text

def save_questionnaire(questions: Dict, industry: str, region: str, version: str, custom_scenario: str = None) -> str:
    """Save questionnaire to file and return filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_industry = industry.replace(' ', '_').replace('/', '_')[:30]
    safe_region = region.replace(' ', '_').replace('/', '_')[:30]
    
    # Add custom scenario indicator to filename if present
    if custom_scenario:
        safe_scenario = custom_scenario.replace(' ', '_').replace('/', '_')[:50]
        filename = f"{version}_custom_{safe_industry}_{safe_region}_{safe_scenario}_{timestamp}.json"
    else:
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
    from vertex_rag_complete import get_rag_engine
    
    rag_engine = get_rag_engine(enable_fallback=True)
    
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'port': PORT,
        'ai_available': ai_generator is not None,
        'approach': 'RAG + LLM with Web Search',
        'rag_enabled': rag_engine.enabled,
        'rag_status': rag_engine.get_status()
    })

if __name__ == '__main__':
    print("="*60)
    print(f"Starting Flask App - {VERSION}")
    print("="*60)
    print(f"Approach: RAG + LLM with Web Search")
    print(f"Port: {PORT}")
    print(f"Code Generator ID: v2-rag")
    print(f"User ID Format: eval-v2-rag-XXXXXXXXXXXX")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=PORT)
