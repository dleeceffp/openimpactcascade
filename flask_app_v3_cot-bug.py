"""
Flask web application for AI-powered risk assessment questionnaire generation.
VERSION 3: RAG + Chain of Thought
Port: 8888
User ID Prefix: COT-
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from ai_question_generator_with_rag_cot import AIQuestionGeneratorWithRAGAndCoT
from user_tracking import get_tracker, create_api_metadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-v3-cot-8888')

# Version identifier
VERSION = "v3-cot"
PORT = 8888
USER_ID_PREFIX = "COT-"

# Token cost tracking (Claude Sonnet 4 pricing as of 2024)
COST_PER_1K_INPUT_TOKENS = 0.003  # $3 per million input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.015  # $15 per million output tokens

# Global tracking dictionary
usage_stats = {
    'total_requests': 0,
    'total_input_tokens': 0,
    'total_output_tokens': 0,
    'total_cost': 0.0,
    'rag_enabled_count': 0,
    'rag_sources_total': 0,
    'cot_enabled_count': 0,
    'avg_reasoning_length': 0,
    'requests': []
}

# Create required directories
os.makedirs('./generated_v3', exist_ok=True)
os.makedirs('./stats', exist_ok=True)
os.makedirs('./reasoning', exist_ok=True)

# Initialize AI generator with RAG and CoT
ai_generator = None
try:
    ai_generator = AIQuestionGeneratorWithRAGAndCoT(
        enable_rag=True, 
        enable_cot=True,
        max_output_tokens=24000  # Higher limit for CoT reasoning
    )
    logger.info(f"[{VERSION}] AI Question Generator with RAG+CoT initialized successfully")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")


def calculate_cost(input_tokens: int, output_tokens: int) -> dict:
    """Calculate cost for the API call."""
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
    total_cost = input_cost + output_cost
    
    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'input_cost': round(input_cost, 6),
        'output_cost': round(output_cost, 6),
        'total_cost': round(total_cost, 6)
    }


def track_request(industry: str, region: str, org_size: str, usage_info: dict, rag_info: dict, cot_info: dict):
    """Track request metrics and costs."""
    global usage_stats
    
    usage_stats['total_requests'] += 1
    usage_stats['total_input_tokens'] += usage_info['input_tokens']
    usage_stats['total_output_tokens'] += usage_info['output_tokens']
    usage_stats['total_cost'] += usage_info['total_cost']
    
    if rag_info.get('rag_enabled'):
        usage_stats['rag_enabled_count'] += 1
        usage_stats['rag_sources_total'] += rag_info.get('rag_sources_count', 0)
    
    if cot_info.get('cot_enabled'):
        usage_stats['cot_enabled_count'] += 1
        # Update running average of reasoning length
        current_avg = usage_stats['avg_reasoning_length']
        new_length = cot_info.get('reasoning_length', 0)
        cot_count = usage_stats['cot_enabled_count']
        usage_stats['avg_reasoning_length'] = ((current_avg * (cot_count - 1)) + new_length) / cot_count
    
    request_record = {
        'timestamp': datetime.now().isoformat(),
        'version': VERSION,
        'industry': industry,
        'region': region,
        'organization_size': org_size,
        'usage': usage_info,
        'rag': rag_info,
        'cot': cot_info
    }
    
    usage_stats['requests'].append(request_record)
    
    # Save stats to file
    stats_file = f'./stats/usage_stats_{VERSION}.json'
    with open(stats_file, 'w') as f:
        json.dump(usage_stats, f, indent=2)
    
    logger.info(f"[{VERSION}] Request tracked - Tokens: {usage_info['total_tokens']}, Cost: ${usage_info['total_cost']:.6f}, RAG: {rag_info.get('rag_enabled')}, CoT: {cot_info.get('cot_enabled')}")


@app.route('/')
def home():
    """Home page with version info."""
    return render_template('home.html', 
                         ai_available=ai_generator is not None,
                         version=VERSION,
                         port=PORT)


@app.route('/stats')
def stats():
    """Display usage statistics."""
    avg_input = usage_stats['total_input_tokens'] / max(1, usage_stats['total_requests'])
    avg_output = usage_stats['total_output_tokens'] / max(1, usage_stats['total_requests'])
    avg_cost = usage_stats['total_cost'] / max(1, usage_stats['total_requests'])
    avg_rag_sources = usage_stats['rag_sources_total'] / max(1, usage_stats['rag_enabled_count'])
    
    return jsonify({
        'version': VERSION,
        'port': PORT,
        'summary': {
            'total_requests': usage_stats['total_requests'],
            'total_input_tokens': usage_stats['total_input_tokens'],
            'total_output_tokens': usage_stats['total_output_tokens'],
            'total_tokens': usage_stats['total_input_tokens'] + usage_stats['total_output_tokens'],
            'total_cost_usd': round(usage_stats['total_cost'], 4),
            'avg_input_tokens': round(avg_input, 0),
            'avg_output_tokens': round(avg_output, 0),
            'avg_cost_per_request': round(avg_cost, 4),
            'rag_enabled_percentage': round(100 * usage_stats['rag_enabled_count'] / max(1, usage_stats['total_requests']), 1),
            'avg_rag_sources_when_enabled': round(avg_rag_sources, 1),
            'cot_enabled_percentage': round(100 * usage_stats['cot_enabled_count'] / max(1, usage_stats['total_requests']), 1),
            'avg_reasoning_length_chars': round(usage_stats['avg_reasoning_length'], 0)
        },
        'recent_requests': usage_stats['requests'][-10:]  # Last 10 requests
    })


@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate a new questionnaire using AI with RAG and CoT."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    if request.method == 'GET':
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
        
        logger.info(f"[{VERSION}] Generating questionnaire for {industry} in {region}")
        
        # Get or generate user ID with version prefix
        tracker = get_tracker(session_based=True)
        base_user_id = tracker.get_user_id()
        user_id = f"{USER_ID_PREFIX}{base_user_id}"
        
        # Generate questionnaire with RAG and CoT
        start_time = datetime.now()
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            user_id=user_id,
            max_retries=2
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract RAG information
        rag_info = {
            'rag_enabled': questions.get('metadata', {}).get('rag_grounding_enabled', False),
            'rag_sources_count': questions.get('metadata', {}).get('rag_sources_count', 0)
        }
        
        # Extract CoT information
        cot_info = {
            'cot_enabled': questions.get('metadata', {}).get('cot_reasoning_enabled', False),
            'reasoning_length': len(questions.get('metadata', {}).get('generation_reasoning', '')),
            'reasoning_quality_score': questions.get('metadata', {}).get('reasoning_quality', {}).get('score', 0)
        }
        
        # Save reasoning separately for review
        if cot_info['cot_enabled'] and 'generation_reasoning' in questions.get('metadata', {}):
            reasoning_filename = save_reasoning(
                questions['metadata']['generation_reasoning'],
                industry, region
            )
            cot_info['reasoning_filename'] = reasoning_filename
        
        # Extract token usage from response metadata if available
        response_text = json.dumps(questions)
        estimated_output_tokens = len(response_text) // 4
        
        # CoT adds significant reasoning text to output
        cot_reasoning_tokens = 0
        if cot_info['cot_enabled']:
            cot_reasoning_tokens = cot_info['reasoning_length'] // 4
            estimated_output_tokens += cot_reasoning_tokens
        
        # RAG adds context to input
        rag_context_tokens = 0
        if rag_info['rag_enabled']:
            rag_context_tokens = rag_info['rag_sources_count'] * 500
        
        estimated_input_tokens = (len(industry) + len(region) + len(org_size or '')) * 5 + rag_context_tokens
        
        # Calculate costs
        usage_info = calculate_cost(estimated_input_tokens, estimated_output_tokens)
        usage_info['duration_seconds'] = round(duration, 2)
        usage_info['cot_reasoning_tokens'] = cot_reasoning_tokens
        
        # Track the request
        track_request(industry, region, org_size, usage_info, rag_info, cot_info)
        
        # Add version and usage info to questionnaire metadata
        if 'metadata' not in questions:
            questions['metadata'] = {}
        questions['metadata']['generation_version'] = VERSION
        questions['metadata']['generation_cost_usd'] = usage_info['total_cost']
        questions['metadata']['token_usage'] = usage_info
        
        # Save to file
        filename = save_questionnaire(questions, industry, region)
        logger.info(f"[{VERSION}] save_questionnaire returned filename: {filename}")
        
        # Store in session
        session['questionnaire_filename'] = filename
        logger.info(f"[{VERSION}] Stored filename in session: {session.get('questionnaire_filename')}")
        
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'organization_size': org_size,
            'generated_at': datetime.now().isoformat(),
            'version': VERSION,
            'usage': usage_info,
            'rag': rag_info,
            'cot': cot_info
        }
        
        logger.info(f"[{VERSION}] Successfully generated questionnaire - Cost: ${usage_info['total_cost']:.6f}, RAG sources: {rag_info['rag_sources_count']}, CoT quality: {cot_info.get('reasoning_quality_score', 0):.1f}/10")
        logger.info(f"[{VERSION}] Redirecting to questionnaire route")
        
        return redirect(url_for('questionnaire'))
        
    except Exception as e:
        logger.error(f"[{VERSION}] Generation error: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"An error occurred while generating the questionnaire: {str(e)}"), 500


@app.route('/questionnaire')
def questionnaire():
    """Display the generated questionnaire."""
    filename = session.get('questionnaire_filename')
    logger.info(f"[{VERSION}] Questionnaire route - filename from session: {filename}")
    
    if not filename:
        logger.warning(f"[{VERSION}] No filename in session, redirecting to home")
        return redirect(url_for('home'))
    
    try:
        filepath = os.path.join('generated_v3', filename)
        logger.info(f"[{VERSION}] Attempting to load questionnaire from: {filepath}")
        
        if not os.path.exists(filepath):
            logger.error(f"[{VERSION}] File not found: {filepath}")
            # List files in directory for debugging
            files_in_dir = os.listdir('generated_v3') if os.path.exists('generated_v3') else []
            logger.info(f"[{VERSION}] Files in generated_v3: {files_in_dir}")
            return render_template('error.html',
                error=f"Questionnaire file not found: {filename}"), 404
        
        with open(filepath, 'r') as f:
            questions = json.load(f)
        
        logger.info(f"[{VERSION}] Successfully loaded questionnaire with {len(questions.get('questions', []))} questions")
        
        params = session.get('generation_params', {})
        
        return render_template('questionnaire.html', 
                             questions=questions,
                             params=params,
                             version=VERSION)
    except Exception as e:
        logger.error(f"[{VERSION}] Error loading questionnaire: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"Error loading questionnaire: {str(e)}"), 500


@app.route('/reasoning/<filename>')
def view_reasoning(filename):
    """View the reasoning file for a questionnaire."""
    try:
        filepath = os.path.join('reasoning', filename)
        if not os.path.exists(filepath):
            return "Reasoning file not found", 404
        
        with open(filepath, 'r') as f:
            reasoning = f.read()
        
        return f"<pre style='white-space: pre-wrap; font-family: monospace; padding: 20px;'>{reasoning}</pre>"
    except Exception as e:
        logger.error(f"[{VERSION}] Error loading reasoning: {e}")
        return "Error loading reasoning file", 500


@app.route('/health')
def health():
    """Health check endpoint."""
    rag_enabled = ai_generator and ai_generator.rag_engine and ai_generator.rag_engine.enabled
    cot_enabled = ai_generator and ai_generator.enable_cot
    
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'port': PORT,
        'user_id_prefix': USER_ID_PREFIX,
        'ai_enabled': ai_generator is not None,
        'rag_enabled': rag_enabled,
        'cot_enabled': cot_enabled,
        'total_requests': usage_stats['total_requests'],
        'total_cost_usd': round(usage_stats['total_cost'], 4),
        'rag_enabled_percentage': round(100 * usage_stats['rag_enabled_count'] / max(1, usage_stats['total_requests']), 1),
        'cot_enabled_percentage': round(100 * usage_stats['cot_enabled_count'] / max(1, usage_stats['total_requests']), 1)
    }), 200


def save_questionnaire(questionnaire: dict, industry: str, region: str) -> str:
    """Save questionnaire to file and return filename."""
    os.makedirs('generated_v3', exist_ok=True)
    
    safe_industry = industry.replace("/", "-").replace(" ", "_")
    safe_region = region.replace("/", "-").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"questions_{safe_industry}_{safe_region}_{timestamp}.json"
    filepath = os.path.join('generated_v3', filename)
    
    logger.info(f"[{VERSION}] Saving questionnaire to: {filepath}")
    logger.info(f"[{VERSION}] Questionnaire has {len(questionnaire.get('questions', []))} questions")
    
    with open(filepath, 'w') as f:
        json.dump(questionnaire, f, indent=2)
    
    # Verify file was created
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        logger.info(f"[{VERSION}] Successfully saved questionnaire: {filename} ({file_size} bytes)")
    else:
        logger.error(f"[{VERSION}] Failed to save questionnaire to {filepath}")
    
    return filename


def save_reasoning(reasoning: str, industry: str, region: str) -> str:
    """Save reasoning text to separate file for review."""
    os.makedirs('reasoning', exist_ok=True)
    
    safe_industry = industry.replace("/", "-").replace(" ", "_")
    safe_region = region.replace("/", "-").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"reasoning_{safe_industry}_{safe_region}_{timestamp}.txt"
    filepath = os.path.join('reasoning', filename)
    
    with open(filepath, 'w') as f:
        f.write("="*70 + "\n")
        f.write("CHAIN-OF-THOUGHT REASONING\n")
        f.write(f"Industry: {industry}\n")
        f.write(f"Region: {region}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("="*70 + "\n\n")
        f.write(reasoning)
    
    logger.info(f"[{VERSION}] Saved reasoning to {filepath}")
    return filename


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    logger.info(f"Starting {VERSION} on port {PORT}")
    logger.info(f"User ID Prefix: {USER_ID_PREFIX}")
    logger.info(f"RAG Enabled: {ai_generator and ai_generator.rag_engine and ai_generator.rag_engine.enabled}")
    logger.info(f"CoT Enabled: {ai_generator and ai_generator.enable_cot}")
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=PORT
    )
