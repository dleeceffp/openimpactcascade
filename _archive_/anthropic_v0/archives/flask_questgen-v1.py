"""
Flask web application for AI-powered risk assessment questionnaire generation.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from ai_question_generator import AIQuestionGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

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
        
        logger.info(f"Generating questionnaire for {industry} in {region}")
        
        # Generate questionnaire with optional parameters
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            max_retries=2
        )
        
        # Store in session for use in the questionnaire
        session['generated_questions'] = questions
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'organization_size': org_size,
            'generated_at': datetime.now().isoformat()
        }
        
        # Also save to file for reference
        filename = save_questionnaire(questions, industry, region)
        session['questionnaire_filename'] = filename
        
        logger.info(f"Successfully generated questionnaire, saved to {filename}")
        
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
    """Display the generated questionnaire."""
    questions = session.get('generated_questions')
    params = session.get('generation_params')
    
    if not questions:
        return redirect(url_for('home'))
    
    return render_template('questionnaire.html', 
        questions=questions,
        params=params
    )

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process the questionnaire responses and run Monte Carlo analysis."""
    try:
        # Import simulation module
        from simulation import run_monte_carlo
        
        # Get form data
        original_inputs = {
            'lef_min': float(request.form.get('lef_min')),
            'lef_mle': float(request.form.get('lef_mle')),
            'lef_max': float(request.form.get('lef_max')),
            'lm_min': float(request.form.get('lm_min')),
            'lm_mle': float(request.form.get('lm_mle')),
            'lm_max': float(request.form.get('lm_max'))
        }
        n_simulations = int(request.form.get('n_simulations', 10000))
        
        # Validate
        if not (0 <= original_inputs['lef_min'] <= original_inputs['lef_mle'] <= original_inputs['lef_max']):
            return render_template('error.html', 
                error="Invalid frequency estimates: must satisfy min ≤ most likely ≤ max"), 400
        
        if not (0 <= original_inputs['lm_min'] <= original_inputs['lm_mle'] <= original_inputs['lm_max']):
            return render_template('error.html', 
                error="Invalid magnitude estimates: must satisfy min ≤ most likely ≤ max"), 400
        
        # Run simulation
        results = run_monte_carlo(**original_inputs, n_simulations=n_simulations)
        
        # Get MITRE references if available
        mitre_references = None
        questions = session.get('generated_questions')
        if questions and 'metadata' in questions:
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
        
        return render_template('results.html',
            results=results,
            original_inputs=original_inputs,
            n_simulations=n_simulations,
            mitre_references=mitre_references,
            generation_params=session.get('generation_params')
        )
        
    except (ValueError, TypeError) as e:
        logger.error(f"Validation error: {e}")
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
        return "Unauthorized", 403
    
    filepath = os.path.join('generated', filename)
    if not os.path.exists(filepath):
        return "File not found", 404
    
    return send_file(filepath, as_attachment=True)

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
    
    return filename


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080))
    )
