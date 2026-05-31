# Assessment Context Design: Session-Based Context Object

## Problem Statement

The chat assistant currently lacks comprehensive context about:
1. **Question Path**: Which questions the user has answered
2. **User Selections**: What choices/answers were selected
3. **Assessment Metadata**: Industry, region, organization size
4. **FAIR Values**: TEF, Vulnerability, LEF, LM estimates captured so far
5. **Session History**: Previous chat exchanges across the entire assessment

## Proposed Solution: `AssessmentContext` Object

Create a **session-based context object** that:
- ✅ Initializes when assessment begins
- ✅ Accumulates data as user progresses through questionnaire
- ✅ Persists in Flask session throughout assessment
- ✅ Passed to chat assistant on every message
- ✅ Clears when new assessment starts

---

## Architecture

### 1. Context Object Structure

```python
class AssessmentContext:
    """
    Session-based context for a single risk assessment.
    Tracks user's journey through questionnaire and all relevant data.
    """
    
    def __init__(self, industry, region, organization_size=None):
        """Initialize new assessment context."""
        self.assessment_id = generate_unique_id()
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
    
    def add_answer(self, question_id, question_text, answer_data):
        """Record user's answer to a question."""
        self.question_path.append(question_id)
        self.answers[question_id] = {
            'question_text': question_text,
            'answer': answer_data,
            'answered_at': datetime.now().isoformat()
        }
        
        # Extract special values
        if 'vulnerability' in answer_data:
            self.fair_estimates['vulnerability'] = answer_data['vulnerability']
        if 'threat_scenario' in answer_data:
            self.threat_scenario = answer_data['threat_scenario']
        if 'control_level' in answer_data:
            self.control_level = answer_data['control_level']
    
    def update_fair_estimates(self, component, min_val=None, mle_val=None, max_val=None):
        """Update FAIR estimates (TEF, LEF, or LM)."""
        if component in ['tef', 'lef', 'lm']:
            if min_val is not None:
                self.fair_estimates[component]['min'] = min_val
            if mle_val is not None:
                self.fair_estimates[component]['mle'] = mle_val
            if max_val is not None:
                self.fair_estimates[component]['max'] = max_val
    
    def add_chat_message(self, user_message, assistant_response, question_id=None):
        """Add chat exchange to history."""
        self.chat_history.append({
            'user': user_message,
            'assistant': assistant_response,
            'question_id': question_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def set_current_question(self, question_id, question_text, question_type):
        """Update current question context."""
        self.current_question_id = question_id
        self.current_question_text = question_text
        self.current_question_type = question_type
    
    def get_recent_chat_history(self, n=3):
        """Get last N chat exchanges."""
        return self.chat_history[-n:] if len(self.chat_history) >= n else self.chat_history
    
    def get_summary_for_chat(self):
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
    
    def _get_recent_answers(self, n=5):
        """Get last N question-answer pairs."""
        recent_q_ids = self.question_path[-n:] if len(self.question_path) >= n else self.question_path
        return {qid: self.answers[qid] for qid in recent_q_ids}
    
    def to_dict(self):
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
    def from_dict(cls, data):
        """Recreate from dictionary (from session)."""
        context = cls(
            industry=data['industry'],
            region=data['region'],
            organization_size=data.get('organization_size')
        )
        context.assessment_id = data.get('assessment_id', generate_unique_id())
        context.started_at = datetime.fromisoformat(data['started_at'])
        context.question_path = data.get('question_path', [])
        context.answers = data.get('answers', {})
        context.fair_estimates = data.get('fair_estimates', {})
        context.threat_scenario = data.get('threat_scenario')
        context.asset_target = data.get('asset_target')
        context.control_level = data.get('control_level')
        context.chat_history = data.get('chat_history', [])
        context.current_question_id = data.get('current_question_id')
        context.current_question_text = data.get('current_question_text')
        context.current_question_type = data.get('current_question_type')
        return context


def generate_unique_id():
    """Generate unique assessment ID."""
    import uuid
    return str(uuid.uuid4())[:8]
```

---

## Implementation Plan

### Phase 1: Backend Integration (Flask)

**File: `flask_oic_v215.py`**

```python
from flask import session

# Initialize context when questionnaire starts
@app.route('/questionnaire')
def questionnaire():
    # Get questionnaire data
    filename = request.args.get('file')
    # ... load questions ...
    
    # Initialize AssessmentContext
    context = AssessmentContext(
        industry=questions['metadata']['industry'],
        region=questions['metadata']['region'],
        organization_size=request.args.get('organization_size')
    )
    
    # Store in session
    session['assessment_context'] = context.to_dict()
    
    return render_template('questionnaire_chat_rationale.html', ...)

# Update context endpoint (called from frontend)
@app.route('/context/update', methods=['POST'])
def update_context():
    """Update assessment context with user progress."""
    data = request.json
    
    # Load context from session
    context_dict = session.get('assessment_context')
    if not context_dict:
        return jsonify({'status': 'error', 'message': 'No context found'}), 400
    
    context = AssessmentContext.from_dict(context_dict)
    
    # Update based on action type
    action = data.get('action')
    
    if action == 'answer_question':
        context.add_answer(
            question_id=data['question_id'],
            question_text=data['question_text'],
            answer_data=data['answer']
        )
    
    elif action == 'set_current_question':
        context.set_current_question(
            question_id=data['question_id'],
            question_text=data['question_text'],
            question_type=data['question_type']
        )
    
    elif action == 'update_fair':
        context.update_fair_estimates(
            component=data['component'],
            min_val=data.get('min'),
            mle_val=data.get('mle'),
            max_val=data.get('max')
        )
    
    # Save back to session
    session['assessment_context'] = context.to_dict()
    
    return jsonify({'status': 'success'})

# Enhanced chat endpoint
@app.route('/chat/assist', methods=['POST'])
def chat_assist():
    data = request.json
    user_message = data.get('message')
    
    # Load assessment context from session
    context_dict = session.get('assessment_context')
    if context_dict:
        context = AssessmentContext.from_dict(context_dict)
        assessment_summary = context.get_summary_for_chat()
    else:
        # Fallback for backward compatibility
        assessment_summary = data.get('context', {})
    
    # Build enhanced prompt with full context
    prompt_parts = []
    prompt_parts.append(f"User question: {user_message}")
    prompt_parts.append(f"\n=== ASSESSMENT CONTEXT ===")
    prompt_parts.append(f"Industry: {assessment_summary['industry']}")
    prompt_parts.append(f"Region: {assessment_summary['region']}")
    
    if assessment_summary.get('organization_size'):
        prompt_parts.append(f"Organization Size: {assessment_summary['organization_size']}")
    
    prompt_parts.append(f"\nQuestions Answered So Far: {assessment_summary['questions_answered']}")
    
    # Current question
    current = assessment_summary['current_question']
    if current['id']:
        prompt_parts.append(f"\nCurrent Question: {current['text']}")
        prompt_parts.append(f"Question Type: {current['type']}")
    
    # Threat scenario context
    if assessment_summary.get('threat_scenario'):
        prompt_parts.append(f"\nThreat Scenario: {assessment_summary['threat_scenario']}")
    
    if assessment_summary.get('control_level'):
        prompt_parts.append(f"Control Maturity: {assessment_summary['control_level']}")
    
    # FAIR estimates captured
    fair = assessment_summary['fair_estimates']
    if fair['tef']['mle']:
        prompt_parts.append(f"\nThreat Event Frequency: {fair['tef']['min']}-{fair['tef']['mle']}-{fair['tef']['max']} attempts/year")
    if fair['vulnerability']:
        prompt_parts.append(f"Vulnerability: {fair['vulnerability']*100:.0f}% (attack success rate)")
    if fair['lef']['mle']:
        prompt_parts.append(f"Loss Event Frequency: {fair['lef']['min']}-{fair['lef']['mle']}-{fair['lef']['max']} events/year")
    
    # Recent question path
    if assessment_summary.get('recent_answers'):
        prompt_parts.append(f"\n=== RECENT ANSWERS ===")
        for qid, ans_data in assessment_summary['recent_answers'].items():
            prompt_parts.append(f"Q: {ans_data['question_text']}")
            prompt_parts.append(f"A: {ans_data['answer'].get('text', str(ans_data['answer']))}")
    
    # Chat history (for continuity)
    if assessment_summary['chat_history']:
        prompt_parts.append(f"\n=== RECENT CHAT HISTORY ===")
        for exchange in assessment_summary['chat_history']:
            prompt_parts.append(f"User: {exchange['user']}")
            prompt_parts.append(f"Assistant: {exchange['assistant'][:100]}...")  # Truncate
    
    user_prompt = "\n".join(prompt_parts)
    
    # Call Claude with enhanced context
    # ... (existing RAG + web search logic) ...
    
    response_text = # ... get from Claude ...
    
    # Update context with chat exchange
    if context_dict:
        context.add_chat_message(
            user_message=user_message,
            assistant_response=response_text,
            question_id=current['id']
        )
        session['assessment_context'] = context.to_dict()
    
    return jsonify({
        'status': 'success',
        'response': response_text
    })

# Clear context when starting new assessment
@app.route('/generate', methods=['POST'])
def generate():
    # Clear old assessment context
    session.pop('assessment_context', None)
    
    # ... existing generation logic ...
```

---

### Phase 2: Frontend Integration (JavaScript)

**File: `questionnaire_chat_rationale.html`**

```javascript
// Track assessment context on frontend
const assessmentContext = {
    questionPath: [],
    answers: {}
};

// Update context when user selects an answer
function selectChoice(element) {
    // ... existing selection logic ...
    
    // Capture answer data
    const answerData = {
        choice_id: element.dataset.choiceId,
        choice_text: element.querySelector('.choice-title').textContent,
        vulnerability: element.dataset.vulnerability,
        next_question: element.dataset.next
    };
    
    // Update backend context
    updateBackendContext('answer_question', {
        question_id: currentQuestionId,
        question_text: questions.questions[currentQuestionId].text,
        answer: answerData
    });
    
    // ... navigate to next question ...
}

// Update context when question changes
function renderQuestion(questionId) {
    // ... existing render logic ...
    
    // Update backend context with current question
    updateBackendContext('set_current_question', {
        question_id: questionId,
        question_text: question.text,
        question_type: question.type
    });
}

// Update FAIR estimates in context
function updatePertValue(key, value) {
    pertValues[key] = parseFloat(value);
    
    // Determine component (tef, lef, or lm)
    let component = 'lef';
    if (key.startsWith('tef_')) component = 'tef';
    else if (key.startsWith('lm_')) component = 'lm';
    
    // Extract min/mle/max
    const suffix = key.split('_').pop(); // 'min', 'mle', or 'max'
    
    updateBackendContext('update_fair', {
        component: component,
        [suffix]: parseFloat(value)
    });
}

// Send context updates to backend
async function updateBackendContext(action, data) {
    try {
        await fetch('/context/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: action,
                ...data
            })
        });
    } catch (error) {
        console.error('Context update failed:', error);
    }
}

// Enhanced sendMessage with context awareness
async function sendMessage() {
    // ... existing message sending logic ...
    
    // Context is now automatically available on backend via session
    // No need to send it in the request (backend pulls from session)
    
    const response = await fetch('/chat/assist', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: message
            // Context is retrieved from session on backend
        })
    });
    
    // ... handle response ...
}
```

---

## Benefits

### For Users
1. **Better assistance**: Chat understands full assessment context
2. **Continuity**: Chat remembers previous answers and discussions
3. **Relevant guidance**: Suggestions based on their specific scenario

### For Chat Assistant
1. **Full context**: Knows industry, region, organization size
2. **Question path**: Understands where user is in assessment
3. **FAIR values**: Can reference TEF, vulnerability, LEF estimates
4. **Previous choices**: Knows threat scenario, controls selected
5. **Chat history**: Maintains conversation continuity

### For System
1. **Session-based**: Automatically clears on new assessment
2. **Scalable**: Stored in Flask session (no database needed initially)
3. **Flexible**: Easy to add new context fields
4. **Backward compatible**: Degrades gracefully if context missing

---

## Example: Context-Aware Chat Response

**Without Context:**
```
User: "How often does this happen?"
Assistant: "It depends on your industry and controls..."
```

**With Full Context:**
```
User: "How often does this happen?"

Context Available to Assistant:
- Industry: Healthcare
- Region: Canada
- Threat: Ransomware
- Controls: Intermediate (15% vulnerability)
- TEF: 6 attempts/year (already answered)
- Previous chat: Discussed backup strategies

Assistant: "Based on your previous answer, ransomware groups attempt attacks against Canadian healthcare organizations about 6 times per year. With your intermediate controls (EDR, training, tested backups), you have 15% vulnerability, meaning 15% of those attempts succeed. So LEF = 6 attempts × 0.15 = 0.9 successful breaches per year, or roughly 1 breach every 13 months. This aligns with the backup strategy we discussed earlier."
```

Notice how the assistant:
- References previous answer (TEF = 6)
- Applies their control level (15% vulnerability)
- Calculates LEF automatically
- References previous chat about backups
- Provides industry/region-specific context

---

## Migration Strategy

### Phase 1: Add Context Infrastructure (Week 1)
- Create `AssessmentContext` class
- Add `/context/update` endpoint
- Store/retrieve from Flask session
- Test with simple context updates

### Phase 2: Frontend Integration (Week 1-2)
- Update `selectChoice()` to record answers
- Update `renderQuestion()` to track current question
- Update `updatePertValue()` to capture FAIR estimates
- Add context update calls

### Phase 3: Enhanced Chat Integration (Week 2)
- Modify `/chat/assist` to use context
- Build comprehensive prompt from context
- Update chat history in context
- Test with full user journey

### Phase 4: Polish & Optimization (Week 3)
- Add context summary to UI (show progress)
- Implement context export/import for resume capability
- Add context debugging tools
- Performance optimization

---

## Testing Checklist

- [ ] Context initializes on questionnaire start
- [ ] Context clears on new assessment
- [ ] Answers recorded correctly
- [ ] FAIR estimates captured (TEF, Vulnerability, LEF, LM)
- [ ] Chat history persists across questions
- [ ] Chat assistant receives full context
- [ ] Context survives page refresh (session-based)
- [ ] Multiple concurrent assessments (different sessions)
- [ ] Context export/import works
- [ ] Graceful degradation if context missing

---

## Future Enhancements

1. **Database Persistence**: Move from session to database for long-term storage
2. **Context Resume**: Allow users to pause and resume assessments
3. **Context Sharing**: Share assessment context with team members
4. **Context Analytics**: Analyze common question paths and answer patterns
5. **Smart Suggestions**: Use accumulated context to pre-fill suggestions
6. **Context Export**: Download assessment journey as report

---

## Implementation Priority: HIGH

This is a **critical enhancement** that will significantly improve:
- Chat assistant quality and relevance
- User experience and guidance
- Assessment accuracy and consistency
- System intelligence and context awareness

Recommend implementing in **next sprint** (Phases 1-3).
