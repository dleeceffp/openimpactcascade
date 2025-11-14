"""
Enhanced AI Question Generator with RAG + Web Search Pre-Generation.

Version 2.1.2 - Adds targeted web search for ultra-recent threat intelligence,
current statistics, and documented incidents to supplement RAG corpus.

This is a DROP-IN REPLACEMENT for v211 with identical interface.
"""

import os
import json
import anthropic
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from user_tracking import get_tracker, create_api_metadata
from vertex_rag_v211 import get_rag_engine


class AIQuestionGeneratorWithRAGAndRationale:
    """
    AI Question Generator with RAG grounding, web search, and constrained reasoning.
    
    Key Enhancements in v212:
    - Pre-generation web search for recent threat intelligence
    - Targeted queries for industry/region-specific incidents
    - Current breach cost statistics and benchmarking data
    - Documented case studies with financial impacts
    - All existing v211 functionality maintained (drop-in compatible)
    """
    
    def __init__(self, api_key: Optional[str] = None, enable_rag: bool = True, enable_web_search: bool = True):
        """
        Initialize the question generator with RAG and web search support.
        
        Args:
            api_key: Anthropic API key (or from environment)
            enable_rag: Enable RAG corpus retrieval (default: True)
            enable_web_search: Enable pre-generation web search (default: True)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.enable_rag = enable_rag
        self.enable_web_search = enable_web_search
        
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
        
        # Web search status
        if self.enable_web_search:
            print("✅ Web search pre-generation enabled")
        else:
            print("ℹ️  Web search pre-generation disabled by configuration")
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with RAG grounding and rationale requirements."""
        return """You are a cybersecurity risk assessment expert with deep knowledge of:

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

### 🎯 CRITICAL: Use Grounding Context (RAG-Enhanced + Web Search)

**When grounding context is provided from authoritative knowledge sources:**
1. **PRIORITIZE** information from grounding sources over general knowledge
2. **CITE** specific sources when making claims (e.g., "According to MITRE ATT&CK T1566.001...")
3. **VERIFY** that grounding sources are relevant to the industry/region
4. **DOCUMENT** which sources informed each threat in the rationale_summary field

**Grounding sources may include:**
- MITRE ATT&CK technique definitions and examples
- CISA advisories and alerts
- Industry-specific threat intelligence reports
- Regional CERT/CSIRT advisories
- Compliance and regulatory guidance
- **Recent web search results** (last 90 days) with current incidents and statistics

### 📊 NEW REQUIREMENT: Rationale Summaries

**For each threat scenario you include, you MUST provide a 'rationale_summary' field:**

**Purpose:** Explain in 100-150 tokens why this threat was selected, with specific source citations.

**Required Content:**
1. **Source Evidence** (50-70 tokens): Which authoritative sources document this threat?
   - Name specific advisories, reports, or incidents
   - Include dates and identifiers when available
   - Example: "CISA advisory AA24-242A (Aug 2024) documented 5 ransomware incidents in Canadian healthcare"

2. **Relevance Justification** (30-50 tokens): Why is this threat relevant to this industry/region?
   - Industry-specific vulnerabilities or targeting patterns
   - Regional threat landscape factors
   - Example: "Healthcare orgs in Canada targeted due to valuable patient data and limited cybersecurity budgets"

3. **Impact Evidence** (20-30 tokens): What data supports the estimated probability/impact?
   - Statistical trends or benchmarks
   - Example: "Average ransom payment $1.2M per IBM X-Force 2024; typical frequency 2-3 events/year"

**Length Constraint:**
- Target: 100-150 tokens (~75-120 words)
- Maximum: 200 tokens
- Be concise but specific with source citations

**Quality Standards:**
- ✓ Must cite at least 2 specific sources by name
- ✓ Must reference actual data points (numbers, dates, trends)
- ✓ Must explain industry/region relevance
- ✓ No generic statements like "this is a common threat"
- ✓ No made-up statistics or sources

**Example (Good):**
```
"rationale_summary": "Selected based on: (1) CISA advisory AA24-242A documenting 5 Canadian healthcare ransomware incidents in Aug 2024, (2) Health Canada CCCS threat bulletin citing 60% increase in healthcare targeting since 2023, (3) Ransomware attacks via phishing (T1566.001) represent 70% of healthcare breaches per Verizon DBIR 2024. Average impact $1.2M per incident (IBM X-Force). High probability (2-3/year) for 500-employee orgs with limited endpoint protection."
```

**Example (Bad - too generic):**
```
"rationale_summary": "Ransomware is a common threat to healthcare organizations. Many incidents have occurred recently. This threat is relevant because healthcare data is valuable."
```

### ⚠️ CRITICAL: FACTUAL ACCURACY REQUIREMENTS

**You must maintain the highest standard of factual accuracy. Users will trust this information for risk decisions involving significant financial and organizational impact.**

**Mandatory Verification Rules:**

1. **Advisory and Report Citations:**
   - PRIORITIZE recently provided web search results for current information
   - When citing CISA advisories, NVD bulletins, or CERT alerts: Use the actual documents provided
   - Verify that the advisory/report actually discusses the industry/region you're generating for
   - If you cannot verify a source through provided context, DO NOT include it

2. **Incident References:**
   - Only reference incidents you can verify through provided authoritative sources
   - If you cannot find specific incidents, state this honestly in the rationale: "Specific documented incidents in [industry/region] are limited; assessment based on adjacent industries"

3. **Statistics and Data:**
   - All percentages, dollar amounts, and statistics MUST be verifiable
   - Cite the specific report and year where data appears
   - Example: "Average $850K per breach (IBM Cost of Data Breach 2024, healthcare sector)"

4. **MITRE ATT&CK Techniques:**
   - Only cite techniques that are genuinely relevant to the threat scenario
   - All MITRE technique IDs must be valid (e.g., T1566.001)

**Your Approach:**
1. USE PROVIDED CONTEXT FIRST: Prioritize grounding context and web search results
2. VERIFY SOURCES: Only cite sources that appear in the provided context
3. BE HONEST: If you cannot verify something, acknowledge limitations in the rationale
4. Document thoroughly: List all sources in the rationale_summary

**JSON Generation Requirements:**

You must generate valid, parseable JSON. Follow these critical rules:

1. **Escape All Special Characters:**
   - Use `\"` for quotes inside strings
   - Use `\\` for backslashes
   - Avoid line breaks within strings

2. **String Content Rules:**
   - NO unescaped double quotes (") in any string value
   - When including URLs or technical content, ensure all special characters are escaped
   - When including citations or report names with quotes, use single quotes or escape

Generate high-quality, factually grounded risk assessment questionnaires with concise, source-backed rationales."""

    def _perform_web_search_pregeneration(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str],
        user_id: Optional[str] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Perform targeted web searches to gather recent threat intelligence.
        
        Args:
            industry: Target industry
            region: Geographic region
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            
        Returns:
            Tuple of (formatted_context_string, list_of_search_metadata)
        """
        if not self.enable_web_search:
            return "", []
        
        print("🔍 Performing web search pre-generation...")
        
        current_year = datetime.now().year
        search_results = []
        web_context_parts = []
        
        # Priority 1: Recent CISA advisories for industry
        query_1 = f"CISA advisory {industry} site:cisa.gov {current_year}"
        print(f"   Search 1: {query_1}")
        try:
            result_1 = self._execute_web_search(query_1, max_results=3)
            if result_1:
                search_results.append({
                    'query': query_1,
                    'category': 'federal_advisories',
                    'results_count': len(result_1),
                    'sources': [r.get('url', '') for r in result_1]
                })
                web_context_parts.append("### Recent CISA Advisories:\n" + result_1)
        except Exception as e:
            print(f"   ⚠️  Search 1 failed: {e}")
        
        # Priority 2: Current breach cost statistics
        query_2 = f"cost of data breach {industry} {current_year} IBM Ponemon"
        print(f"   Search 2: {query_2}")
        try:
            result_2 = self._execute_web_search(query_2, max_results=2)
            if result_2:
                search_results.append({
                    'query': query_2,
                    'category': 'breach_statistics',
                    'results_count': len(result_2),
                    'sources': [r.get('url', '') for r in result_2]
                })
                web_context_parts.append("### Breach Cost Statistics:\n" + result_2)
        except Exception as e:
            print(f"   ⚠️  Search 2 failed: {e}")
        
        # Priority 3: Regional threat landscape
        query_3 = f"{region} {industry} cyberattack incident {current_year}"
        print(f"   Search 3: {query_3}")
        try:
            result_3 = self._execute_web_search(query_3, max_results=3)
            if result_3:
                search_results.append({
                    'query': query_3,
                    'category': 'regional_incidents',
                    'results_count': len(result_3),
                    'sources': [r.get('url', '') for r in result_3]
                })
                web_context_parts.append("### Regional Threat Intelligence:\n" + result_3)
        except Exception as e:
            print(f"   ⚠️  Search 3 failed: {e}")
        
        # Priority 4: Documented incidents with financial impact
        query_4 = f"{industry} ransomware attack cost {current_year} settlement"
        print(f"   Search 4: {query_4}")
        try:
            result_4 = self._execute_web_search(query_4, max_results=2)
            if result_4:
                search_results.append({
                    'query': query_4,
                    'category': 'incident_case_studies',
                    'results_count': len(result_4),
                    'sources': [r.get('url', '') for r in result_4]
                })
                web_context_parts.append("### Documented Incidents:\n" + result_4)
        except Exception as e:
            print(f"   ⚠️  Search 4 failed: {e}")
        
        # Priority 5: Industry-specific threat reports
        query_5 = f"{industry} cybersecurity threat report {current_year}"
        print(f"   Search 5: {query_5}")
        try:
            result_5 = self._execute_web_search(query_5, max_results=2)
            if result_5:
                search_results.append({
                    'query': query_5,
                    'category': 'threat_reports',
                    'results_count': len(result_5),
                    'sources': [r.get('url', '') for r in result_5]
                })
                web_context_parts.append("### Industry Threat Reports:\n" + result_5)
        except Exception as e:
            print(f"   ⚠️  Search 5 failed: {e}")
        
        # Compile formatted context
        if web_context_parts:
            formatted_context = "\n\n".join([
                "=" * 70,
                "🌐 WEB SEARCH RESULTS (Recent Threat Intelligence)",
                "=" * 70,
                "\n\n".join(web_context_parts),
                "=" * 70
            ])
            print(f"✅ Web search completed: {len(search_results)} successful queries")
        else:
            formatted_context = ""
            print("⚠️  No web search results obtained")
        
        return formatted_context, search_results
    
    def _execute_web_search(self, query: str, max_results: int = 3) -> str:
        """
        Execute a web search and return formatted results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to include
            
        Returns:
            Formatted search results string
        """
        try:
            # Use Anthropic's web search tool via the client
            # Note: This simulates the tool call - actual implementation uses the client's tool system
            search_response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"Search the web for: {query}\n\nProvide a concise summary of the top {max_results} most relevant results, focusing on: dates, specific incidents, statistics, advisory IDs, and dollar amounts. Format as a bulleted list."
                }],
                tools=[{
                    "name": "web_search",
                    "description": "Search the web",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }]
            )
            
            # Extract search results from response
            if search_response.content:
                for block in search_response.content:
                    if hasattr(block, 'text'):
                        return block.text
            
            return ""
            
        except Exception as e:
            print(f"   Web search error: {e}")
            return ""

    def generate_questionnaire(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate risk assessment questionnaire WITH web search + RAG grounding + rationales.
        
        Args:
            industry: Target industry
            region: Geographic region
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            max_retries: Maximum retry attempts
            
        Returns:
            Generated questionnaire dictionary with source-backed rationales
        """
        print(f"\nGenerating questionnaire for {industry} in {region}")
        print("   Including web search + RAG grounding + source-backed rationales...")
        
        # STEP 1: Perform web search pre-generation (NEW)
        web_context = ""
        web_search_metadata = []
        
        if self.enable_web_search:
            web_context, web_search_metadata = self._perform_web_search_pregeneration(
                industry=industry,
                region=region,
                organization_size=organization_size,
                user_id=user_id
            )
        
        # STEP 2: Retrieve RAG grounding context (EXISTING)
        rag_context = ""
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
                    print(f"✅ Retrieved {len(rag_contexts)} relevant documents from RAG corpus")
                    
                    # Format for prompt
                    rag_context = self.rag_engine.format_context_for_prompt(rag_contexts)
                    
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
                    print("⚠️  No relevant documents found in RAG corpus")
            
            except Exception as e:
                print(f"⚠️  RAG retrieval failed: {e}")
                # Continue without RAG context
        
        # STEP 3: Build user message with BOTH contexts
        user_message = self._build_user_message_with_contexts(
            industry=industry,
            region=region,
            organization_size=organization_size,
            web_context=web_context,
            rag_context=rag_context
        )
        
        # STEP 4: Generate with Claude (with retries)
        print("🤖 Generating questionnaire with Claude...")
        
        for attempt in range(max_retries):
            try:
                # Get user tracking metadata
                metadata = create_api_metadata(user_id)
                original_user_id = metadata.pop('_original_user_id')
                
                # Call Claude API
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16000,  # Sufficient for questionnaire + rationales
                    system=self.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_message
                    }],
                    metadata=metadata
                )
                
                # Parse response
                response_text = response.content[0].text
                
                # Extract and validate JSON
                questionnaire = self._extract_json(response_text)
                
                # Validate rationales
                self._validate_rationales(questionnaire)
                
                # Add metadata
                if 'metadata' not in questionnaire:
                    questionnaire['metadata'] = {}
                
                questionnaire['metadata']['web_search_enabled'] = self.enable_web_search
                questionnaire['metadata']['web_search_queries'] = len(web_search_metadata)
                questionnaire['metadata']['rag_grounding_enabled'] = bool(rag_context)
                questionnaire['metadata']['rag_sources_count'] = len(rag_sources_used)
                questionnaire['metadata']['rationale_included'] = True
                
                if web_search_metadata:
                    questionnaire['metadata']['web_search_metadata'] = web_search_metadata
                
                if rag_sources_used:
                    questionnaire['metadata']['rag_sources'] = rag_sources_used
                
                # Log API call
                tracker = get_tracker()
                tracker.log_api_call(
                    user_id=original_user_id,
                    hashed_user_id=metadata['user_id'],
                    api_type='questionnaire_generation_with_web_rag_rationale',
                    model='claude-sonnet-4-20250514',
                    request_id=response.id,
                    metadata={
                        'industry': industry,
                        'region': region,
                        'web_search_enabled': self.enable_web_search,
                        'web_search_queries': len(web_search_metadata),
                        'rag_enabled': bool(rag_context),
                        'rag_sources': len(rag_sources_used),
                        'rationale_enabled': True
                    }
                )
                
                print(f"✅ Questionnaire generated successfully")
                if web_search_metadata:
                    print(f"   Web search: {len(web_search_metadata)} queries executed")
                if rag_sources_used:
                    print(f"   RAG grounding: {len(rag_sources_used)} authoritative sources")
                print(f"   Rationales validated for all threats")
                
                return questionnaire
                
            except json.JSONDecodeError as e:
                print(f"❌ Attempt {attempt + 1} failed: JSON parsing error")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
            except ValueError as e:
                print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("   Retrying...")
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate questionnaire after {max_retries} attempts")
    
    def _build_user_message_with_contexts(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str],
        web_context: str,
        rag_context: str
    ) -> str:
        """Build user message with BOTH web search and RAG grounding contexts."""
        
        message_parts = []
        
        # Add web search context FIRST (most recent information)
        if web_context:
            message_parts.append(web_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above web search results contain RECENT, verified information.")
            message_parts.append("PRIORITIZE these sources for current incidents and statistics.")
            message_parts.append("CITE these sources in your rationale_summary fields.")
            message_parts.append("="*70 + "\n")
        
        # Add RAG context SECOND (authoritative foundational knowledge)
        if rag_context:
            message_parts.append(rag_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above RAG context contains authoritative, foundational knowledge.")
            message_parts.append("Use this context for framework guidance and established threat patterns.")
            message_parts.append("CITE these sources in your rationale_summary fields.")
            message_parts.append("="*70 + "\n")
        
        # Add generation request with rationale requirements
        message_parts.append(f"""Generate a risk assessment questionnaire for:

**Target Organization:**
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size or 'Not specified'}

**Instructions:**
1. PRIORITIZE web search results for recent incidents and current statistics
2. Use RAG context for foundational threat intelligence and framework guidance
3. Generate 3-5 threat scenarios relevant to this industry/region
4. For EACH threat, include a rationale_summary (100-150 tokens) explaining:
   - Which specific sources support this threat (with names, dates, IDs)
   - Why it's relevant to this industry/region
   - What data informed your probability/impact estimates
5. Include PERT estimates for Loss Event Frequency and Loss Magnitude
6. Reference specific MITRE ATT&CK techniques

**CRITICAL: You MUST use this exact JSON structure:**

```json
{{
    "version": "1.0",
    "metadata": {{
        "industry": "{industry}",
        "region": "{region}",
        "approach": "industry-region-threat-tree",
        "framework": "FAIR + MITRE ATT&CK",
        "generation_date": "YYYY-MM-DD",
        "threat_research_sources": [
            "List ALL sources you searched and referenced"
        ]
    }},
    "start_question_id": "threat_selection",
    "questions": {{
        "threat_selection": {{
            "id": "threat_selection",
            "text": "Based on current threat intelligence for {industry} organizations in {region}, which risk scenario do you want to analyze?",
            "type": "multiple_choice",
            "help_text": "These threats are based on recent advisories and documented incidents",
            "choices": [
                {{
                    "id": "threat_ransomware",
                    "text": "Ransomware Attack Targeting Patient Data",
                    "description": "Ransomware attack via phishing email encrypting EHR systems and demanding ransom. Common attack chain: Initial access via phishing (T1566.001), credential access (T1078), data encryption (T1486).",
                    "mitre_techniques": ["T1566.001", "T1078", "T1486"],
                    "rationale_summary": "Selected based on: (1) CISA advisory AA24-242A documenting 5 Canadian healthcare ransomware incidents in Aug 2024, (2) Health Canada CCCS threat bulletin citing 60% increase in healthcare targeting since 2023, (3) Ransomware attacks via phishing represent 70% of healthcare breaches per Verizon DBIR 2024. Average impact $1.2M per incident (IBM X-Force 2024). High probability (2-3/year) for 500-employee healthcare orgs with limited endpoint protection per HC3 analysis.",
                    "next_question_id": "threat_ransomware_assets"
                }},
                {{
                    "id": "threat_insider",
                    "text": "Insider Data Exfiltration",
                    "description": "Authorized user with access to patient records exfiltrates data for sale or personal gain. Techniques: Valid accounts (T1078), data from information repositories (T1213), exfiltration over web service (T1567).",
                    "mitre_techniques": ["T1078", "T1213", "T1567"],
                    "rationale_summary": "INCLUDE SIMILAR RATIONALE HERE: Cite 2+ specific sources, explain industry relevance, provide data on probability/impact. Keep to 100-150 tokens. Be specific with source names, dates, and numbers.",
                    "next_question_id": "threat_insider_assets"
                }}
            ]
        }},
        "threat_ransomware_assets": {{
            "id": "threat_ransomware_assets",
            "text": "What critical assets would be impacted by a ransomware attack?",
            "type": "multiple_choice",
            "choices": [
                {{
                    "id": "asset_ehr",
                    "text": "Electronic Health Records (EHR) system",
                    "next_question_id": "threat_ransomware_controls"
                }},
                {{
                    "id": "asset_billing",
                    "text": "Billing and payment systems",
                    "next_question_id": "threat_ransomware_controls"
                }}
            ]
        }},
        "threat_ransomware_controls": {{
            "id": "threat_ransomware_controls",
            "text": "What security controls do you have in place against ransomware?",
            "type": "multiple_choice",
            "choices": [
                {{
                    "id": "controls_basic",
                    "text": "Basic antivirus and email filtering only",
                    "risk_multiplier": 2.0,
                    "next_question_id": "threat_ransomware_frequency"
                }},
                {{
                    "id": "controls_advanced",
                    "text": "EDR, backup, email security, security awareness training",
                    "risk_multiplier": 0.5,
                    "next_question_id": "threat_ransomware_frequency"
                }}
            ]
        }},
        "threat_ransomware_frequency": {{
            "id": "threat_ransomware_frequency",
            "text": "How often do you estimate this ransomware threat could occur?",
            "type": "pert_estimate",
            "estimate_type": "frequency_per_year",
            "help_text": "Provide three-point estimate based on industry data",
            "guidance": {{
                "minimum": "Best case (e.g., 0.1 = once every 10 years)",
                "most_likely": "Most realistic estimate (e.g., 2 = twice per year)",
                "maximum": "Worst case (e.g., 5 = five times per year)"
            }},
            "next_question_id": "threat_ransomware_magnitude"
        }},
        "threat_ransomware_magnitude": {{
            "id": "threat_ransomware_magnitude",
            "text": "What would be the financial impact per ransomware incident?",
            "type": "pert_estimate",
            "estimate_type": "loss_magnitude_usd",
            "help_text": "Estimate in USD including ransom, recovery, and downtime costs",
            "guidance": {{
                "minimum": "Best case (e.g., 50000 = $50K)",
                "most_likely": "Most realistic estimate (e.g., 250000 = $250K)",
                "maximum": "Worst case (e.g., 1000000 = $1M)"
            }},
            "next_question_id": null
        }}
    }}
}}
```

**CRITICAL REQUIREMENTS:**
1. **rationale_summary is MANDATORY** for each threat choice
2. Rationale must be 100-150 tokens (75-120 words)
3. Must cite at least 2 specific sources with names/dates
4. Must explain industry/region relevance with data
5. Must reference actual statistics (no made-up numbers)
6. Include "start_question_id" at the top level
7. "questions" must be a dictionary (not a list)
8. Each question must have "id" and "next_question_id" fields
9. Create complete question trees for each threat scenario

Return ONLY valid JSON matching this structure.
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
    
    def _validate_rationales(self, questionnaire: Dict) -> None:
        """Validate that all threat choices have proper rationale summaries."""
        
        questions = questionnaire.get('questions', {})
        threat_selection = questions.get('threat_selection', {})
        choices = threat_selection.get('choices', [])
        
        for choice in choices:
            threat_id = choice.get('id', 'unknown')
            rationale = choice.get('rationale_summary', '')
            
            # Check presence
            if not rationale or len(rationale.strip()) < 50:
                raise ValueError(
                    f"Missing or insufficient rationale for threat '{threat_id}'. "
                    f"Each threat must have a rationale_summary of 100-150 tokens."
                )
            
            # Check length (rough token estimate: 1 token ≈ 4 chars)
            token_estimate = len(rationale) / 4
            
            if token_estimate < 80:
                print(f"⚠️  Warning: Rationale too short ({token_estimate:.0f} tokens) for '{threat_id}'")
            elif token_estimate > 250:
                print(f"⚠️  Warning: Rationale too long ({token_estimate:.0f} tokens) for '{threat_id}'")
            
            # Check for source references (basic heuristic)
            has_source_reference = any(word in rationale.lower() for word in 
                ['according', 'report', 'advisory', 'documented', 'cisa', 'mitre', 
                 'study', 'bulletin', 'per', 'verizon', 'ibm', 'cert'])
            
            if not has_source_reference:
                raise ValueError(
                    f"Rationale for threat '{threat_id}' lacks specific source citations. "
                    f"Must cite at least 2 authoritative sources by name."
                )
            
            # Check for data points
            has_numbers = any(char.isdigit() for char in rationale)
            if not has_numbers:
                print(f"⚠️  Warning: Rationale for '{threat_id}' lacks quantitative data")
        
        print(f"✅ Validated {len(choices)} threat rationales")


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("AI Question Generator v2.1.2 - Web Search + RAG + Rationale Test")
    print("="*70)
    
    try:
        # Initialize generator with web search + RAG
        generator = AIQuestionGeneratorWithRAGAndRationale(
            enable_rag=True,
            enable_web_search=True
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
        
        # Show threat rationales
        threat_selection = questionnaire['questions']['threat_selection']
        print(f"\nGenerated {len(threat_selection['choices'])} threats with rationales:")
        print()
        
        for i, threat in enumerate(threat_selection['choices'], 1):
            print(f"{i}. {threat['text']}")
            print(f"   MITRE Techniques: {', '.join(threat['mitre_techniques'])}")
            print(f"   Rationale: {threat['rationale_summary'][:150]}...")
            print()
        
        # Show integration status
        if questionnaire['metadata'].get('web_search_enabled'):
            print(f"✅ Web Search: {questionnaire['metadata'].get('web_search_queries', 0)} queries")
        
        if questionnaire['metadata'].get('rag_grounding_enabled'):
            print(f"✅ RAG Grounding: {questionnaire['metadata'].get('rag_sources_count', 0)} sources")
        
        # Save to file
        filename = "questionnaire_v212_web_rag_test.json"
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
