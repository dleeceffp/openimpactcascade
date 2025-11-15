"""
Flask web application for AI-powered risk assessment questionnaire generation.
VERSION 2 ENHANCED: RAG + LLM with Enhanced Monte Carlo Distributions

Port: 8085
Code Generator ID: v2-rag-enhanced
Uses simulation_enhanced.py with lognormal and configurable distributions
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from ai_question_generator_v214 import AIQuestionGeneratorWithRAGAndRationale
from user_tracking import get_tracker, create_api_metadata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Version identifier
VERSION = "v215-rag-websearch"
PORT = 8080
# Right after line 27 in flask_app_chat_v2_rag.py
logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")

# Create required directories
os.makedirs('./generated', exist_ok=True)

# Initialize AI generator with version-specific tracker
ai_generator = None
try:
    ai_generator = AIQuestionGeneratorWithRAGAndRationale()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Web Search)")
except Exception as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}", exc_info=True)
    ai_generator = None

@app.route('/')
def home():
    """Home page - choose between static or AI-generated questionnaire."""
    return render_template('home.html', 
                         ai_available=ai_generator is not None,
                         version=VERSION,
                         port=PORT,
                         description="RAG + LLM with Enhanced Distributions")

@app.route('/about/mitre')
def about_mitre():
    """Information page about MITRE ATT&CK framework."""
    return render_template('about_mitre.html')

@app.route('/about/fair')
def about_fair():
    """Information page about FAIR methodology."""
    return render_template('about_fair.html')

@app.route('/about/probability-weighting')
def about_probability_weighting():
    """Information page about probability weighting modifications for cyber risk."""
    return render_template('about_probability_weighting.html')

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
        logger.info(f"[{VERSION}] Post request - retrieving form data")
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
        tracker = get_tracker(session_based=True, code_generator="v215-rag-websearchenhanced")
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
        tracker = get_tracker(session_based=True, code_generator="v215-rag-websearch-enhanced")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] User ID: {user_id}")
        
        # Build organization size string that includes custom scenario context
        org_context = org_size if org_size else ""
        
        # Append custom scenario to organization context
        if scenario_description:
            org_context = f"{org_context}\n\nCustom Risk Scenario: {risk_scenario}\nDetails: {scenario_description}".strip()
        else:
            org_context = f"{org_context}\n\nCustom Risk Scenario: {risk_scenario}".strip()
        
        # Generate questionnaire using standard method with custom scenario in context
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_context,
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

@app.route('/refine_scenario', methods=['POST'])
def refine_scenario():
    """Refine a user's narrative risk concern into structured scenario options."""
    if not ai_generator:
        return jsonify({'error': 'AI question generation is not available'}), 503
    
    try:
        data = request.get_json()
        narrative = data.get('narrative', '').strip()
        industry = data.get('industry', '').strip()
        region = data.get('region', '').strip()
        
        if not narrative or not industry or not region:
            return jsonify({'error': 'Narrative, industry, and region are required'}), 400
        
        logger.info(f"[{VERSION}] Refining scenario for {industry} in {region}")
        
        # Get tracker
        tracker = get_tracker(session_based=True, code_generator="v215-rag-websearch-enhanced")
        user_id = tracker.get_user_id()

        # Prepare RAG and intelligent web search context using v214 generator logic
        from vertex_rag_v211 import get_rag_engine
        rag_engine = get_rag_engine(enable_fallback=True)
        rag_contexts = []
        if rag_engine.enabled:
            try:
                rag_contexts = rag_engine.retrieve_coaching_context(
                    user_question=narrative,
                    industry=industry or "General",
                    region=region or "Global",
                    fair_component=None,
                    max_results=5
                )
                logger.info(f"[{VERSION}] [refine_scenario] Retrieved {len(rag_contexts)} RAG contexts")
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] RAG retrieval failed: {e}")

        # Analyze RAG coverage and conditionally perform intelligent web search
        rag_context_str = ""
        if rag_contexts:
            try:
                rag_context_str = rag_engine.format_context_for_prompt(rag_contexts)
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] Failed to format RAG context: {e}")

        web_context = ""
        if getattr(ai_generator, 'enable_web_search', False):
            try:
                rag_analysis = ai_generator._analyze_rag_content(rag_contexts, industry or "General", region or "Global")

                has_content = rag_analysis.get('has_content', False)
                has_current_year = rag_analysis.get('has_current_year_data', False)
                has_regional = rag_analysis.get('has_regional_data', False)
                has_breach_stats = rag_analysis.get('has_breach_statistics', False)

                needs_web_search = (not has_content) or (not has_current_year) or (not has_regional) or (not has_breach_stats)

                if needs_web_search:
                    logger.info(f"[{VERSION}] [refine_scenario] RAG gaps detected (current_year={has_current_year}, regional={has_regional}, breach_stats={has_breach_stats}); performing targeted web search")
                    web_context, _ = ai_generator._perform_intelligent_web_search(
                        industry=industry or "General",
                        region=region or "Global",
                        rag_analysis=rag_analysis,
                        user_id=user_id
                    )
                    if web_context:
                        logger.info(f"[{VERSION}] [refine_scenario] Web search context added to scenario refinement prompt")
                else:
                    logger.info(f"[{VERSION}] [refine_scenario] RAG coverage sufficient; skipping web search")
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] Web search for scenario refinement failed: {e}")

        # Use AI to refine the narrative into structured scenarios, grounded by RAG and optional web context
        import anthropic
        
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        
        system_prompt = """You are a cybersecurity risk assessment expert. Analyze the user's risk concern narrative and extract:
1. Key concerns (2-4 specific worries)
2. Recommended scenario options (3-5 specific, actionable risk scenarios)

You are provided with two kinds of optional grounding context:
- RAG corpus excerpts (framework and established threat intelligence)
- Recent web search results (current incidents, statistics, advisories)

When present, prioritize these contexts for factual grounding. Do not invent statistics or sources.

Return JSON format:
{
    "key_concerns": ["concern 1", "concern 2", ...],
    "scenarios": [
        {
            "title": "Specific Risk Scenario",
            "description": "Brief explanation of this scenario",
            "rationale": "Why this is relevant based on their concern (with sources)",
            "recommended": true/false
        }
    ]
}"""

        # Build user prompt with RAG + optional web context followed by the original narrative
        prompt_parts = []
        if rag_context_str:
            prompt_parts.append("=== RAG GROUNDING CONTEXT ===\n")
            prompt_parts.append(rag_context_str)
            prompt_parts.append("\n=== END RAG CONTEXT ===\n")
        if web_context:
            prompt_parts.append("\n=== WEB SEARCH CONTEXT (fills gaps in RAG, e.g., current-year, regional, breach statistics) ===\n")
            prompt_parts.append(web_context)
            prompt_parts.append("\n=== END WEB CONTEXT ===\n")

        prompt_parts.append(f"Industry: {industry}\nRegion: {region}\n\nUser's Risk Concern Narrative:\n{narrative}\n\nAnalyze this concern and provide structured scenario options grounded in the above contexts when available.")

        user_prompt = "".join(prompt_parts)

        api_metadata = create_api_metadata(user_id)
        original_user_id = api_metadata.pop('_original_user_id')
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            metadata=api_metadata
        )
        
        # Log API call
        tracker.log_api_call(
            user_id=original_user_id,
            hashed_user_id=api_metadata['user_id'],
            api_type='scenario_refinement',
            model='claude-sonnet-4-20250514',
            request_id=response.id
        )
        
        # Extract JSON from response
        content = response.content[0].text
        
        # Try to extract JSON if wrapped in code blocks
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        result = json.loads(content)
        
        logger.info(f"[{VERSION}] Successfully refined scenario: {len(result.get('scenarios', []))} options")
        
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        logger.error(f"[{VERSION}] JSON parsing error in scenario refinement: {e}")
        return jsonify({'error': 'Failed to parse AI response'}), 500
    except Exception as e:
        logger.error(f"[{VERSION}] Scenario refinement error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/questionnaire')
def questionnaire():
    """Display the generated questionnaire with chat interface."""
    filename = session.get('questionnaire_filename')
    params = session.get('generation_params', {})
    
    logger.info(f"[{VERSION}] 📋 Questionnaire route called")
    logger.info(f"[{VERSION}]   - Filename from session: {filename}")
    logger.info(f"[{VERSION}]   - Params from session: {params}")
    
    if not filename:
        logger.warning(f"[{VERSION}] ❌ No filename in session, redirecting to home")
        return redirect(url_for('home'))
    
    try:
        filepath = f'./generated/{filename}'
        logger.info(f"[{VERSION}]   - Loading file: {filepath}")
        
        # Check if file exists
        import os
        if not os.path.exists(filepath):
            logger.error(f"[{VERSION}] ❌ File does not exist: {filepath}")
            return render_template('error.html',
                error="Questionnaire not found. Please generate a new one."), 404
        
        # Get file size
        file_size = os.path.getsize(filepath)
        logger.info(f"[{VERSION}]   - File size: {file_size} bytes")
        
        # Load questionnaire from file
        with open(filepath, 'r') as f:
            questions = json.load(f)
        
        logger.info(f"[{VERSION}]   - JSON loaded successfully")
        
        return render_template('questionnaire_chat_rationale.html',
                             questions=questions,
                             params=params,
                             version=VERSION)
    except FileNotFoundError as e:
        logger.error(f"[{VERSION}] ❌ Questionnaire file not found: {filename}", exc_info=True)
        return render_template('error.html',
            error="Questionnaire not found. Please generate a new one."), 404
    except json.JSONDecodeError as e:
        logger.error(f"[{VERSION}] ❌ Invalid JSON in questionnaire file: {filename}", exc_info=True)
        logger.error(f"[{VERSION}]   - JSON error: {str(e)}")
        return render_template('error.html',
            error="Questionnaire file is corrupted. Please generate a new one."), 500
    except Exception as e:
        logger.error(f"[{VERSION}] ❌ Unexpected error loading questionnaire: {e}", exc_info=True)
        return render_template('error.html',
            error=f"Error loading questionnaire: {str(e)}"), 500

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
        tracker = get_tracker(session_based=True, code_generator="v215-rag-websearch-enhanced")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] Chat request from {user_id}: {user_message[:50]}...")
        
        # Generate response using Claude with RAG grounding
        response = generate_chat_response(user_message, context, user_id)
        
        return jsonify({
            'status': 'success', # required for chat assistant
            'response': response,
            'version': VERSION
        })
        
    except Exception as e:
        logger.error(f"[{VERSION}] Error in chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def generate_chat_response(user_message: str, context: Dict, user_id: str) -> str:
    """Generate chat response using Claude with RAG grounding, optionally supplemented by web search when RAG has gaps."""
    import anthropic
    from vertex_rag_v211 import get_rag_engine
    
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
    
    # Analyze RAG coverage and only perform web search when there are meaningful gaps
    web_context = ""
    if ai_generator is not None and getattr(ai_generator, 'enable_web_search', False):
        try:
            industry_for_search = context.get('industry', 'General')
            region_for_search = context.get('region', 'Global')
            rag_analysis = ai_generator._analyze_rag_content(rag_contexts, industry_for_search, region_for_search)

            has_content = rag_analysis.get('has_content', False)
            has_current_year = rag_analysis.get('has_current_year_data', False)
            has_regional = rag_analysis.get('has_regional_data', False)
            has_breach_stats = rag_analysis.get('has_breach_statistics', False)

            needs_web_search = (not has_content) or (not has_current_year) or (not has_regional) or (not has_breach_stats)

            if needs_web_search:
                logger.info(f"[{VERSION}] RAG gaps detected for chat (current_year={has_current_year}, regional={has_regional}, breach_stats={has_breach_stats}); performing targeted web search")
                web_context, _ = ai_generator._perform_intelligent_web_search(
                    industry=industry_for_search,
                    region=region_for_search,
                    rag_analysis=rag_analysis,
                    user_id=user_id
                )
                if web_context:
                    logger.info(f"[{VERSION}] Web search context added to chat prompt")
            else:
                logger.info(f"[{VERSION}] RAG coverage sufficient for chat; skipping web search")
        except Exception as e:
            logger.warning(f"[{VERSION}] Web search for chat failed: {e}")
    
    # Build system prompt with RAG grounding
    system_prompt = """You are a cybersecurity risk assessment coach helping users complete FAIR-based risk assessments.

Your role:
- Help users understand FAIR methodology (Loss Event Frequency and Loss Magnitude)
- Guide them in making realistic estimates based on their industry and organization
- Provide context about relevant threats and controls
- Use both the grounding context provided AND web search for current information

When grounding context is provided, prioritize it as authoritative but supplement with web search for current events.

Be concise, practical, and supportive."""
    
    # Build user prompt with RAG context (and optional web search context)
    prompt_parts = []
    
    # Add RAG grounding context if available
    if rag_contexts:
        formatted_context = rag_engine.format_context_for_prompt(rag_contexts, max_length=3000)
        prompt_parts.append(formatted_context)
        prompt_parts.append("\n---\n")

    # Add web search context only when gaps were detected and search succeeded
    if web_context:
        prompt_parts.append(web_context)
        prompt_parts.append("\n---\nThese recent web search results fill gaps in the RAG corpus (e.g., current-year, regional, or breach-statistics data). Use them together with the RAG context above when coaching the user.\n---\n")
    
    prompt_parts.append(f"User question: {user_message}")
    
    if context.get('industry'):
        prompt_parts.append(f"\nIndustry: {context['industry']}")
    if context.get('region'):
        prompt_parts.append(f"Region: {context['region']}")
    
    # Add current question context (sent from questionnaire page)
    if context.get('question_text'):
        prompt_parts.append(f"\nCurrent Question: {context['question_text']}")
    if context.get('question_type'):
        prompt_parts.append(f"Question Type: {context['question_type']}")
    if context.get('fair_component'):
        prompt_parts.append(f"FAIR Component: {context['fair_component']}")
    if context.get('help_text'):
        prompt_parts.append(f"Help Text: {context['help_text']}")
    
    # Add results page context (sent from results page)
    if context.get('page') == 'results':
        if context.get('risk_scenario'):
            prompt_parts.append(f"\nRisk Scenario: {context['risk_scenario']}")
        if context.get('expected_loss'):
            prompt_parts.append(f"Expected Annual Loss: ${context['expected_loss']:,.0f}")
        if context.get('p90_loss'):
            prompt_parts.append(f"90th Percentile Loss: ${context['p90_loss']:,.0f}")
        
        # Add FAIR estimates for context
        if context.get('lef_min') is not None:
            prompt_parts.append(f"\nLoss Event Frequency Estimates:")
            prompt_parts.append(f"  Min: {context['lef_min']} events/year")
            prompt_parts.append(f"  Most Likely: {context['lef_mle']} events/year")
            prompt_parts.append(f"  Max: {context['lef_max']} events/year")
        
        if context.get('lm_min') is not None:
            prompt_parts.append(f"\nLoss Magnitude Estimates:")
            prompt_parts.append(f"  Min: ${context['lm_min']:,.0f}")
            prompt_parts.append(f"  Most Likely: ${context['lm_mle']:,.0f}")
            prompt_parts.append(f"  Max: ${context['lm_max']:,.0f}")
    
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
    tracker = get_tracker(session_based=True, code_generator="v215-rag-websearch-enhanced")
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

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process the questionnaire responses and run Monte Carlo analysis."""
    try:
        # Import ENHANCED simulation module
        from simulation_v211 import run_monte_carlo
        
        # Get form data with better error handling
        try:
            lef_min = request.form.get('lef_min')
            lef_mle = request.form.get('lef_mle')
            lef_max = request.form.get('lef_max')
            lm_min = request.form.get('lm_min')
            lm_mle = request.form.get('lm_mle')
            lm_max = request.form.get('lm_max')
            # Optional context captured from the questionnaire UI: the first question answered and first option selected
            first_question_text = request.form.get('first_question_text', '').strip()
            first_choice_text = request.form.get('first_choice_text', '').strip()
            
            # Check for missing values
            if not all([lef_min, lef_mle, lef_max, lm_min, lm_mle, lm_max]):
                missing = []
                if not lef_min: missing.append('lef_min')
                if not lef_mle: missing.append('lef_mle')
                if not lef_max: missing.append('lef_max')
                if not lm_min: missing.append('lm_min')
                if not lm_mle: missing.append('lm_mle')
                if not lm_max: missing.append('lm_max')
                
                logger.error(f"[{VERSION}] Missing form fields: {missing}")
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
            logger.error(f"[{VERSION}] Invalid number format: {e}")
            return render_template('error.html', 
                error="Invalid number format. Please enter valid numbers for all estimate fields."), 400
        
        n_simulations = int(request.form.get('n_simulations', 10000))
        
        # Validate ranges
        if not (0 <= original_inputs['lef_min'] <= original_inputs['lef_mle'] <= original_inputs['lef_max']):
            logger.error(f"[{VERSION}] Invalid LEF range: {original_inputs['lef_min']}, {original_inputs['lef_mle']}, {original_inputs['lef_max']}")
            return render_template('error.html', 
                error=f"Invalid frequency estimates: min ({original_inputs['lef_min']}) ≤ most likely ({original_inputs['lef_mle']}) ≤ max ({original_inputs['lef_max']}) not satisfied"), 400
        
        if not (0 <= original_inputs['lm_min'] <= original_inputs['lm_mle'] <= original_inputs['lm_max']):
            logger.error(f"[{VERSION}] Invalid LM range: {original_inputs['lm_min']}, {original_inputs['lm_mle']}, {original_inputs['lm_max']}")
            return render_template('error.html', 
                error=f"Invalid magnitude estimates: min (${original_inputs['lm_min']:,.0f}) ≤ most likely (${original_inputs['lm_mle']:,.0f}) ≤ max (${original_inputs['lm_max']:,.0f}) not satisfied"), 400
        
        logger.info(f"[{VERSION}] Running ENHANCED Monte Carlo simulation with LEF: {original_inputs['lef_min']}-{original_inputs['lef_mle']}-{original_inputs['lef_max']}, LM: ${original_inputs['lm_min']}-${original_inputs['lm_mle']}-${original_inputs['lm_max']}")
        logger.info(f"[{VERSION}] Using lognormal distribution for Loss Magnitude (more realistic for cyber losses)")
        
        # Run ENHANCED simulation with lognormal for LM (default)
        results = run_monte_carlo(
            **original_inputs, 
            n_simulations=n_simulations,
            lef_distribution='pert',
            lm_distribution='lognormal'
        )
        
        # Validate results structure
        required_keys = ['mean', 'std', 'min', 'max', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95']
        missing_keys = [key for key in required_keys if key not in results]
        
        if missing_keys:
            logger.error(f"[{VERSION}] Simulation returned invalid results. Missing keys: {missing_keys}")
            logger.error(f"[{VERSION}] Results keys: {list(results.keys())}")
            logger.error(f"[{VERSION}] Results: {results}")
            return render_template('error.html',
                error=f"Simulation error: Invalid results format. Missing: {', '.join(missing_keys)}"), 500
        
        logger.info(f"[{VERSION}] Simulation complete: Mean=${results['mean']:,.0f}, StdDev=${results['std']:,.0f}")
        logger.info(f"[{VERSION}] Distribution info: {results.get('distribution_info', 'N/A')}")
        
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
                    logger.info(f"[{VERSION}] Found {len(mitre_references)} MITRE techniques")
                    
            except Exception as e:
                logger.warning(f"[{VERSION}] Could not load MITRE references: {e}")
        
        return render_template('results.html',
            results=results,
            original_inputs=original_inputs,
            n_simulations=n_simulations,
            mitre_references=mitre_references,
            generation_params=session.get('generation_params'),
            first_question_text=first_question_text,
            first_choice_text=first_choice_text
        )
        
    except (ValueError, TypeError) as e:
        logger.error(f"[{VERSION}] Validation error: {e}", exc_info=True)
        return render_template('error.html', error=f"Invalid input: {str(e)}"), 400
    except Exception as e:
        logger.error(f"[{VERSION}] Analysis error: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"Error during analysis: {str(e)}"), 500

@app.route('/recalculate', methods=['POST'])
def recalculate():
    """Recalculate simulation with adjusted parameters using enhanced distributions."""
    try:
        from simulation_v211 import run_monte_carlo
        
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
        
        logger.info(f"[{VERSION}] Recalculating with likelihood reduction: {likelihood_reduction*100}%, impact reduction: {impact_reduction*100}%")
        
        # Run ENHANCED simulation with lognormal for LM
        new_results = run_monte_carlo(
            **adjusted_inputs, 
            n_simulations=n_simulations,
            lef_distribution='pert',
            lm_distribution='lognormal'
        )
        
        return jsonify({
            'status': 'success',
            'results': new_results
        })
        
    except Exception as e:
        logger.error(f"[{VERSION}] Recalculation error: {e}")
        return jsonify({
            'error': 'Recalculation failed',
            'details': str(e)
        }), 500

@app.route('/chat/assist', methods=['POST'])
def chat_assist():
    """Stub route - redirects to main chat endpoint."""
    return chat()

@app.route('/chat/results', methods=['POST'])
def chat_results():
    """Handle chat messages on the results page."""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get tracker with version-specific code generator ID
        tracker = get_tracker(session_based=True, code_generator="v215-rag-websearch-enhanced")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] Results chat request from {user_id}: {user_message[:50]}...")
        
        # Generate response using Claude with RAG grounding
        response = generate_chat_response(user_message, context, user_id)
        
        return jsonify({
            'status': 'success',  # required for chat assistant
            'response': response,
            'version': VERSION
        })
    except Exception as e:
        logger.error(f"[{VERSION}] Results chat error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/chat/save', methods=['POST'])
def save_chat():
    """Stub route - chat saving not implemented in test version."""
    return jsonify({'error': 'Chat saving not available in test version'}), 501

@app.route('/download/<filename>')
def download_file(filename):
    """Stub route - file download not implemented in test version."""
    return jsonify({'error': 'File download not available in test version'}), 501

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
    from vertex_rag_v211 import get_rag_engine
    
    rag_engine = get_rag_engine(enable_fallback=True)
    
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'port': PORT,
        'ai_available': ai_generator is not None,
        'approach': 'RAG + LLM with Enhanced Distributions',
        'rag_enabled': rag_engine.enabled,
        'rag_status': rag_engine.get_status()
    })

if __name__ == '__main__':
    print("="*60)
    print(f"Starting Flask App - {VERSION}")
    print("="*60)
    print(f"Approach: RAG + LLM with Enhanced Distributions")
    print(f"Port: {PORT}")
    print(f"Code Generator ID: v2-rag-enhanced")
    print(f"User ID Format: eval-v2-rag-enhanced-XXXXXXXXXXXX")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=PORT)

