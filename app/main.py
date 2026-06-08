"""
Flask web application for AI-powered risk assessment questionnaire generation.
VERSION 3.0.2: currated-context + LLM with Assessment Context Tracking

Port: 8080
Code Generator ID: v221-context-aware
Features: Session-based assessment context, TEF/LEF decomposition, enhanced chat assistance
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, List, Any
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from ai_question_generator import AIQuestionGeneratorWithRAGAndRationale
from user_tracking import get_tracker, create_api_metadata
from context_storage import get_context_storage

from config import (
    OIC_MODEL, OIC_MODEL_FAST, OIC_MODEL_DEEP, build_system,
    OIC_CARDS_ENABLED, OIC_ARCHETYPE_SELECT, OIC_ARCHETYPE_LIMIT,
)
from cards.library import get_card_library

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Version identifier
VERSION = "v3.0.2-casade and curated context"
PORT = 8080
# Right after line 27 in flask_app_chat_v2_rag.py
logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")

# Create required directories
os.makedirs('./generated', exist_ok=True)

# Initialize context storage (SQLite-based)
context_storage = get_context_storage()


# ========== ASSESSMENT CONTEXT CLASS ==========

class AssessmentContext:
    """
    Session-based context for a single risk assessment.
    Tracks user's journey through questionnaire and all relevant data.
    """
    
    def __init__(self, industry: str, region: str, organization_size: Optional[str] = None):
        """Initialize new assessment context."""
        self.assessment_id = str(uuid.uuid4())[:8]
        self.started_at = datetime.now()
        
        # Assessment metadata
        self.industry = industry
        self.region = region
        self.organization_size = organization_size
        
        # Question path tracking
        self.question_path = []  # List of question IDs answered
        self.answers = {}  # {question_id: answer_data}
        
        # FAIR estimates captured
        self.fair_estimates = {
            'tef': {'min': None, 'mle': None, 'max': None},
            'vulnerability': None,  # From control selection
            'lef': {'min': None, 'mle': None, 'max': None},
            'lm': {'min': None, 'mle': None, 'max': None}
        }
        
        # Threat/scenario information
        self.threat_scenario = None  # Selected threat
        self.asset_target = None  # Selected asset
        self.control_level = None  # Selected control maturity
        
        # Chat history for this assessment
        self.chat_history = []  # List of {user: msg, assistant: response, question_id: id}
        
        # Current question context
        self.current_question_id = None
        self.current_question_text = None
        self.current_question_type = None
    
    def add_answer(self, question_id: str, question_text: str, answer_data: Dict):
        """Record user's answer to a question."""
        self.question_path.append(question_id)
        self.answers[question_id] = {
            'question_text': question_text,
            'answer': answer_data,
            'answered_at': datetime.now().isoformat()
        }
        
        # Extract special values
        if 'vulnerability' in answer_data and answer_data['vulnerability'] is not None:
            self.fair_estimates['vulnerability'] = float(answer_data['vulnerability'])
        if 'threat_scenario' in answer_data:
            self.threat_scenario = answer_data['threat_scenario']
        if 'control_level' in answer_data:
            self.control_level = answer_data['control_level']
        if 'choice_text' in answer_data:
            # Store the first significant choice
            if not self.threat_scenario and 'threat' in question_id.lower():
                self.threat_scenario = answer_data['choice_text']
    
    def update_fair_estimates(self, component: str, min_val=None, mle_val=None, max_val=None):
        """Update FAIR estimates (TEF, LEF, or LM)."""
        if component in ['tef', 'lef', 'lm']:
            if min_val is not None:
                self.fair_estimates[component]['min'] = float(min_val)
            if mle_val is not None:
                self.fair_estimates[component]['mle'] = float(mle_val)
            if max_val is not None:
                self.fair_estimates[component]['max'] = float(max_val)
    
    def add_chat_message(self, user_message: str, assistant_response: str, question_id: Optional[str] = None):
        """Add chat exchange to history."""
        self.chat_history.append({
            'user': user_message,
            'assistant': assistant_response,
            'question_id': question_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def set_current_question(self, question_id: str, question_text: str, question_type: str):
        """Update current question context."""
        self.current_question_id = question_id
        self.current_question_text = question_text
        self.current_question_type = question_type
    
    def get_recent_chat_history(self, n: int = 3) -> List[Dict]:
        """Get last N chat exchanges."""
        return self.chat_history[-n:] if len(self.chat_history) >= n else self.chat_history
    
    def get_summary_for_chat(self) -> Dict:
        """
        Generate a concise summary of assessment progress for chat assistant.
        This is passed to Claude to provide full context.
        """
        summary = {
            'industry': self.industry,
            'region': self.region,
            'organization_size': self.organization_size,
            'questions_answered': len(self.question_path),
            'current_question': {
                'id': self.current_question_id,
                'text': self.current_question_text,
                'type': self.current_question_type
            },
            'threat_scenario': self.threat_scenario,
            'control_level': self.control_level,
            'fair_estimates': self.fair_estimates,
            'recent_answers': self._get_recent_answers(5),
            'chat_history': self.get_recent_chat_history(3)
        }
        return summary
    
    def _get_recent_answers(self, n: int = 5) -> Dict:
        """Get last N question-answer pairs."""
        recent_q_ids = self.question_path[-n:] if len(self.question_path) >= n else self.question_path
        return {qid: self.answers[qid] for qid in recent_q_ids}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for session storage."""
        return {
            'assessment_id': self.assessment_id,
            'started_at': self.started_at.isoformat(),
            'industry': self.industry,
            'region': self.region,
            'organization_size': self.organization_size,
            'question_path': self.question_path,
            'answers': self.answers,
            'fair_estimates': self.fair_estimates,
            'threat_scenario': self.threat_scenario,
            'asset_target': self.asset_target,
            'control_level': self.control_level,
            'chat_history': self.chat_history,
            'current_question_id': self.current_question_id,
            'current_question_text': self.current_question_text,
            'current_question_type': self.current_question_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AssessmentContext':
        """Recreate from dictionary (from session)."""
        context = cls(
            industry=data['industry'],
            region=data['region'],
            organization_size=data.get('organization_size')
        )
        context.assessment_id = data.get('assessment_id', str(uuid.uuid4())[:8])
        context.started_at = datetime.fromisoformat(data['started_at'])
        context.question_path = data.get('question_path', [])
        context.answers = data.get('answers', {})
        context.fair_estimates = data.get('fair_estimates', {
            'tef': {'min': None, 'mle': None, 'max': None},
            'vulnerability': None,
            'lef': {'min': None, 'mle': None, 'max': None},
            'lm': {'min': None, 'mle': None, 'max': None}
        })
        context.threat_scenario = data.get('threat_scenario')
        context.asset_target = data.get('asset_target')
        context.control_level = data.get('control_level')
        context.chat_history = data.get('chat_history', [])
        context.current_question_id = data.get('current_question_id')
        context.current_question_text = data.get('current_question_text')
        context.current_question_type = data.get('current_question_type')
        return context


# ========== END ASSESSMENT CONTEXT CLASS ==========

# Initialize AI generator with version-specific tracker
ai_generator = None
try:
    ai_generator = AIQuestionGeneratorWithRAGAndRationale()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (currated-context + Web Search)")
except Exception as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}", exc_info=True)
    ai_generator = None

# Eager load pillar reader so first request isn't slow (lazy fallback stays)
try:
    from corpus.pillar_reader import get_pillar_reader
    get_pillar_reader().load()
    logger.info(f"[{VERSION}] PillarReader eager loaded")
except Exception as e:
    logger.warning(f"[{VERSION}] PillarReader eager load failed (will lazy-load): {e}")

# ========== AUTHENTICATION ==========

@app.before_request
def require_auth():
    """Require authentication for all routes except login, static files, and health check."""
    # Always allow health check for Cloud Run
    if request.endpoint == 'health':
        return
        
    # Allow static assets and login page
    if request.endpoint in ['login', 'static']:
        return
        
    # Check session
    if not session.get('authenticated'):
        # For API endpoints, return 401
        if request.path.startswith('/api/') or request.path.startswith('/chat/') or request.path.startswith('/context/'):
            return jsonify({'error': 'Unauthorized'}), 401
        # For web pages, redirect to login
        return redirect(url_for('login', next=request.url))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Basic auth login page to prevent bot access."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        expected_username = os.environ.get('APP_USERNAME', 'admin')
        expected_password = os.environ.get('APP_PASSWORD')
        
        if not expected_password:
            logger.error("APP_PASSWORD environment variable is not set!")
            return render_template('login.html', error='System configuration error. Please contact administrator.')
            
        if username == expected_username and password == expected_password:
            session['authenticated'] = True
            
            # Redirect to next URL if provided and safe, else home
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Log out the current user."""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    """Home page - choose between static or AI-generated questionnaire."""
    return render_template('home.html', 
                         ai_available=ai_generator is not None,
                         version=VERSION,
                         port=PORT,
                         description="currated-context + LLM with Enhanced Distributions")

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

@app.route('/about/layered-controls')
def about_layered_controls():
    """Information page about layered security controls and vulnerability reduction."""
    return render_template('about_layered_controls.html')

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Generate a new questionnaire using AI."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    archetype_step = OIC_CARDS_ENABLED and OIC_ARCHETYPE_SELECT

    if request.method == 'GET':
        # Show the generation form. When the archetype step is enabled, surface
        # the available cascade archetypes for the selection dropdown.
        archetypes = []
        if archetype_step:
            try:
                archetypes = get_card_library().archetypes_for('', None, OIC_ARCHETYPE_LIMIT)
            except Exception as e:
                logger.error(f"[{VERSION}] Failed to load archetypes: {e}", exc_info=True)
        # Pillar grounding context for UI
        pillar_grounding_enabled = False
        dbir_edition = None
        try:
            from corpus.pillar_reader import get_pillar_reader, SERIES_VERIZON_DBIR
            reader = get_pillar_reader()
            pillar_grounding_enabled = reader.has_series(SERIES_VERIZON_DBIR)
            if pillar_grounding_enabled:
                dbir_edition = reader.latest_edition(SERIES_VERIZON_DBIR)
        except Exception:
            pass  # Pillar reader not critical for UI

        return render_template(
            'generate.html',
            version=VERSION,
            archetype_step=archetype_step,
            archetypes=archetypes,
            pillar_grounding_enabled=pillar_grounding_enabled,
            dbir_edition=dbir_edition,
        )
    
    # POST - generate the questionnaire
    try:
        # Preserve auth state if present
        was_authenticated = session.get('authenticated')
        
        # Clear entire session to prevent cookie overflow from stale data
        session.clear()
        
        # Restore auth state
        if was_authenticated:
            session['authenticated'] = True
        
        # Generate new session ID for context storage
        new_session_id = str(uuid.uuid4())
        session['context_session_id'] = new_session_id
        logger.info(f"[{VERSION}] Created new context session: {new_session_id}")
        
        # Cleanup old context storage (delete old session from SQLite if needed)
        # Note: session.clear() already removed the old session_id from cookie
        
        # Cleanup old sessions (older than 24 hours)
        context_storage.cleanup_old_sessions(hours=2)
        
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
        
        # Resolve optional cascade-archetype selection (Path A grounded mode).
        # 'none'/'ai_suggest'/empty -> existing web-search behavior (fallback).
        archetype_card = None
        if archetype_step:
            selected_id = request.form.get('selected_archetype_id', '').strip()
            if selected_id and selected_id not in ('none', 'ai_suggest'):
                archetype_card = get_card_library().get(selected_id)
                if archetype_card is None:
                    logger.warning(f"[{VERSION}] Unknown archetype id '{selected_id}'; falling back to web-only")
                else:
                    logger.info(f"[{VERSION}] Grounding on cascade archetype: {selected_id}")
        
        logger.info(f"[{VERSION}] Generating questionnaire for {industry} in {region}" + 
                   (f" (org size: {org_size})" if org_size else ""))
        
        # Get tracker with version-specific code generator ID
        tracker = get_tracker(session_based=True, code_generator="v221-context-aware")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] User ID: {user_id}")
        
        # Generate questionnaire
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            user_id=user_id,
            max_retries=2,
            archetype_card=archetype_card
        )
        
        # Save to file
        filename = save_questionnaire(questions, industry, region, VERSION)
        
        # Store in session
        session['questionnaire_filename'] = filename
        session['generation_params'] = {
            'industry': industry,
            'region': region,
            'organization_size': org_size,
            'selected_archetype_id': archetype_card.id if archetype_card else None,
            'generated_at': datetime.now().isoformat(),
            'version': VERSION
        }
        
        logger.info(f"[{VERSION}] Successfully generated questionnaire, saved to {filename}")
        
        return redirect(url_for('questionnaire'))
        
    except Exception as e:
        logger.error(f"[{VERSION}] Error generating questionnaire: {e}", exc_info=True)
        return render_template('error.html', 
            error=f"Failed to generate questionnaire: {str(e)}"), 500

@app.route('/archetype/view/<archetype_id>')
def archetype_view(archetype_id):
    """Render a full cascade-archetype card as a standalone HTML page.

    Linked from the generate form's archetype selector (opens in a new tab) so
    the presenter can read the complete cascade without losing the in-progress
    selection. A Back button returns to the selection.
    """
    if not (OIC_CARDS_ENABLED and OIC_ARCHETYPE_SELECT):
        return render_template('error.html',
            error="Cascade archetypes are not enabled."), 404

    card = get_card_library().get(archetype_id)
    if card is None:
        return render_template('error.html',
            error=f"Cascade archetype '{archetype_id}' not found."), 404

    # Render the card's markdown body to HTML. Fall back to preformatted text
    # if the markdown package is unavailable so the page still works.
    try:
        import markdown as _md
        body_html = _md.markdown(card.body, extensions=['tables', 'fenced_code'])
    except Exception:
        from html import escape as _escape
        body_html = f"<pre>{_escape(card.body)}</pre>"

    return render_template(
        'archetype_view.html',
        version=VERSION,
        card=card,
        body_html=body_html,
    )

@app.route('/generate-custom', methods=['GET', 'POST'])
def generate_custom():
    """Generate a questionnaire for a user-defined risk scenario."""
    if not ai_generator:
        return render_template('error.html', 
            error="AI question generation is not available. Please set ANTHROPIC_API_KEY environment variable."), 503
    
    if request.method == 'GET':
        # Show the custom scenario generation form
        # Pillar grounding context for UI
        pillar_grounding_enabled = False
        dbir_edition = None
        try:
            from corpus.pillar_reader import get_pillar_reader, SERIES_VERIZON_DBIR
            reader = get_pillar_reader()
            pillar_grounding_enabled = reader.has_series(SERIES_VERIZON_DBIR)
            if pillar_grounding_enabled:
                dbir_edition = reader.latest_edition(SERIES_VERIZON_DBIR)
        except Exception:
            pass
        return render_template(
            'generate_custom.html',
            version=VERSION,
            pillar_grounding_enabled=pillar_grounding_enabled,
            dbir_edition=dbir_edition,
        )
    
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
        
        # Build custom scenario string: combine title + optional description
        if scenario_description:
            custom_scenario_str = f"{risk_scenario}: {scenario_description}"
        else:
            custom_scenario_str = risk_scenario
        
        # Generate questionnaire using dedicated custom_scenario path
        questions = ai_generator.generate_questionnaire(
            industry=industry,
            region=region,
            organization_size=org_size if org_size else None,
            user_id=user_id,
            max_retries=2,
            custom_scenario=custom_scenario_str
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

        # Prepare currated-context and intelligent web search context using v214 generator logic
        from corpus.retrieve import get_rag_engine as get_corpus_retriever
        rag_engine = get_corpus_retriever(enable_fallback=True)
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
                logger.info(f"[{VERSION}] [refine_scenario] Retrieved {len(rag_contexts)} currated-context contexts")
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] currated-context retrieval failed: {e}")

        # Analyze currated-context coverage and conditionally perform intelligent web search
        rag_context_str = ""
        if rag_contexts:
            try:
                rag_context_str = rag_engine.format_context_for_prompt(rag_contexts)
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] Failed to format currated-context context: {e}")

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
                    logger.info(f"[{VERSION}] [refine_scenario] currated-context gaps detected (current_year={has_current_year}, regional={has_regional}, breach_stats={has_breach_stats}); performing targeted web search")
                    web_context, _ = ai_generator._perform_intelligent_web_search(
                        industry=industry or "General",
                        region=region or "Global",
                        rag_analysis=rag_analysis,
                        user_id=user_id
                    )
                    if web_context:
                        logger.info(f"[{VERSION}] [refine_scenario] Web search context added to scenario refinement prompt")
                else:
                    logger.info(f"[{VERSION}] [refine_scenario] currated-context coverage sufficient; skipping web search")
            except Exception as e:
                logger.warning(f"[{VERSION}] [refine_scenario] Web search for scenario refinement failed: {e}")

        # Use AI to refine the narrative into structured scenarios, grounded by currated-context and optional web context
        import anthropic
        
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        
        system_prompt = """You are a cybersecurity risk assessment expert. Analyze the user's risk concern narrative and extract:
1. Key concerns (2-4 specific worries)
2. Recommended scenario options (3-5 specific, actionable risk scenarios)

You are provided with two kinds of optional grounding context:
- currated-context corpus excerpts (framework and established threat intelligence)
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

        # Build user prompt with currated-context + optional web context followed by the original narrative
        prompt_parts = []
        if rag_context_str:
            prompt_parts.append("=== CORPUS GROUNDING CONTEXT ===\n")
            prompt_parts.append(rag_context_str)
            prompt_parts.append("\n=== END CORPUS CONTEXT ===\n")
        if web_context:
            prompt_parts.append("\n=== WEB SEARCH CONTEXT (fills gaps in RAG, e.g., current-year, regional, breach statistics) ===\n")
            prompt_parts.append(web_context)
            prompt_parts.append("\n=== END WEB CONTEXT ===\n")

        prompt_parts.append(f"Industry: {industry}\nRegion: {region}\n\nUser's Risk Concern Narrative:\n{narrative}\n\nAnalyze this concern and provide structured scenario options grounded in the above contexts when available.")

        user_prompt = "".join(prompt_parts)

        api_metadata = create_api_metadata(user_id)
        original_user_id = api_metadata.pop('_original_user_id')
        
        response = client.messages.create(
            model=OIC_MODEL,
            max_tokens=4000,
            system=build_system(system_prompt),
            messages=[{"role": "user", "content": user_prompt}],
            metadata=api_metadata
        )
        
        # Log API call
        tracker.log_api_call(
            user_id=original_user_id,
            hashed_user_id=api_metadata['user_id'],
            api_type='scenario_refinement',
            model=OIC_MODEL,
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
        
        # Initialize AssessmentContext for this session
        context = AssessmentContext(
            industry=questions['metadata'].get('industry', params.get('industry', 'Unknown')),
            region=questions['metadata'].get('region', params.get('region', 'Unknown')),
            organization_size=params.get('organization_size')
        )
        
        # Save context to SQLite storage
        session_id = session.get('context_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['context_session_id'] = session_id
        
        context_storage.save(session_id, context.to_dict())
        logger.info(f"[{VERSION}]   - Assessment context initialized (ID: {context.assessment_id}, Session: {session_id[:8]})")
        
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

@app.route('/context/update', methods=['POST'])
def update_context():
    """Update assessment context with user progress."""
    try:
        data = request.json
        
        # Load context from SQLite storage
        session_id = session.get('context_session_id')
        if not session_id:
            logger.warning(f"[{VERSION}] No context session ID found")
            return jsonify({'status': 'error', 'message': 'No session found'}), 400
        
        context_dict = context_storage.load(session_id)
        if not context_dict:
            logger.warning(f"[{VERSION}] No assessment context found for session {session_id}")
            return jsonify({'status': 'error', 'message': 'No context found'}), 400
        
        context = AssessmentContext.from_dict(context_dict)
        
        # Update based on action type
        action = data.get('action')
        logger.info(f"[{VERSION}] Context update: action={action}")
        
        if action == 'answer_question':
            context.add_answer(
                question_id=data['question_id'],
                question_text=data['question_text'],
                answer_data=data['answer']
            )
            logger.info(f"[{VERSION}]   - Recorded answer for: {data['question_id']}")
        
        elif action == 'set_current_question':
            context.set_current_question(
                question_id=data['question_id'],
                question_text=data['question_text'],
                question_type=data['question_type']
            )
            logger.info(f"[{VERSION}]   - Set current question: {data['question_id']}")
        
        elif action == 'update_fair':
            context.update_fair_estimates(
                component=data['component'],
                min_val=data.get('min'),
                mle_val=data.get('mle'),
                max_val=data.get('max')
            )
            logger.info(f"[{VERSION}]   - Updated {data['component']} estimates")
        
        else:
            logger.warning(f"[{VERSION}]   - Unknown action: {action}")
        
        # Save back to SQLite storage
        context_storage.save(session_id, context.to_dict())
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"[{VERSION}] Context update error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
        tracker = get_tracker(session_based=True, code_generator="v221-context-aware")
        user_id = tracker.get_user_id()
        
        logger.info(f"[{VERSION}] Chat request from {user_id}: {user_message[:50]}...")
        
        # Generate response using Claude with currated-context grounding
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
    """Generate chat response using Claude with currated-context grounding, optionally supplemented by web search when currated-context has gaps."""
    import anthropic
    from corpus.retrieve import get_rag_engine as get_corpus_retriever
    
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    # Get currated-context engine and retrieve grounding context
    rag_engine = get_corpus_retriever(enable_fallback=True)
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
            logger.info(f"[{VERSION}] Retrieved {len(rag_contexts)} currated contexts")
        except Exception as e:
            logger.warning(f"[{VERSION}] currated-context retrieval failed: {e}")
    
    # Analyze currated-context coverage and only perform web search when there are meaningful gaps
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
                logger.info(f"[{VERSION}] currated-context gaps detected for chat (current_year={has_current_year}, regional={has_regional}, breach_stats={has_breach_stats}); performing targeted web search")
                web_context, _ = ai_generator._perform_intelligent_web_search(
                    industry=industry_for_search,
                    region=region_for_search,
                    rag_analysis=rag_analysis,
                    user_id=user_id
                )
                if web_context:
                    logger.info(f"[{VERSION}] Web search context added to chat prompt")
            else:
                logger.info(f"[{VERSION}] currated-context coverage sufficient for chat; skipping web search")
        except Exception as e:
            logger.warning(f"[{VERSION}] Web search for chat failed: {e}")
    
    # Build system prompt with currated-context grounding
    system_prompt = """You are a cybersecurity risk assessment coach helping users complete FAIR-based risk assessments.

Your role:
- Help users understand FAIR methodology (Loss Event Frequency and Loss Magnitude)
- Guide them in making realistic estimates based on their industry and organization
- Provide context about relevant threats and controls
- Use both the grounding context provided AND web search for current information

When grounding context is provided, prioritize it as authoritative but supplement with web search for current events.

Be concise, practical, and supportive."""
    
    # Build user prompt with currated-context context (and optional web search context)
    prompt_parts = []
    
    # Add currated-context grounding context if available
    if rag_contexts:
        formatted_context = rag_engine.format_context_for_prompt(rag_contexts, max_length=3000)
        prompt_parts.append(formatted_context)
        prompt_parts.append("\n---\n")

    # Add web search context only when gaps were detected and search succeeded
    if web_context:
        prompt_parts.append(web_context)
        prompt_parts.append("\n---\nThese recent web search results fill gaps in the currated-context corpus (e.g., current-year, regional, or breach-statistics data). Use them together with the currated-context context above when coaching the user.\n---\n")
    
    prompt_parts.append(f"User question: {user_message}")
    
    # Try to load full AssessmentContext from SQLite storage for enhanced context
    assessment_summary = None
    try:
        from flask import session as flask_session
        session_id = flask_session.get('context_session_id')
        if session_id:
            context_dict = context_storage.load(session_id)
            if context_dict:
                assessment_context = AssessmentContext.from_dict(context_dict)
                assessment_summary = assessment_context.get_summary_for_chat()
                logger.info(f"[{VERSION}] Using full AssessmentContext for chat (answered {assessment_summary['questions_answered']} questions)")
    except Exception as e:
        logger.warning(f"[{VERSION}] Could not load AssessmentContext: {e}")
    
    # Use enhanced context if available, otherwise fall back to basic context
    if assessment_summary:
        prompt_parts.append(f"\n=== ASSESSMENT CONTEXT ===")
        prompt_parts.append(f"Industry: {assessment_summary['industry']}")
        prompt_parts.append(f"Region: {assessment_summary['region']}")
        
        if assessment_summary.get('organization_size'):
            prompt_parts.append(f"Organization Size: {assessment_summary['organization_size']}")
        
        prompt_parts.append(f"\nQuestions Answered: {assessment_summary['questions_answered']}")
        
        # Current question
        current = assessment_summary['current_question']
        if current.get('id'):
            prompt_parts.append(f"\nCurrent Question: {current['text']}")
            prompt_parts.append(f"Question Type: {current['type']}")
        
        # Threat scenario context
        if assessment_summary.get('threat_scenario'):
            prompt_parts.append(f"\nThreat Scenario: {assessment_summary['threat_scenario']}")
        
        if assessment_summary.get('control_level'):
            prompt_parts.append(f"Control Maturity: {assessment_summary['control_level']}")
        
        # FAIR estimates captured (only show if all values present)
        fair = assessment_summary['fair_estimates']
        
        # TEF estimates
        tef = fair.get('tef', {})
        if tef.get('min') is not None and tef.get('mle') is not None and tef.get('max') is not None:
            prompt_parts.append(f"\nThreat Event Frequency: {tef['min']}-{tef['mle']}-{tef['max']} attempts/year")
        
        # Vulnerability
        if fair.get('vulnerability') is not None:
            prompt_parts.append(f"Vulnerability: {fair['vulnerability']*100:.0f}% (attack success rate)")
        
        # LEF estimates
        lef = fair.get('lef', {})
        if lef.get('min') is not None and lef.get('mle') is not None and lef.get('max') is not None:
            prompt_parts.append(f"Loss Event Frequency: {lef['min']}-{lef['mle']}-{lef['max']} events/year")
        
        # LM estimates
        lm = fair.get('lm', {})
        if lm.get('min') is not None and lm.get('mle') is not None and lm.get('max') is not None:
            prompt_parts.append(f"Loss Magnitude: ${lm['min']:,.0f}-${lm['mle']:,.0f}-${lm['max']:,.0f}")
        
        # Recent question path
        if assessment_summary.get('recent_answers'):
            prompt_parts.append(f"\n=== RECENT ANSWERS ===")
            for qid, ans_data in list(assessment_summary['recent_answers'].items())[:3]:
                prompt_parts.append(f"Q: {ans_data['question_text'][:80]}")
                answer_text = ans_data['answer'].get('choice_text', str(ans_data['answer']))[:80]
                prompt_parts.append(f"A: {answer_text}")
        
        # Chat history (for continuity)
        if assessment_summary.get('chat_history'):
            prompt_parts.append(f"\n=== RECENT CHAT HISTORY ===")
            for exchange in assessment_summary['chat_history'][-2:]:
                prompt_parts.append(f"User: {exchange['user'][:60]}")
                prompt_parts.append(f"Assistant: {exchange['assistant'][:100]}...")
    
    else:
        # Fallback to basic context from request
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
    
    user_prompt = "\n".join(prompt_parts)
    
    # Create API metadata with hashed user_id
    api_metadata = create_api_metadata(user_id)
    original_user_id = api_metadata.pop('_original_user_id')
    
    # Call Claude
    message = client.messages.create(
        model=OIC_MODEL,
        max_tokens=2048,
        temperature=0.3,
        system=build_system(system_prompt),
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        metadata=api_metadata
    )
    
    # Log the API call
    tracker = get_tracker(session_based=True, code_generator="v221-context-aware")
    tracker.log_api_call(
        user_id=original_user_id,
        hashed_user_id=api_metadata['user_id'],
        api_type='chat_assist',
        model=OIC_MODEL,
        request_id=message.id,
        metadata={
            'version': VERSION,
            'has_context': bool(context),
            'has_assessment_context': assessment_summary is not None,
            'questions_answered': assessment_summary.get('questions_answered', 0) if assessment_summary else 0,
            'rag_contexts_retrieved': len(rag_contexts),
            'rag_enabled': rag_engine.enabled
        }
    )
    
    response_text = message.content[0].text
    
    # Save chat exchange to AssessmentContext in SQLite
    try:
        from flask import session as flask_session
        session_id = flask_session.get('context_session_id')
        if session_id:
            context_dict = context_storage.load(session_id)
            if context_dict:
                assessment_context = AssessmentContext.from_dict(context_dict)
                current_q_id = assessment_context.current_question_id
                assessment_context.add_chat_message(
                    user_message=user_message,
                    assistant_response=response_text,
                    question_id=current_q_id
                )
                context_storage.save(session_id, assessment_context.to_dict())
                logger.info(f"[{VERSION}] Chat exchange saved to AssessmentContext")
    except Exception as e:
        logger.warning(f"[{VERSION}] Could not save chat to context: {e}")
    
    return response_text

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
        from simulation import run_monte_carlo
        from config import OIC_MC_COMPOUND
        
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
            lm_distribution='lognormal',
            compound_mode=OIC_MC_COMPOUND,
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
        from simulation import run_monte_carlo, combine_reductions
        from config import OIC_MC_COMPOUND

        data = request.get_json()

        # Get parameters
        inputs = data.get('original_inputs')
        likelihood_reduction = data.get('likelihood_reduction', 0) / 100.0
        impact_reduction = data.get('impact_reduction', 0) / 100.0
        n_simulations = min(int(data.get('n_simulations', 10000)), 100000)

        # The existing 25% vulnerability-management credit is a likelihood/frequency
        # reduction, not a final-loss haircut. Route it into odds_reduction and
        # combine multiplicatively with any user-selected likelihood controls.
        VULN_CREDIT = 0.25
        odds_reduction = combine_reductions([VULN_CREDIT, likelihood_reduction])
        size_reduction = impact_reduction

        logger.info(
            f"[{VERSION}] Recalculating — odds_reduction: {odds_reduction*100:.1f}% "
            f"(vuln credit + {likelihood_reduction*100:.0f}% slider), "
            f"size_reduction: {size_reduction*100:.0f}%, compound_mode: {OIC_MC_COMPOUND}"
        )

        # Run ENHANCED simulation with lognormal for LM.
        # Levers are applied inside run_monte_carlo; inputs are unchanged.
        new_results = run_monte_carlo(
            lef_min=inputs['lef_min'],
            lef_mle=inputs['lef_mle'],
            lef_max=inputs['lef_max'],
            lm_min=inputs['lm_min'],
            lm_mle=inputs['lm_mle'],
            lm_max=inputs['lm_max'],
            n_simulations=n_simulations,
            lef_distribution='pert',
            lm_distribution='lognormal',
            odds_reduction=odds_reduction,
            size_reduction=size_reduction,
            compound_mode=OIC_MC_COMPOUND,
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
        
        # Generate response using Claude with currated-context grounding
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

@app.route('/chat/export', methods=['GET'])
def export_chat():
    """Export complete chat history from SQLite storage."""
    try:
        # Get session ID
        session_id = session.get('context_session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400
        
        # Load context from SQLite
        context_dict = context_storage.load(session_id)
        if not context_dict:
            return jsonify({'error': 'No chat history found'}), 404
        
        context = AssessmentContext.from_dict(context_dict)
        chat_history = context.chat_history
        
        if not chat_history:
            return jsonify({'error': 'No chat messages to export'}), 404
        
        # Format as text
        lines = []
        lines.append("=" * 80)
        lines.append(f"RISK ASSESSMENT CHAT HISTORY")
        lines.append(f"Industry: {context.industry}")
        lines.append(f"Region: {context.region}")
        if context.organization_size:
            lines.append(f"Organization Size: {context.organization_size}")
        lines.append(f"Assessment ID: {context.assessment_id}")
        lines.append(f"Started: {context.started_at}")
        lines.append(f"Total Exchanges: {len(chat_history)}")
        lines.append("=" * 80)
        lines.append("")
        
        # Add each exchange
        for i, exchange in enumerate(chat_history, 1):
            lines.append(f"{'=' * 80}")
            lines.append(f"EXCHANGE {i}")
            if exchange.get('question_id'):
                lines.append(f"Question ID: {exchange['question_id']}")
            if exchange.get('timestamp'):
                lines.append(f"Timestamp: {exchange['timestamp']}")
            lines.append(f"{'=' * 80}")
            lines.append("")
            lines.append(f"USER:")
            lines.append(exchange.get('user', ''))
            lines.append("")
            lines.append(f"ASSISTANT:")
            lines.append(exchange.get('assistant', ''))
            lines.append("")
        
        lines.append("=" * 80)
        lines.append(f"END OF CHAT HISTORY - {len(chat_history)} exchanges")
        lines.append("=" * 80)
        
        content = "\n".join(lines)
        
        return jsonify({
            'status': 'success',
            'content': content,
            'count': len(chat_history),
            'metadata': {
                'industry': context.industry,
                'region': context.region,
                'assessment_id': context.assessment_id
            }
        })
        
    except Exception as e:
        logger.error(f"[{VERSION}] Chat export error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

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
    from corpus.retrieve import get_rag_engine as get_corpus_retriever
    
    rag_engine = get_corpus_retriever(enable_fallback=True)
    
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'port': PORT,
        'ai_available': ai_generator is not None,
        'approach': 'currated-context + LLM with Enhanced Distributions',
        'rag_enabled': rag_engine.enabled
    })

if __name__ == '__main__':
    print("="*60)
    print(f"Starting Flask App - {VERSION}")
    print("="*60)
    print(f"Approach: currated-context + LLM with Enhanced Distributions, gaps filled with websearch")
    print(f"Port: {PORT}")
    print(f"AI Question Generator ID: v214")
    print(f"User ID Format: eval-v2-rag-websearch-enhanced-XXXXXXXXXXXX")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=PORT)

