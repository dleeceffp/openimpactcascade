"""
Example integration of Vertex AI RAG into AI Question Generator with Chain-of-Thought.

This shows how to add RAG grounding context AND chain-of-thought reasoning
to the questionnaire generation process for improved accuracy and transparency.
"""

import os
import json
import anthropic
from typing import Dict, List, Optional, Tuple
from user_tracking import get_tracker, create_api_metadata
from vertex_rag_complete import get_rag_engine


class AIQuestionGeneratorWithRAGAndCoT:
    """
    AI Question Generator with RAG grounding context and Chain-of-Thought reasoning.
    
    Key Enhancements from Original:
    1. Retrieves grounding context from RAG corpus before generation
    2. Injects verified threat intelligence into prompts
    3. Uses Chain-of-Thought prompting for transparent reasoning
    4. Extracts and validates reasoning before accepting outputs
    5. Tracks both RAG sources and reasoning steps in metadata
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        enable_rag: bool = True, 
        enable_cot: bool = True,
        max_output_tokens: int = 24000
    ):
        """
        Initialize the question generator with RAG and CoT support.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            enable_rag: Enable RAG grounding (default: True)
            enable_cot: Enable Chain-of-Thought reasoning (default: True)
            max_output_tokens: Maximum tokens for Claude's response (default: 24000)
                              - Without CoT: 8,000-12,000 is sufficient
                              - With CoT: 20,000-30,000 recommended
                              - Complex multi-scenario: 30,000+ may be needed
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.enable_rag = enable_rag
        self.enable_cot = enable_cot
        self.max_output_tokens = max_output_tokens
        
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
        
        if self.enable_cot:
            print("✅ Chain-of-Thought reasoning enabled")
        else:
            print("ℹ️  Chain-of-Thought reasoning disabled")
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with CoT reasoning instructions."""
        
        base_prompt = """You are a cybersecurity risk assessment expert with deep knowledge of:

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
"""
        
        if self.enable_cot:
            base_prompt += """

**CRITICAL: Use Chain-of-Thought Reasoning**

You MUST show your analytical reasoning process:

1. SOURCE EVALUATION REASONING:
   - Analyze each grounding source for relevance and authority
   - Identify key facts, statistics, and threat intelligence
   - Note any conflicting information and resolve it
   - Explain which sources are most credible and why

2. THREAT PRIORITIZATION REASONING:
   - Explain why you selected each threat scenario
   - Show how probability and impact assessments were derived
   - Connect threats to specific evidence in sources
   - Justify MITRE ATT&CK technique selections

3. PARAMETER ESTIMATION REASONING:
   - Explain the basis for each LEF estimate (min/likely/max)
   - Show how loss magnitude ranges were calculated
   - Reference comparable incidents or industry benchmarks
   - State assumptions and uncertainties explicitly

4. QUALITY VALIDATION:
   - Verify all claims trace to specific sources
   - Check MITRE technique IDs for accuracy
   - Ensure estimates are reasonable and evidence-based
   - Flag any gaps or limitations in available data

Your reasoning must be thorough, transparent, and traceable to sources.
"""
        
        base_prompt += """

**Quality Requirements:**
- All threat scenarios must reference VERIFIED sources (either grounding context or web search)
- MITRE ATT&CK technique IDs must be accurate and relevant
- Statistics must be traceable to authoritative reports
- Be transparent about data limitations
- Never fabricate sources or statistics

**Output Format:**

Structure your response as:

<reasoning>
[Your detailed analytical reasoning - be thorough and show all steps]
</reasoning>

<questionnaire>
```json
{
  "metadata": {
    "industry": "string",
    "region": "string",
    "organization_size": "string",
    "generation_date": "YYYY-MM-DD",
    "methodology": "FAIR + MITRE ATT&CK",
    "reasoning_summary": "Brief summary of key analytical decisions"
  },
  "questions": {
    "threat_scenarios": [
      {
        "id": "T1",
        "scenario": "Threat scenario description",
        "threat_actor": "Actor type and motivation",
        "mitre_techniques": ["T1566.001", "T1486"],
        "lef_estimates": {
          "min": 0.5,
          "most_likely": 2,
          "max": 5,
          "unit": "events per year",
          "justification": "Explanation of estimates"
        },
        "lm_estimates": {
          "min": 50000,
          "most_likely": 250000,
          "max": 1000000,
          "unit": "USD per event",
          "justification": "Explanation of estimates"
        },
        "sources": ["Source 1", "Source 2"]
      }
    ]
  }
}
```
</questionnaire>

Generate high-quality, factually grounded risk assessment questionnaires with transparent reasoning.
"""
        
        return base_prompt
    
    def generate_questionnaire(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate risk assessment questionnaire WITH RAG grounding and CoT reasoning.
        
        Args:
            industry: Target industry
            region: Geographic region
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            max_retries: Maximum retry attempts
            
        Returns:
            Generated questionnaire dictionary with reasoning metadata
        """
        print(f"\nGenerating questionnaire for {industry} in {region}")
        if self.enable_cot:
            print("   Using Chain-of-Thought reasoning for transparency")
        
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
        
        # STEP 2: Build user message with grounding context and CoT instructions
        user_message = self._build_user_message_with_rag_and_cot(
            industry=industry,
            region=region,
            organization_size=organization_size,
            grounding_context=grounding_context
        )
        
        # STEP 3: Generate with Claude (with retries)
        print("🤖 Generating questionnaire with Claude...")
        if self.enable_cot:
            print("   Requesting detailed reasoning...")
        
        for attempt in range(max_retries):
            try:
                # Get user tracking metadata
                metadata = create_api_metadata(user_id)
                original_user_id = metadata.pop('_original_user_id')
                
                # Call Claude API
                # Note: max_output_tokens for CoT reasoning (typically uses 4,000-7,000 tokens)
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=self.max_output_tokens,
                    system=self.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_message
                    }],
                    metadata=metadata
                )
                
                # Parse response
                response_text = response.content[0].text
                
                # Track token usage
                token_usage = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
                    'max_output_tokens': self.max_output_tokens,
                    'output_utilization': f"{(response.usage.output_tokens / self.max_output_tokens * 100):.1f}%"
                }
                
                print(f"   📊 Token usage: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
                print(f"   📈 Output utilization: {token_usage['output_utilization']} of max")
                
                if response.usage.output_tokens > self.max_output_tokens * 0.9:
                    print(f"   ⚠️  WARNING: Output near token limit! Consider increasing max_output_tokens")
                
                # Extract reasoning and JSON (CoT-aware)
                if self.enable_cot:
                    reasoning, questionnaire = self._extract_reasoning_and_json(response_text)
                    
                    # Validate reasoning quality
                    reasoning_quality = self._validate_reasoning(reasoning, rag_sources_used)
                    print(f"   Reasoning quality: {reasoning_quality['score']:.1f}/10")
                    
                    if reasoning_quality['score'] < 5.0:
                        print(f"   ⚠️  Low reasoning quality: {reasoning_quality['issues']}")
                else:
                    reasoning = None
                    questionnaire = self._extract_json(response_text)
                
                # Add RAG and CoT metadata
                if 'metadata' not in questionnaire:
                    questionnaire['metadata'] = {}
                
                questionnaire['metadata']['rag_grounding_enabled'] = bool(grounding_context)
                questionnaire['metadata']['rag_sources_count'] = len(rag_sources_used)
                questionnaire['metadata']['cot_reasoning_enabled'] = self.enable_cot
                questionnaire['metadata']['token_usage'] = token_usage
                
                if rag_sources_used:
                    questionnaire['metadata']['rag_sources'] = rag_sources_used
                
                if self.enable_cot and reasoning:
                    questionnaire['metadata']['generation_reasoning'] = reasoning
                    questionnaire['metadata']['reasoning_quality'] = reasoning_quality
                
                # Log API call
                tracker = get_tracker()
                tracker.log_api_call(
                    user_id=original_user_id,
                    hashed_user_id=metadata['user_id'],
                    api_type='questionnaire_generation_with_rag_cot',
                    model='claude-sonnet-4-20250514',
                    request_id=response.id,
                    metadata={
                        'industry': industry,
                        'region': region,
                        'rag_enabled': bool(grounding_context),
                        'rag_sources': len(rag_sources_used),
                        'cot_enabled': self.enable_cot,
                        'reasoning_quality': reasoning_quality.get('score', 0) if self.enable_cot else None
                    }
                )
                
                print(f"✅ Questionnaire generated successfully")
                if rag_sources_used:
                    print(f"   Grounded in {len(rag_sources_used)} authoritative sources")
                if self.enable_cot and reasoning:
                    print(f"   Reasoning steps documented ({len(reasoning.split())} words)")
                
                return questionnaire
                
            except json.JSONDecodeError as e:
                print(f"❌ Attempt {attempt + 1} failed: JSON parsing error")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
            except ValueError as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate questionnaire after {max_retries} attempts")
    
    def _build_user_message_with_rag_and_cot(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str],
        grounding_context: str
    ) -> str:
        """Build user message with RAG grounding context and CoT instructions."""
        
        message_parts = []
        
        # Add grounding context FIRST (high priority)
        if grounding_context:
            message_parts.append(grounding_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above grounding context contains VERIFIED, authoritative information.")
            message_parts.append("Use this context as your PRIMARY source for threat intelligence.")
            message_parts.append("="*70 + "\n")
        
        # Add generation request with CoT instructions
        if self.enable_cot:
            message_parts.append(f"""Generate a risk assessment questionnaire for:

**Target Organization:**
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size or 'Not specified'}

**APPROACH: Use Chain-of-Thought Reasoning**

═══════════════════════════════════════════════════════════════════
PHASE 1: ANALYZE THE THREAT LANDSCAPE (Show your reasoning)
═══════════════════════════════════════════════════════════════════

Review the grounding context (if provided) and think through:

1. SOURCE EVALUATION:
   - Which sources are most authoritative for {industry} in {region}?
   - What are the 5-7 most relevant threats mentioned?
   - Are there any conflicting claims? If so, which source is more credible and why?
   - What key statistics or facts are most reliable?

2. REGIONAL & INDUSTRY CONTEXT:
   - What makes {industry} particularly vulnerable?
   - What {region}-specific factors increase or decrease risk?
   - What recent incidents in {industry}/{region} set precedent?
   - Are there regulatory or compliance factors to consider?

3. THREAT ACTOR ANALYSIS:
   - Which threat actors typically target {industry}?
   - What are their motivations (financial, espionage, disruption)?
   - What are their typical TTPs based on the grounding sources?
   - How sophisticated are these actors?

═══════════════════════════════════════════════════════════════════
PHASE 2: PRIORITIZE TOP 3-5 SCENARIOS (Explain your choices)
═══════════════════════════════════════════════════════════════════

For each scenario you select, explain:

a) WHY THIS SCENARIO?
   - What evidence suggests high probability for {industry}?
   - What evidence suggests high impact for organizations of this size?
   - Which specific source(s) support this scenario?
   - How does this compare to other potential scenarios?

b) MITRE ATT&CK MAPPING:
   - Which techniques apply (use specific IDs like T1566.001)?
   - Why are these techniques relevant to this scenario?
   - What attack chain or sequence do they form?
   - Are there industry-specific variations?

c) PARAMETER JUSTIFICATION:
   - LEF (Loss Event Frequency): 
     * Why this minimum value per year?
     * Why this most likely value?
     * Why this maximum value?
     * What comparable data supports these estimates?
   
   - LM (Loss Magnitude):
     * Why this minimum loss amount?
     * Why this most likely loss amount?
     * Why this maximum loss amount?
     * What incident data or benchmarks inform these ranges?

d) UNCERTAINTY & LIMITATIONS:
   - What assumptions are you making?
   - Where is data limited or unavailable?
   - What would you need to refine these estimates?

═══════════════════════════════════════════════════════════════════
PHASE 3: GENERATE QUESTIONNAIRE JSON
═══════════════════════════════════════════════════════════════════

Based on your Phase 1-2 analysis, generate the final questionnaire.

**STRUCTURE YOUR RESPONSE EXACTLY AS:**

<reasoning>
[Your detailed Phase 1 & 2 analysis here - be thorough and explicit]

PHASE 1 ANALYSIS:
[Source evaluation, regional context, threat actors...]

PHASE 2 SCENARIO PRIORITIZATION:
[For each of 3-5 scenarios: justification, MITRE mapping, parameter reasoning...]
</reasoning>

<questionnaire>
```json
{{
  "metadata": {{
    "industry": "{industry}",
    "region": "{region}",
    "organization_size": "{organization_size or 'Not specified'}",
    "generation_date": "2025-11-02",
    "methodology": "FAIR + MITRE ATT&CK",
    "reasoning_summary": "2-3 sentence summary of your key analytical decisions"
  }},
  "questions": {{
    "threat_scenarios": [
      {{
        "id": "T1",
        "scenario": "Clear description of the threat",
        "threat_actor": "Actor profile and motivation",
        "mitre_techniques": ["T1566.001", "T1486"],
        "lef_estimates": {{
          "min": 0.5,
          "most_likely": 2,
          "max": 5,
          "unit": "events per year",
          "justification": "Brief explanation referencing sources"
        }},
        "lm_estimates": {{
          "min": 50000,
          "most_likely": 250000,
          "max": 1000000,
          "unit": "USD per event",
          "justification": "Brief explanation referencing sources"
        }},
        "sources": ["Specific source citations"]
      }}
    ]
  }}
}}
```
</questionnaire>

**QUALITY CHECKS BEFORE SUBMITTING:**
- ✓ Every scenario traces to specific sources
- ✓ Every MITRE technique ID is accurate and relevant
- ✓ Every estimate has stated justification
- ✓ Reasoning is transparent and verifiable
- ✓ Limitations and uncertainties are explicitly noted
""")
        else:
            # Original simpler instructions without CoT
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
    
    def _extract_reasoning_and_json(self, text: str) -> Tuple[str, Dict]:
        """Extract both reasoning and final JSON from CoT response."""
        
        reasoning = ""
        if "<reasoning>" in text and "</reasoning>" in text:
            start = text.find("<reasoning>") + 11
            end = text.find("</reasoning>")
            reasoning = text[start:end].strip()
            print(f"   ✅ Extracted reasoning ({len(reasoning)} chars)")
        else:
            print(f"   ⚠️  No <reasoning> tags found in response")
        
        # Extract JSON from questionnaire block
        try:
            if "<questionnaire>" in text:
                json_section = text[text.find("<questionnaire>"):]
                
                if "```json" in json_section:
                    start = json_section.find("```json") + 7
                    end = json_section.find("```", start)
                    json_text = json_section[start:end].strip()
                elif "```" in json_section:
                    start = json_section.find("```") + 3
                    end = json_section.find("```", start)
                    json_text = json_section[start:end].strip()
                else:
                    # Try to find JSON object directly
                    start = json_section.find("{")
                    if start != -1:
                        # Find matching closing brace
                        brace_count = 0
                        for i, char in enumerate(json_section[start:], start):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_text = json_section[start:i+1]
                                    break
                    else:
                        raise ValueError("No JSON found in <questionnaire> block")
            else:
                # Fallback to original extraction method
                json_text = self._extract_json_fallback(text)
            
            questionnaire = json.loads(json_text)
            print(f"   ✅ Parsed questionnaire JSON")
            
            return reasoning, questionnaire
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ❌ JSON parsing failed: {e}")
            raise
    
    def _extract_json_fallback(self, text: str) -> str:
        """Fallback JSON extraction (original method)."""
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
        
        return json_text
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from response text (original method for backward compatibility)."""
        json_text = self._extract_json_fallback(text)
        return json.loads(json_text)
    
    def _validate_reasoning(self, reasoning: str, rag_sources: List[Dict]) -> Dict:
        """
        Validate the quality of Chain-of-Thought reasoning.
        
        Returns a quality score and identified issues.
        """
        if not reasoning:
            return {
                'score': 0.0,
                'issues': ['No reasoning provided']
            }
        
        score = 10.0
        issues = []
        
        # Check for phase structure
        if "PHASE 1" not in reasoning or "PHASE 2" not in reasoning:
            score -= 2.0
            issues.append("Missing phase structure")
        
        # Check for source citations
        if rag_sources and not any(src['source'] in reasoning for src in rag_sources):
            score -= 2.0
            issues.append("No RAG sources cited in reasoning")
        
        # Check for MITRE references
        if "T1" not in reasoning and "MITRE" not in reasoning:
            score -= 1.5
            issues.append("Limited MITRE ATT&CK analysis")
        
        # Check for parameter justification keywords
        justification_keywords = ['because', 'based on', 'according to', 'estimate', 'frequency']
        if not any(kw in reasoning.lower() for kw in justification_keywords):
            score -= 2.0
            issues.append("Insufficient parameter justification")
        
        # Check reasoning length (should be substantial for complex analysis)
        word_count = len(reasoning.split())
        if word_count < 200:
            score -= 1.5
            issues.append(f"Reasoning too brief ({word_count} words)")
        
        # Check for uncertainty acknowledgment
        uncertainty_keywords = ['uncertain', 'limited data', 'assumption', 'estimate', 'approximately']
        if not any(kw in reasoning.lower() for kw in uncertainty_keywords):
            score -= 1.0
            issues.append("No uncertainty acknowledgment")
        
        return {
            'score': max(0.0, score),
            'issues': issues if issues else ['None - reasoning quality is good']
        }


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("AI Question Generator with RAG + Chain-of-Thought Integration Test")
    print("="*70)
    
    try:
        # Initialize generator with RAG and CoT
        generator = AIQuestionGeneratorWithRAGAndCoT(
            enable_rag=True,
            enable_cot=True,
            max_output_tokens=24000  # Adjust based on expected reasoning complexity
        )
        
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
        print(f"Questions: {len(questionnaire.get('questions', {}).get('threat_scenarios', []))}")
        
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
        
        # Show CoT integration
        if questionnaire['metadata'].get('cot_reasoning_enabled'):
            print(f"\n✅ Chain-of-Thought: ENABLED")
            
            if 'generation_reasoning' in questionnaire['metadata']:
                reasoning = questionnaire['metadata']['generation_reasoning']
                print(f"   Reasoning captured: {len(reasoning)} characters")
                print(f"   Word count: {len(reasoning.split())} words")
                
                # Show reasoning quality
                if 'reasoning_quality' in questionnaire['metadata']:
                    quality = questionnaire['metadata']['reasoning_quality']
                    print(f"   Quality score: {quality['score']:.1f}/10")
                    if quality['score'] < 8.0:
                        print(f"   Issues: {', '.join(quality['issues'])}")
                
                # Show reasoning preview
                print(f"\n   Reasoning preview (first 500 chars):")
                print(f"   {'-'*66}")
                preview = reasoning[:500].replace('\n', '\n   ')
                print(f"   {preview}...")
        else:
            print(f"\n⚠️  Chain-of-Thought: DISABLED")
        
        # Show reasoning summary if available
        if 'reasoning_summary' in questionnaire['metadata']:
            print(f"\n📋 Reasoning Summary:")
            print(f"   {questionnaire['metadata']['reasoning_summary']}")
        
        # Save to file
        filename = f"questionnaire_with_rag_cot_test.json"
        with open(filename, 'w') as f:
            json.dump(questionnaire, f, indent=2)
        
        print(f"\n✅ Saved to {filename}")
        
        # Save reasoning separately for easy review
        if 'generation_reasoning' in questionnaire['metadata']:
            reasoning_filename = f"questionnaire_reasoning_test.txt"
            with open(reasoning_filename, 'w') as f:
                f.write("="*70 + "\n")
                f.write("CHAIN-OF-THOUGHT REASONING\n")
                f.write("="*70 + "\n\n")
                f.write(questionnaire['metadata']['generation_reasoning'])
            print(f"✅ Reasoning saved to {reasoning_filename}")
        
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
