"""
Example integration of Vertex AI RAG into AI Question Generator.

This shows how to add RAG grounding context to the questionnaire generation process.
"""

import os
import json
import anthropic
from typing import Dict, List, Optional
from user_tracking import get_tracker, create_api_metadata
from vertex_rag_complete import get_rag_engine


class AIQuestionGeneratorWithRAG:
    """
    AI Question Generator with RAG grounding context.
    
    Key Changes from Original:
    1. Retrieves grounding context from RAG corpus before generation
    2. Injects verified threat intelligence into prompts
    3. Tracks RAG sources in metadata
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_rag: bool = True):
        """
        Initialize the question generator with RAG support.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            enable_rag: Enable RAG grounding (default: True)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.enable_rag = enable_rag
        
        # Initialize RAG engine if enabled
        if self.enable_rag:
            self.rag_engine = get_rag_engine(enable_fallback=True)
            if self.rag_engine.enabled:
                print("✅ RAG grounding enabled")
            else:
                print("⚠️  RAG grounding disabled (fallback mode)")
        else:
            self.rag_engine = None
            print("ℹ️  RAG grounding disabled by configuration")
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt (same as original, but emphasizes grounding sources)."""
        return """You are a cybersecurity risk assessment expert with deep knowledge of:

**FAIR (Factor Analysis of Information Risk) Methodology:**
- Loss Event Frequency (LEF): How often loss events occur per year
- Loss Magnitude (LM): Financial impact per single event in USD
- Three-point PERT estimates (minimum, most likely, maximum)

**MITRE ATT&CK Framework:**
- Real-world threat actor TTPs (Tactics, Techniques, Procedures)
- Industry-specific attack patterns and techniques
- Regional threat actor profiles and motivations

**CRITICAL: Use Grounding Context**

When grounding context is provided from authoritative knowledge sources:
1. PRIORITIZE information from grounding sources over general knowledge
2. CITE specific sources when making claims (e.g., "According to CISA advisory...")
3. VERIFY that grounding sources are relevant to the industry/region
4. If grounding context conflicts with general knowledge, PREFER grounding sources
5. Document which sources informed your threat scenarios

**Quality Requirements:**
- All threat scenarios must reference VERIFIED sources (either grounding context or web search)
- MITRE ATT&CK technique IDs must be accurate and relevant
- Statistics must be traceable to authoritative reports
- Be transparent about data limitations

Generate high-quality, factually grounded risk assessment questionnaires.

[Rest of system prompt follows same structure as original...]
"""
    
    def generate_questionnaire(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate risk assessment questionnaire WITH RAG grounding.
        
        Args:
            industry: Target industry
            region: Geographic region
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            max_retries: Maximum retry attempts
            
        Returns:
            Generated questionnaire dictionary
        """
        print(f"\nGenerating questionnaire for {industry} in {region}")
        
        # STEP 1: Retrieve RAG grounding context
        grounding_context = ""
        rag_sources_used = []
        
        if self.rag_engine and self.rag_engine.enabled:
            print("🔍 Retrieving grounding context from knowledge base...")
            
            try:
                rag_contexts = self.rag_engine.retrieve_risk_identification_context(
                    industry=industry,
                    region=region,
                    organization_size=organization_size,
                    max_results=5
                )
                
                if rag_contexts:
                    print(f"✅ Retrieved {len(rag_contexts)} relevant documents")
                    
                    # Format for prompt
                    grounding_context = self.rag_engine.format_context_for_prompt(rag_contexts)
                    
                    # Track sources for metadata
                    rag_sources_used = [
                        {
                            'source': ctx.source,
                            'relevance': ctx.relevance_score,
                            'content_preview': ctx.content[:200]
                        }
                        for ctx in rag_contexts
                    ]
                else:
                    print("⚠️  No relevant documents found in knowledge base")
            
            except Exception as e:
                print(f"⚠️  RAG retrieval failed: {e}")
                # Continue without grounding context
        
        # STEP 2: Build user message with grounding context
        user_message = self._build_user_message_with_rag(
            industry=industry,
            region=region,
            organization_size=organization_size,
            grounding_context=grounding_context
        )
        
        # STEP 3: Generate with Claude (with retries)
        print("🤖 Generating questionnaire with Claude...")
        
        for attempt in range(max_retries):
            try:
                # Get user tracking metadata
                metadata = create_api_metadata(user_id)
                original_user_id = metadata.pop('_original_user_id')
                
                # Call Claude API
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16000,
                    system=self.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_message
                    }],
                    metadata=metadata
                )
                
                # Parse response
                response_text = response.content[0].text
                
                # Extract JSON
                questionnaire = self._extract_json(response_text)
                
                # Add RAG metadata
                if 'metadata' not in questionnaire:
                    questionnaire['metadata'] = {}
                
                questionnaire['metadata']['rag_grounding_enabled'] = bool(grounding_context)
                questionnaire['metadata']['rag_sources_count'] = len(rag_sources_used)
                
                if rag_sources_used:
                    questionnaire['metadata']['rag_sources'] = rag_sources_used
                
                # Log API call
                tracker = get_tracker()
                tracker.log_api_call(
                    user_id=original_user_id,
                    hashed_user_id=metadata['user_id'],
                    api_type='questionnaire_generation_with_rag',
                    model='claude-sonnet-4-20250514',
                    request_id=response.id,
                    metadata={
                        'industry': industry,
                        'region': region,
                        'rag_enabled': bool(grounding_context),
                        'rag_sources': len(rag_sources_used)
                    }
                )
                
                print(f"✅ Questionnaire generated successfully")
                if rag_sources_used:
                    print(f"   Grounded in {len(rag_sources_used)} authoritative sources")
                
                return questionnaire
                
            except json.JSONDecodeError as e:
                print(f"❌ Attempt {attempt + 1} failed: JSON parsing error")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate questionnaire after {max_retries} attempts")
    
    def _build_user_message_with_rag(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str],
        grounding_context: str
    ) -> str:
        """Build user message with RAG grounding context injected."""
        
        message_parts = []
        
        # Add grounding context FIRST (high priority)
        if grounding_context:
            message_parts.append(grounding_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above grounding context contains VERIFIED, authoritative information.")
            message_parts.append("Use this context as your PRIMARY source for threat intelligence.")
            message_parts.append("="*70 + "\n")
        
        # Add generation request
        message_parts.append(f"""Generate a risk assessment questionnaire for:

**Target Organization:**
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size or 'Not specified'}

**Instructions:**
1. If grounding context is provided above, USE IT as your primary source
2. Search the web for additional current threat intelligence if needed
3. Generate 3-5 threat scenarios relevant to this industry/region
4. Include PERT estimates for Loss Event Frequency and Loss Magnitude
5. Reference specific MITRE ATT&CK techniques
6. Document all sources in metadata

Return the questionnaire as valid JSON following the schema in your system prompt.
""")
        
        return "\n".join(message_parts)
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from response text."""
        # Try to find JSON in code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_text = text[start:end].strip()
        else:
            json_text = text.strip()
        
        return json.loads(json_text)


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("AI Question Generator with RAG Integration Test")
    print("="*70)
    
    try:
        # Initialize generator with RAG
        generator = AIQuestionGeneratorWithRAG(enable_rag=True)
        
        # Generate questionnaire
        questionnaire = generator.generate_questionnaire(
            industry="Healthcare",
            region="Canada",
            organization_size="500 employees"
        )
        
        # Display results
        print("\n" + "="*70)
        print("GENERATED QUESTIONNAIRE")
        print("="*70)
        
        print(f"\nIndustry: {questionnaire['metadata']['industry']}")
        print(f"Region: {questionnaire['metadata']['region']}")
        print(f"Questions: {len(questionnaire.get('questions', {}))}")
        
        # Show RAG integration
        if questionnaire['metadata'].get('rag_grounding_enabled'):
            print(f"\n✅ RAG Grounding: ENABLED")
            print(f"   Sources used: {questionnaire['metadata'].get('rag_sources_count', 0)}")
            
            if 'rag_sources' in questionnaire['metadata']:
                print(f"\n   Top sources:")
                for i, source in enumerate(questionnaire['metadata']['rag_sources'][:3], 1):
                    print(f"   {i}. {source['source']} (relevance: {source['relevance']:.2f})")
        else:
            print(f"\n⚠️  RAG Grounding: DISABLED")
        
        # Save to file
        filename = f"questionnaire_with_rag_test.json"
        with open(filename, 'w') as f:
            json.dump(questionnaire, f, indent=2)
        
        print(f"\n✅ Saved to {filename}")
        
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease set required environment variables:")
        print("  - ANTHROPIC_API_KEY")
        print("  - GOOGLE_CLOUD_PROJECT (for RAG)")
        print("  - VERTEX_RAG_CORPUS (for RAG)")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
