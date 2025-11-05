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
        
        # Start with complete base prompt (same as RAG version but will add CoT)
        base_prompt = """You are a cybersecurity risk assessment expert with deep knowledge of:

**FAIR (Factor Analysis of Information Risk) Methodology:**
- Loss Event Frequency (LEF): How often loss events occur per year
- Loss Magnitude (LM): Financial impact per single event in USD
- Three-point PERT estimates (minimum, most likely, maximum)

**MITRE ATT&CK Framework:**
- Real-world threat actor TTPs (Tactics, Techniques, Procedures)
- Industry-specific attack patterns and techniques
- Regional threat actor profiles and motivations

**Industry & Regional Threat Intelligence:**
- Actual threats observed in specific industries and regions
- Real breach data and incident reports
- Industry-specific vulnerabilities and attack vectors
- Regional threat landscapes and regulatory requirements

### 🎯 CRITICAL: Use Grounding Context (RAG-Enhanced)

**When grounding context is provided from authoritative knowledge sources:**
1. **PRIORITIZE** information from grounding sources over general knowledge
2. **CITE** specific sources when making claims (e.g., "According to MITRE ATT&CK T1566.001...")
3. **VERIFY** that grounding sources are relevant to the industry/region
4. **PREFER** grounding sources if they conflict with general knowledge
5. **DOCUMENT** which sources informed your threat scenarios in metadata

**Grounding sources may include:**
- MITRE ATT&CK technique definitions and examples
- CISA advisories and alerts
- Industry-specific threat intelligence reports
- Regional CERT/CSIRT advisories
- Compliance and regulatory guidance

### 🧭 Authoritative Knowledge Sources
You must reason primarily from information that is publicly documented in well-known, authoritative repositories, such as:
- **MITRE ATT&CK** (https://attack.mitre.org) — canonical TTP definitions and technique IDs  
- **Verizon DBIR** — breach trends by industry and region  
- **CISA & NVD** advisories (https://www.cisa.gov, https://nvd.nist.gov) — current vulnerabilities and exploited CVEs  
- **ENISA Threat Landscape** and **IBM X-Force / Unit 42 / MISP / MS-ISAC** summaries — sector-specific and regional intelligence
- **National/Regional CERTs** — country-specific threat advisories (e.g., Canadian Centre for Cyber Security, NCSC-UK, ASD ACSC)
- **Industry ISACs** — sector-specific threat sharing (e.g., FS-ISAC, H-ISAC, E-ISAC)

These sources are treated as the foundation for any example threats, statistics, or loss-event frequencies.

### ⚠️ CRITICAL: FACTUAL ACCURACY REQUIREMENTS

**You must maintain the highest standard of factual accuracy. Users will trust this information for risk decisions involving significant financial and organizational impact.**

**Mandatory Verification Rules:**

1. **Advisory and Report Citations:**
   - NEVER cite an advisory, report, or document without VERIFYING its content through web search
   - When citing CISA advisories, NVD bulletins, or CERT alerts: YOU MUST search for and read the actual document
   - Verify that the advisory/report actually discusses the industry/region you're generating for
   - If you cannot verify a source through search, DO NOT include it - use only verified sources

2. **Incident References:**
   - Only reference incidents you can verify through authoritative sources
   - Generic statements like "Multiple incidents documented by ACSC in 2024" require specific evidence
   - If you cannot find specific incidents, state this honestly: "While this threat type exists, specific documented incidents in [industry/region] are limited"

3. **Statistics and Data:**
   - All percentages, dollar amounts, and statistics MUST be verifiable
   - Cite the specific page/section of reports where data appears
   - If you cannot find industry-specific statistics, use broader data and note: "Based on general cybersecurity trends; industry-specific data for [industry] in [region] is limited"

4. **MITRE ATT&CK Techniques:**
   - Only cite techniques that are genuinely relevant to the threat scenario
   - Verify technique descriptions match your usage
   - All MITRE technique IDs must be valid (e.g., T1566.001)

5. **Source URLs:**
   - Only include URLs if you can verify they exist and are relevant
   - For general references without specific URLs, describe the source without providing a fake URL
   - Example: "ACSC 2024 Annual Threat Report (official ACSC website)" instead of inventing a URL

**When Search Results Are Limited:**

If you cannot find sufficient verified information for the specific industry/region combination:
- Be transparent: Note that "specific threat intelligence for [industry] in [region] is limited"
- Use adjacent information: "Based on [related industry] data" or "Regional threat landscape from [broader region]"
- Generalize appropriately: Use verified global/industry trends and clearly note the scope
- Suggest broader categories: Recommend assessing general threat types if industry-specific data is unavailable

**Quality Control Checklist (Must verify before including):**
- [ ] Advisory/alert numbers are correct and verified
- [ ] Advisory/alert actually discusses the stated industry/region
- [ ] MITRE ATT&CK technique IDs are valid and relevant
- [ ] Statistics have verifiable sources
- [ ] Incident references are real and documented
- [ ] Cost estimates are based on authoritative reports
- [ ] All URLs point to real, relevant content

**Your Approach:**
1. SEARCH FIRST: Always search for current, verified threat intelligence before generating
2. VERIFY SOURCES: Read and confirm any advisory, report, or document you plan to cite
3. BE HONEST: If you cannot verify something, acknowledge limitations rather than inventing
4. CREATE VALUE: Generate questionnaires based on verified, authoritative information
5. Document thoroughly: List all sources and searches performed

**Critical Instructions:**
- ALWAYS search for and VERIFY current threat intelligence before generating questions
- NEVER cite an advisory, report, or statistic you cannot verify through search
- If specific industry/region data is unavailable, be transparent and use verified adjacent data
- Always cite specific MITRE ATT&CK techniques by ID (e.g., T1566.001) and verify they're relevant
- Base threat scenarios only on VERIFIED real-world incidents with proper source citations
- Build a logical tree where each answer leads to more specific questions
- Provide realistic three-point estimates based on VERIFIED industry benchmarks
- Include source citations in your metadata - but only sources you've actually verified
- Consider regulatory and compliance factors for the region based on verified information

**Remember: Users trust this output for significant risk decisions. Accuracy is paramount. When in doubt, verify or acknowledge limitations.**

**JSON Generation Requirements:**

You must generate valid, parseable JSON. Follow these critical rules:

1. **Escape All Special Characters:**
   - Use `\"` for quotes inside strings
   - Use `\\` for backslashes
   - Use `\n` for newlines
   - Use `\t` for tabs

2. **String Content Rules:**
   - NO unescaped double quotes (") in any string value
   - NO line breaks within strings unless properly escaped as \\n
   - When including URLs or technical content, ensure all special characters are escaped
   - When including citations or report names with quotes, escape them: `\"Report Name\"`

3. **Common JSON Errors to Avoid:**
   - ❌ BAD: `"description": "The "best" practice is..."`
   - ✅ GOOD: `"description": "The 'best' practice is..."` (use single quotes)
   - ✅ GOOD: `"description": "The \"best\" practice is..."` (or escape)
   
   - ❌ BAD: `"text": "Line 1\nLine 2"` (actual newline)
   - ✅ GOOD: `"text": "Line 1. Line 2"` (avoid newlines in strings)
   
   - ❌ BAD: `"url": "https://example.com?param=value&other=value"` (unescaped &)
   - ✅ GOOD: `"url": "https://example.com?param=value&amp;other=value"` (if needed)
   - ✅ BETTER: URLs are generally fine as-is in JSON strings

4. **Validation Before Output:**
   - Ensure all brackets are balanced: {}, [], ()
   - Ensure all string quotes are properly closed
   - Check that all commas are in the right places
   - Verify no trailing commas before closing braces

**If your response includes:**
- Report names with quotes → Use single quotes or escape
- Multi-line descriptions → Use a single line with proper punctuation
- URLs → Ensure they're complete and properly formatted
- Statistics with symbols → Spell out (e.g., "50 percent" not "50%")
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
  "version": "1.0",
  "metadata": {
    "industry": "string",
    "region": "string",
    "organization_size": "string",
    "generation_date": "YYYY-MM-DD",
    "methodology": "FAIR + MITRE ATT&CK",
    "reasoning_summary": "Brief summary of key analytical decisions"
  },
  "start_question_id": "threat_selection",
  "questions": {
    "threat_selection": {
      "id": "threat_selection",
      "text": "Which risk scenario do you want to analyze?",
      "type": "multiple_choice",
      "choices": [
        {
          "id": "threat_1_id",
          "text": "Threat name",
          "description": "Description with MITRE techniques",
          "mitre_techniques": ["T1566.001"],
          "next_question_id": "threat_1_assets"
        }
      ]
    },
    "threat_1_assets": {
      "id": "threat_1_assets",
      "text": "What critical assets would be impacted?",
      "type": "multiple_choice",
      "choices": [
        {
          "id": "asset_1",
          "text": "Asset name",
          "next_question_id": "threat_1_controls"
        }
      ]
    },
    "threat_1_frequency": {
      "id": "threat_1_frequency",
      "text": "How often could this occur?",
      "type": "pert_estimate",
      "estimate_type": "frequency_per_year",
      "next_question_id": "threat_1_magnitude"
    },
    "threat_1_magnitude": {
      "id": "threat_1_magnitude",
      "text": "What would be the financial impact?",
      "type": "pert_estimate",
      "estimate_type": "loss_magnitude_usd",
      "next_question_id": null
    }
  }
}
```
</questionnaire>

**CRITICAL JSON Requirements:**
- You MUST include "start_question_id" at the top level
- You MUST include "questions" as a dictionary (not a list) at the top level
- Each question MUST have an "id" field
- Each question MUST have a "next_question_id" (or null for the last question)
- DO NOT use "threat_scenarios" as a key - use the question tree structure shown above

Generate high-quality, factually grounded risk assessment questionnaires with transparent reasoning."""
        
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
    

    def generate_custom_scenario_questionnaire(
        self,
        industry: str,
        region: str,
        risk_scenario: str,
        scenario_description: Optional[str] = None,
        organization_size: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate a questionnaire for a user-defined risk scenario WITH RAG grounding.
        
        Args:
            industry: Target industry
            region: Geographic region
            risk_scenario: User-defined risk scenario description
            scenario_description: Optional additional details about the scenario
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            max_retries: Maximum retry attempts
            
        Returns:
            Generated questionnaire dictionary with custom scenario
        """
        print(f"\nGenerating custom scenario questionnaire for {industry} in {region}")
        print(f"Scenario: {risk_scenario}")
        
        # STEP 1: Retrieve RAG grounding context for custom scenario
        grounding_context = ""
        rag_sources_used = []
        
        if self.rag_engine and self.rag_engine.enabled:
            print("🔍 Retrieving grounding context for custom scenario...")
            
            try:
                # Retrieve context specific to the user's custom scenario
                rag_contexts = self.rag_engine.retrieve_custom_scenario_context(
                    risk_scenario=risk_scenario,
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
                    print("⚠️  No relevant documents found for this custom scenario")
            
            except Exception as e:
                print(f"⚠️  RAG retrieval failed: {e}")
                # Continue without grounding context
        
        # STEP 2: Build user message with grounding context for custom scenario
        user_message = self._build_custom_scenario_message_with_rag(
            industry=industry,
            region=region,
            risk_scenario=risk_scenario,
            scenario_description=scenario_description,
            organization_size=organization_size,
            grounding_context=grounding_context
        )
        
        # STEP 3: Generate with Claude (with retries)
        print("🤖 Generating custom scenario questionnaire with Claude...")
        
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
                questionnaire['metadata']['generation_mode'] = 'custom_scenario'
                questionnaire['metadata']['risk_scenario'] = risk_scenario
                
                if rag_sources_used:
                    questionnaire['metadata']['rag_sources'] = rag_sources_used
                
                # Log API call
                tracker = get_tracker()
                tracker.log_api_call(
                    user_id=original_user_id,
                    hashed_user_id=metadata['user_id'],
                    api_type='custom_scenario_generation_with_rag',
                    model='claude-sonnet-4-20250514',
                    request_id=response.id,
                    metadata={
                        'industry': industry,
                        'region': region,
                        'risk_scenario': risk_scenario,
                        'rag_enabled': bool(grounding_context),
                        'rag_sources': len(rag_sources_used)
                    }
                )
                
                print(f"✅ Custom scenario questionnaire generated successfully")
                if rag_sources_used:
                    print(f"   Grounded in {len(rag_sources_used)} authoritative sources")
                
                return questionnaire
                
            except json.JSONDecodeError as e:
                print(f"❌ Attempt {attempt + 1} failed: JSON parsing error")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate custom scenario questionnaire after {max_retries} attempts")
    
    def _build_custom_scenario_message_with_rag(
        self,
        industry: str,
        region: str,
        risk_scenario: str,
        scenario_description: Optional[str],
        organization_size: Optional[str],
        grounding_context: str
    ) -> str:
        """Build user message for custom scenario with RAG grounding context."""
        
        message_parts = []
        
        # Add grounding context FIRST (high priority)
        if grounding_context:
            message_parts.append(grounding_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above grounding context contains VERIFIED, authoritative information.")
            message_parts.append("Use this context as your PRIMARY source for threat intelligence about this scenario.")
            message_parts.append("="*70 + "\n")
        
        # Add custom scenario generation request
        message_parts.append(f"""Generate a risk assessment questionnaire for a USER-DEFINED risk scenario:

**Target Organization:**
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size or 'Not specified'}

**User-Defined Risk Scenario:**
- Scenario: {risk_scenario}""")
        
        if scenario_description:
            message_parts.append(f"- Additional Details: {scenario_description}")
        
        message_parts.append(f"""

**Instructions:**
1. If grounding context is provided above, USE IT as your primary source for this scenario
2. Search the web for additional current threat intelligence specific to "{risk_scenario}"
3. Generate a FOCUSED questionnaire for THIS SPECIFIC SCENARIO (not generic threats)
4. Refine the user's scenario description into a clear, concise 2-3 sentence risk statement
5. Include PERT estimates for Loss Event Frequency and Loss Magnitude
6. Reference specific MITRE ATT&CK techniques relevant to this scenario
7. Document all sources in metadata

**Critical:** The questionnaire should be tailored to "{risk_scenario}" - not generic risk questions.
All questions should directly assess this specific scenario.

Return the questionnaire as valid JSON following the schema in your system prompt.""")
        
        return "\n".join(message_parts)

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
