"""
Flask web application for AI-powered risk assessment questionnaire generation.
CORRECTED VERSION - Uses file storage, NOT session cookies for questionnaires.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from ai_question_generator import AIQuestionGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Create required directories
os.makedirs('./generated', exist_ok=True)

# Initialize AI generator (will be None if API key not set)
ai_generator = None
try:
    ai_generator = AIQuestionGenerator()
    logger.info("AI Question Generator initialized successfully")
except ValueError as e:
    logger.warning(f"AI Generator not available: {e}")

@app.route('/')
def home():
    """Home page - choose between static or AI-generated questionnaire."""
    return render_template('home.html', ai_available=ai_generator is not None)

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate a new questionnaire using AI."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    if request.method == 'GET':
        # Show the generation form
        return render_template('generate.html')
    
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
        
        # Sanitize organization size to prevent JSON issues
        if org_size:
            # Remove any potentially problematic characters
            org_size = org_size.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', '')
            # Limit length to prevent very long inputs
            org_size = org_size[:100]
            logger.info(f"Sanitized organization size: '{org_size}'")
        
        logger.info(f"Generating questionnaire for {industry} in {region}" + 
                   (f" (org size: {org_size})" if org_size else ""))
        
        # Generate questionnaire with optional parameters
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            max_retries=2
        )
        
        # Save to file
        filename = save_questionnaire(questions, industry, region)
        
        # Store ONLY filename and params in session (not the full JSON)
        session['questionnaire_filename'] = filename
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'organization_size': org_size,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Successfully generated questionnaire, saved to {filename}")
        logger.info(f"Session data size: filename={len(filename)} bytes, params=~100 bytes")
        
        # Redirect to the questionnaire page
        return redirect(url_for('questionnaire'))
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return render_template('error.html', 
            error=f"Failed to generate valid questionnaire. The AI response could not be parsed. Please try again."), 500
    
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"An error occurred while generating the questionnaire: {str(e)}"), 500

@app.route('/questionnaire')
def questionnaire():
    """Display the generated questionnaire - loads from file."""
    filename = session.get('questionnaire_filename')
    params = session.get('generation_params')
    
    if not filename:
        logger.warning("No questionnaire filename in session, redirecting to home")
        return redirect(url_for('home'))
    
    # Load questionnaire from file
    filepath = os.path.join('generated', filename)
    
    if not os.path.exists(filepath):
        logger.error(f"Questionnaire file not found: {filepath}")
        return render_template('error.html', 
            error="Questionnaire file not found. Please generate a new questionnaire."), 404
    
    try:
        with open(filepath, 'r') as f:
            questions = json.load(f)
        
        logger.info(f"Loaded questionnaire from file: {filename} ({os.path.getsize(filepath)} bytes)")
        
    except Exception as e:
        logger.error(f"Error loading questionnaire: {e}")
        return render_template('error.html', 
            error=f"Error loading questionnaire: {str(e)}"), 500
    
    return render_template('questionnaire_chat.html', 
        questions=questions,
        params=params
    )

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process the questionnaire responses and run Monte Carlo analysis."""
    try:
        # Import simulation module
        from simulation import run_monte_carlo
        
        # Get form data with better error handling
        try:
            lef_min = request.form.get('lef_min')
            lef_mle = request.form.get('lef_mle')
            lef_max = request.form.get('lef_max')
            lm_min = request.form.get('lm_min')
            lm_mle = request.form.get('lm_mle')
            lm_max = request.form.get('lm_max')
            
            # Check for missing values
            if not all([lef_min, lef_mle, lef_max, lm_min, lm_mle, lm_max]):
                missing = []
                if not lef_min: missing.append('lef_min')
                if not lef_mle: missing.append('lef_mle')
                if not lef_max: missing.append('lef_max')
                if not lm_min: missing.append('lm_min')
                if not lm_mle: missing.append('lm_mle')
                if not lm_max: missing.append('lm_max')
                
                logger.error(f"Missing form fields: {missing}")
                return render_template('error.html', 
                    error=f"Missing required fields: {', '.join(missing)}. Please complete all estimate fields in the questionnaire."), 400
            
            original_inputs = {
                'lef_min': float(lef_min),
                'lef_mle': float(lef_mle),
                'lef_max': float(lef_max),
                'lm_min': float(lm_min),
                'lm_mle': float(lm_mle),
                'lm_max': float(lm_max)
            }
            
        except ValueError as e:
            logger.error(f"Invalid number format: {e}")
            return render_template('error.html', 
                error="Invalid number format. Please enter valid numbers for all estimate fields."), 400
        
        n_simulations = int(request.form.get('n_simulations', 10000))
        
        # Validate ranges
        if not (0 <= original_inputs['lef_min'] <= original_inputs['lef_mle'] <= original_inputs['lef_max']):
            logger.error(f"Invalid LEF range: {original_inputs['lef_min']}, {original_inputs['lef_mle']}, {original_inputs['lef_max']}")
            return render_template('error.html', 
                error=f"Invalid frequency estimates: min ({original_inputs['lef_min']}) ≤ most likely ({original_inputs['lef_mle']}) ≤ max ({original_inputs['lef_max']}) not satisfied"), 400
        
        if not (0 <= original_inputs['lm_min'] <= original_inputs['lm_mle'] <= original_inputs['lm_max']):
            logger.error(f"Invalid LM range: {original_inputs['lm_min']}, {original_inputs['lm_mle']}, {original_inputs['lm_max']}")
            return render_template('error.html', 
                error=f"Invalid magnitude estimates: min (${original_inputs['lm_min']:,.0f}) ≤ most likely (${original_inputs['lm_mle']:,.0f}) ≤ max (${original_inputs['lm_max']:,.0f}) not satisfied"), 400
        
        logger.info(f"Running Monte Carlo simulation with LEF: {original_inputs['lef_min']}-{original_inputs['lef_mle']}-{original_inputs['lef_max']}, LM: ${original_inputs['lm_min']}-${original_inputs['lm_mle']}-${original_inputs['lm_max']}")
        
        # Run simulation
        results = run_monte_carlo(**original_inputs, n_simulations=n_simulations)
        
        # Validate results structure
        required_keys = ['mean', 'std', 'min', 'max', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95']
        missing_keys = [key for key in required_keys if key not in results]
        
        if missing_keys:
            logger.error(f"Simulation returned invalid results. Missing keys: {missing_keys}")
            logger.error(f"Results keys: {list(results.keys())}")
            logger.error(f"Results: {results}")
            return render_template('error.html',
                error=f"Simulation error: Invalid results format. Missing: {', '.join(missing_keys)}"), 500
        
        logger.info(f"Simulation complete: Mean=${results['mean']:,.0f}, StdDev=${results['std']:,.0f}")
        
        # Get MITRE references if available - load from file
        mitre_references = None
        filename = session.get('questionnaire_filename')
        
        if filename:
            filepath = os.path.join('generated', filename)
            try:
                with open(filepath, 'r') as f:
                    questions = json.load(f)
                    
                # Extract MITRE techniques from questions
                mitre_techniques = set()
                for q_id, q_data in questions.get('questions', {}).items():
                    if 'choices' in q_data:
                        for choice in q_data['choices']:
                            if 'mitre_techniques' in choice:
                                mitre_techniques.update(choice['mitre_techniques'])
                    if 'threat_context' in q_data and 'mitre_techniques' in q_data['threat_context']:
                        mitre_techniques.update(q_data['threat_context']['mitre_techniques'])
                
                if mitre_techniques:
                    mitre_references = list(mitre_techniques)
                    logger.info(f"Found {len(mitre_references)} MITRE techniques")
                    
            except Exception as e:
                logger.warning(f"Could not load MITRE references: {e}")
        
        return render_template('results.html',
            results=results,
            original_inputs=original_inputs,
            n_simulations=n_simulations,
            mitre_references=mitre_references,
            generation_params=session.get('generation_params')
        )
        
    except (ValueError, TypeError) as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return render_template('error.html', error=f"Invalid input: {str(e)}"), 400
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"Error during analysis: {str(e)}"), 500

@app.route('/recalculate', methods=['POST'])
def recalculate():
    """Recalculate simulation with adjusted parameters."""
    try:
        from simulation import run_monte_carlo
        
        data = request.get_json()
        
        # Get parameters
        inputs = data.get('original_inputs')
        likelihood_reduction = data.get('likelihood_reduction', 0) / 100.0
        impact_reduction = data.get('impact_reduction', 0) / 100.0
        n_simulations = min(int(data.get('n_simulations', 10000)), 100000)
        
        # Apply reductions
        adjusted_inputs = {
            'lef_min': inputs['lef_min'] * (1 - likelihood_reduction),
            'lef_mle': inputs['lef_mle'] * (1 - likelihood_reduction),
            'lef_max': inputs['lef_max'] * (1 - likelihood_reduction),
            'lm_min': inputs['lm_min'] * (1 - impact_reduction),
            'lm_mle': inputs['lm_mle'] * (1 - impact_reduction),
            'lm_max': inputs['lm_max'] * (1 - impact_reduction)
        }
        
        # Run simulation
        new_results = run_monte_carlo(**adjusted_inputs, n_simulations=n_simulations)
        
        return jsonify({
            'status': 'success',
            'results': new_results
        })
        
    except Exception as e:
        logger.error(f"Recalculation error: {e}")
        return jsonify({
            'error': 'Recalculation failed',
            'details': str(e)
        }), 500

@app.route('/download/<filename>')
def download(filename):
    """Download a generated questionnaire JSON file."""
    # Security: only allow downloading files that were generated in this session
    session_filename = session.get('questionnaire_filename')
    if filename != session_filename:
        logger.warning(f"Unauthorized download attempt: {filename}")
        return "Unauthorized", 403
    
    filepath = os.path.join('generated', filename)
    if not os.path.exists(filepath):
        logger.error(f"Download file not found: {filepath}")
        return "File not found", 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/chat/assist', methods=['POST'])
def chat_assist():
    """AI chat assistant for helping with questionnaire."""
    if not ai_generator:
        return jsonify({
            'status': 'error',
            'response': 'AI assistant is not available. Please set ANTHROPIC_API_KEY.'
        }), 503
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({
                'status': 'error',
                'response': 'No message provided'
            }), 400
        
        # Build context-aware system prompt
        system_prompt = build_chat_system_prompt(context)
        
        # Build conversation history
        messages = []
        for exchange in history:
            messages.append({"role": "user", "content": exchange['user']})
            messages.append({"role": "assistant", "content": exchange['assistant']})
        messages.append({"role": "user", "content": user_message})
        
        # Call Claude API
        response = ai_generator.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,  # Shorter responses for chat
            temperature=0.7,   # More conversational
            system=system_prompt,
            messages=messages
        )
        
        assistant_response = response.content[0].text
        
        logger.info(f"Chat assist: '{user_message[:50]}...' -> '{assistant_response[:50]}...'")
        
        return jsonify({
            'status': 'success',
            'response': assistant_response
        })
        
    except Exception as e:
        logger.error(f"Chat assist error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'response': 'I apologize, but I encountered an error. Please try rephrasing your question.'
        }), 500


def build_chat_system_prompt(context):
    """Build a context-aware system prompt for the chat assistant."""
    
    base_prompt = """You are a friendly and knowledgeable risk assessment assistant helping users complete a FAIR-based cybersecurity risk questionnaire.

Your role is to:
- Explain risk assessment concepts in simple, clear language
- Help users estimate Loss Event Frequency (LEF) and Loss Magnitude (LM)
- Provide examples and guidance for their specific industry and threat
- Explain security controls and how they reduce risk
- Be encouraging and supportive - many users are new to quantitative risk analysis

Keep responses concise (2-4 paragraphs), practical, and easy to understand. Use examples when possible."""
    
    # Add context-specific guidance
    question_text = context.get('question_text', '')
    question_type = context.get('question_type', '')
    fair_component = context.get('fair_component', '')
    industry = context.get('industry', '')
    region = context.get('region', '')
    
    context_guidance = f"\n\nCurrent Context:\n- Industry: {industry}\n- Region: {region}\n"
    
    if fair_component == 'LEF':
        context_guidance += """
The user is estimating Loss Event Frequency (how often attacks occur per year).

Help them understand:
- LEF represents events per year (e.g., 0.5 = once every 2 years, 2 = twice per year)
- Min/Most Likely/Max creates a PERT distribution for uncertainty
- Consider their security controls, threat landscape, and industry trends
- Examples: "For a well-protected hospital, ransomware might occur 0.5-2-8 times/year"
- Don't just give numbers - explain HOW to think about frequency"""
        
    elif fair_component == 'LM':
        context_guidance += """
The user is estimating Loss Magnitude (financial impact per incident in USD).

Help them understand:
- LM is the cost of a SINGLE incident, not annual
- Include: response costs, downtime, data recovery, legal fees, fines, reputation damage
- Min/Most Likely/Max accounts for incident severity variation
- Examples: "A minor breach might cost $50K-$250K-$1.5M depending on scope"
- Break down cost categories to help them estimate"""
        
    elif 'controls' in question_text.lower():
        context_guidance += """
The user is assessing their security controls.

Help them understand:
- Prevention controls: Stop attacks before they succeed (firewalls, MFA, training)
- Detection controls: Find attacks faster (SIEM, EDR, monitoring)
- Response controls: Minimize damage (backups, incident response, insurance)
- How each level (minimal/moderate/advanced) typically looks
- Practical steps to improve their security posture"""
    
    return base_prompt + context_guidance


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'ai_enabled': ai_generator is not None
    }), 200

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return render_template('error.html', error="Internal server error"), 500


def save_questionnaire(questionnaire: dict, industry: str, region: str) -> str:
    """Save questionnaire to file and return filename."""
    # Create generated directory if it doesn't exist
    os.makedirs('generated', exist_ok=True)
    
    # Create safe filename
    safe_industry = industry.replace("/", "-").replace(" ", "_")
    safe_region = region.replace("/", "-").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"questions_{safe_industry}_{safe_region}_{timestamp}.json"
    
    filepath = os.path.join('generated', filename)
    
    with open(filepath, 'w') as f:
        json.dump(questionnaire, f, indent=2)
    
    logger.info(f"Saved questionnaire to {filepath} ({os.path.getsize(filepath)} bytes)")
    
    return filename


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080))
    )
