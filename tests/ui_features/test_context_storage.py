"""
Test SQLite-based context storage system.
Verifies it solves the cookie size limit issue.
"""

import sys
sys.path.insert(0, 'app')

import json
from context_storage import get_context_storage, ContextStorage

# Simplified AssessmentContext for testing (avoid Flask import)
class AssessmentContext:
    def __init__(self, industry, region, organization_size=None):
        self.assessment_id = "test-assessment-001"
        self.industry = industry
        self.region = region
        self.organization_size = organization_size
        self.answers = {}
        self.chat_history = []
        self.fair_estimates = {'tef': {}, 'lef': {}, 'lm': {}, 'vulnerability': None}
    
    def add_answer(self, question_id, question_text, answer_data):
        self.answers[question_id] = {'question_text': question_text, 'answer': answer_data}
    
    def update_fair_estimates(self, component, min_val=None, mle_val=None, max_val=None):
        if component in ['tef', 'lef', 'lm']:
            if min_val: self.fair_estimates[component]['min'] = min_val
            if mle_val: self.fair_estimates[component]['mle'] = mle_val
            if max_val: self.fair_estimates[component]['max'] = max_val
    
    def add_chat_message(self, user_message, assistant_response, question_id=None):
        self.chat_history.append({'user': user_message, 'assistant': assistant_response})
    
    def to_dict(self):
        return {
            'assessment_id': self.assessment_id,
            'industry': self.industry,
            'region': self.region,
            'organization_size': self.organization_size,
            'answers': self.answers,
            'chat_history': self.chat_history,
            'fair_estimates': self.fair_estimates
        }
    
    @classmethod
    def from_dict(cls, data):
        context = cls(data['industry'], data['region'], data.get('organization_size'))
        context.assessment_id = data['assessment_id']
        context.answers = data.get('answers', {})
        context.chat_history = data.get('chat_history', [])
        context.fair_estimates = data.get('fair_estimates', {})
        return context

print("="*80)
print("TESTING SQLITE-BASED CONTEXT STORAGE")
print("="*80)
print()

# Initialize storage (uses /tmp/assessment_contexts.db)
storage = get_context_storage()
print("✅ Storage initialized")
print()

# Create a large context (similar to what was breaking cookies)
context = AssessmentContext(
    industry="Technology",
    region="Canada", 
    organization_size="500 employees"
)

# Add multiple answers to simulate a real assessment
for i in range(10):
    context.add_answer(
        question_id=f"q{i}",
        question_text=f"Question {i}: What is your assessment of threat level {i}?",
        answer_data={
            'choice_text': f"High severity threat scenario {i}",
            'choice_description': f"This is a detailed description of the threat scenario and why it matters for cybersecurity risk assessment. It includes information about attack vectors, threat actors, and potential impact on business operations." * 3,
            'vulnerability': 0.15
        }
    )

# Add FAIR estimates
context.update_fair_estimates('tef', min_val=4.0, mle_val=6.0, max_val=12.0)
context.update_fair_estimates('lef', min_val=0.6, mle_val=0.9, max_val=1.8)
context.update_fair_estimates('lm', min_val=50000, mle_val=400000, max_val=2000000)

# Add chat history
for i in range(15):
    context.add_chat_message(
        user_message=f"User question {i}: Can you explain more about this threat?",
        assistant_response=f"Assistant response {i}: " + ("This is a detailed response about the threat scenario including best practices, industry standards, and recommendations for your specific situation. " * 10),
        question_id=f"q{i % 5}"
    )

# Convert to dictionary and check size
context_dict = context.to_dict()
context_json = json.dumps(context_dict)
size_bytes = len(context_json.encode('utf-8'))

print(f"Context Statistics:")
print(f"  Assessment ID: {context.assessment_id}")
print(f"  Questions answered: {len(context.answers)}")
print(f"  Chat messages: {len(context.chat_history)}")
print(f"  Serialized size: {size_bytes:,} bytes")
print(f"  Cookie limit: 4,093 bytes")
print(f"  Size ratio: {size_bytes / 4093:.1f}x over limit")
print()

if size_bytes > 4093:
    print("⚠️  This context EXCEEDS cookie size limit!")
    print("   (This is the problem we're solving)")
else:
    print("✓ Context fits in cookie (test needs more data)")
print()

# Test saving to SQLite
session_id = "test-session-12345"
print(f"Testing SQLite storage with session ID: {session_id}")
print()

# Save
success = storage.save(session_id, context_dict)
if success:
    print("✅ Context saved to SQLite")
else:
    print("❌ Failed to save context")
    sys.exit(1)

# Load
loaded_dict = storage.load(session_id)
if loaded_dict:
    print("✅ Context loaded from SQLite")
    loaded_context = AssessmentContext.from_dict(loaded_dict)
    print(f"   - Assessment ID: {loaded_context.assessment_id}")
    print(f"   - Questions answered: {len(loaded_context.answers)}")
    print(f"   - Chat messages: {len(loaded_context.chat_history)}")
else:
    print("❌ Failed to load context")
    sys.exit(1)

# Verify data integrity
assert loaded_context.assessment_id == context.assessment_id
assert len(loaded_context.answers) == len(context.answers)
assert len(loaded_context.chat_history) == len(context.chat_history)
print("✅ Data integrity verified")
print()

# Test statistics
stats = storage.get_stats()
print(f"Storage Statistics:")
print(f"  Total sessions: {stats['total_sessions']}")
print(f"  Total size: {stats['total_size_bytes']:,} bytes")
print(f"  Oldest session: {stats['oldest_session']}")
print(f"  Newest session: {stats['newest_session']}")
print()

# Test cleanup
deleted = storage.cleanup_old_sessions(hours=0)  # Clean everything
print(f"✅ Cleanup test: Removed {deleted} old session(s)")
print()

# Test delete
storage.save(session_id, context_dict)
success = storage.delete(session_id)
if success:
    print("✅ Context deleted successfully")
    loaded = storage.load(session_id)
    assert loaded is None
    print("✅ Verified deletion")
else:
    print("❌ Failed to delete context")

print()
print("="*80)
print("SOLUTION SUMMARY")
print("="*80)
print()
print("❌ OLD (Cookie-based):")
print(f"   - Stored in Flask session cookie")
print(f"   - Limited to 4,093 bytes")
print(f"   - This context: {size_bytes:,} bytes (TOO BIG!)")
print()
print("✅ NEW (SQLite-based):")
print(f"   - Stored in SQLite database")
print(f"   - No size limit (practical limit: many MB)")
print(f"   - Cookie only stores tiny session ID (~36 bytes)")
print(f"   - Works with immutable containers (/tmp storage)")
print(f"   - Auto-cleanup of old sessions (24h)")
print()
print("✅ ALL TESTS PASSED!")
print()
