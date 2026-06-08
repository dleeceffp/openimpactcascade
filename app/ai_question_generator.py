"""
Enhanced AI Question Generator with currated-context informed Intelligent Web Search.

Version 2.2.1 - Analyzes currated-context content to identify gaps, then performs targeted
web searches only for missing information. Avoids duplication.

This is a DROP-IN REPLACEMENT for v213 with identical interface.
"""

import os
import json
import anthropic
import requests
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from user_tracking import get_tracker, create_api_metadata
from corpus.retrieve import get_rag_engine as get_corpus_retriever


from config import OIC_MODEL, OIC_MODEL_FAST, OIC_MODEL_DEEP, build_system

class AIQuestionGeneratorWithRAGAndRationale:
    """
    AI Question Generator with currated-context grounding, intelligent web search, and rationales.
    
    Key Enhancements in v221:
    - Currated-context informed search queries (analyzes what currated-contexthas, searches for gaps)
    - Reduced query count (2-4 instead of always 5)
    - Avoids duplicating information currated-contextalready contains
    - Targets ultra-recent incidents (last 30-60 days)
    - Adapts to each industry/region/currated-contextstate
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        enable_rag: bool = True, 
        enable_web_search: bool = True,
        google_search_api_key: Optional[str] = None,
        google_search_cse_id: Optional[str] = None
    ):
        """
        Initialize the question generator with currated-context and intelligent Google Search.
        
        Args:
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
            enable_rag: Enable currated-context corpus retrieval (default: True)
            enable_web_search: Enable intelligent web search (default: True)
            google_search_api_key: Google Custom Search API key (or from env)
            google_search_cse_id: Google Custom Search Engine ID (or from env)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.enable_rag = enable_rag
        self.enable_web_search = enable_web_search
        
        # Google Search API credentials
        self.google_search_api_key = google_search_api_key or os.environ.get('GOOGLE_SEARCH_API_KEY')
        self.google_search_cse_id = google_search_cse_id or os.environ.get('GOOGLE_SEARCH_CSE_ID')
        
        self.model = OIC_MODEL
        
        # Validate web search configuration
        if self.enable_web_search:
            if not self.google_search_api_key or not self.google_search_cse_id:
                print("⚠️  Google Search credentials missing (GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CSE_ID)")
                print("    Web search will be disabled")
                self.enable_web_search = False
            else:
                print("✅ Google Custom Search API enabled (intelligent mode)")
        
        # Initialize Corpus Retriever (pillar-based grounding)
        if self.enable_rag:
            self.grounding_retriever = get_corpus_retriever(enable_fallback=True)
            if self.grounding_retriever.enabled:
                print("✅ Pillar grounding enabled (DBIR likelihood)")
            else:
                print("⚠️  Pillar grounding unavailable - defaulting to web-only")
        else:
            self.grounding_retriever = None
            print("ℹ️  Pillar grounding disabled by configuration")
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with currated-context grounding and rationale requirements."""
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
- **Recent web search results** (last 60 days) with current incidents and statistics

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
   - If you cannot find specific incidents, state this honestly in the rationale

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

    def _analyze_rag_content(
        self,
        rag_contexts: List,
        industry: str,
        region: str,
        pillar_context: Optional[str] = None
    ) -> Dict:
        """
        Analyze grounding content to identify what information exists and what gaps need web search.

        Args:
            rag_contexts: Retrieved grounding context chunks (card text in cascade mode)
            industry: Target industry
            region: Geographic region
            pillar_context: Optional pillar likelihood block (DBIR data) to include in analysis

        Returns:
            Dictionary with analysis of content and identified gaps
        """
        if not rag_contexts and not pillar_context:
            return {
                'has_content': False,
                'gaps': ['all']  # Search for everything
            }
        
        analysis = {
            'has_content': True,
            'threats_mentioned': set(),
            'has_current_year_data': False,
            'has_regional_data': False,
            'has_breach_statistics': False,
            'has_recent_advisories': False,
            'newest_year_found': 0,
            'gaps': []
        }
        
        current_year = datetime.now().year
        
        import re

        # Combine all content sources for analysis
        all_contents = []
        for ctx in rag_contexts:
            all_contents.append(ctx.content)
        if pillar_context:
            all_contents.append(pillar_context)
            analysis['has_content'] = True

        # Analyze all content sources (currated-context contexts + pillar data)
        for content in all_contents:
            content_lower = content.lower()

            # Check for current year data
            if str(current_year) in content:
                analysis['has_current_year_data'] = True

            # Check for regional information
            if region.lower() in content_lower:
                analysis['has_regional_data'] = True

            # Check for breach statistics (DBIR counts as breach statistics)
            if any(term in content_lower for term in [
                'cost of breach', 'breach cost', 'average loss',
                'ibm x-force', 'ponemon', 'dbir', 'verizon', 'incident count', 'breach count'
            ]):
                analysis['has_breach_statistics'] = True

            # Check for recent advisories
            if any(term in content_lower for term in ['cisa', 'advisory', 'aa24', 'aa23']):
                analysis['has_recent_advisories'] = True

            # Extract years mentioned (from all sources)
            years = re.findall(r'\b(20\d{2})\b', content)
            if years:
                max_year = max(int(y) for y in years)
                analysis['newest_year_found'] = max(analysis['newest_year_found'], max_year)

            # Identify threat types mentioned
            threat_keywords = {
                'ransomware': 'ransomware',
                'phishing': 'phishing',
                'insider': 'insider threat',
                'ddos': 'DDoS',
                'supply chain': 'supply chain attack',
                'vulnerability': 'vulnerability exploitation',
                'credential': 'credential theft',
                'malware': 'malware'
            }

            for keyword, threat_name in threat_keywords.items():
                if keyword in content_lower:
                    analysis['threats_mentioned'].add(threat_name)
        
        # Identify gaps that need web search
        if not analysis['has_current_year_data'] or analysis['newest_year_found'] < current_year:
            analysis['gaps'].append('current_year_statistics')
        
        if not analysis['has_regional_data']:
            analysis['gaps'].append('regional_incidents')
        
        if not analysis['has_breach_statistics'] or analysis['newest_year_found'] < current_year:
            analysis['gaps'].append('breach_costs')
        
        # Always check for very recent incidents (last 30-60 days)
        analysis['gaps'].append('ultra_recent_incidents')
        
        return analysis

    def _generate_targeted_queries(
        self,
        industry: str,
        region: str,
        rag_analysis: Dict,
        max_queries: int = 4
    ) -> List[Tuple[str, str]]:
        """
        Generate intelligent, targeted search queries based on currated-context gaps.
        
        Args:
            industry: Target industry
            region: Geographic region
            rag_analysis: Analysis of currated-context content gaps
            max_queries: Maximum number of queries to generate
            
        Returns:
            List of (query_string, category) tuples
        """
        queries = []
        current_year = datetime.now().year
        current_month = datetime.now().strftime('%B')
        
        # PRIORITY 1: Always search for ultra-recent incidents (last 30-60 days)
        # This is time-sensitive and currated-context can't have it
        queries.append((
            f"{region} {industry} cyberattack incident {current_month} {current_year}",
            "ultra_recent_incidents"
        ))
        
        # PRIORITY 2: Current year breach statistics (if currated-context doesn't have it)
        if 'breach_costs' in rag_analysis.get('gaps', []):
            queries.append((
                f"cost of data breach {industry} {current_year} IBM Ponemon report",
                "breach_statistics"
            ))
        
        # PRIORITY 3: Current year CISA advisories (if not in RAG)
        if 'current_year_statistics' in rag_analysis.get('gaps', []):
            queries.append((
                f"CISA advisory {industry} site:cisa.gov {current_year}",
                "federal_advisories"
            ))
        
        # PRIORITY 4: Regional incidents (if currated-context lacks regional data)
        if 'regional_incidents' in rag_analysis.get('gaps', []) and len(queries) < max_queries:
            queries.append((
                f"{region} {industry} data breach incident {current_year}",
                "regional_incidents"
            ))
        
        # PRIORITY 5: Specific threats currated-context mentioned (get current status)
        # Only if we have room for more queries
        if len(queries) < max_queries and rag_analysis.get('threats_mentioned'):
            # Pick top 1-2 threats and search for recent activity
            top_threats = list(rag_analysis['threats_mentioned'])[:max_queries - len(queries)]
            for threat in top_threats:
                queries.append((
                    f"{threat} {industry} {region} {current_year} incident",
                    f"threat_specific_{threat.replace(' ', '_')}"
                ))
        
        # Limit to max_queries
        return queries[:max_queries]

    def _execute_google_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Execute a Google Custom Search and return structured results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to retrieve (1-10)
            
        Returns:
            List of result dictionaries with title, snippet, link
        """
        if not self.google_search_api_key or not self.google_search_cse_id:
            return []
        
        try:
            # Google Custom Search API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            
            params = {
                'key': self.google_search_api_key,
                'cx': self.google_search_cse_id,
                'q': query,
                'num': min(max_results, 10)  # API max is 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('items', []):
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'link': item.get('link', ''),
                        'display_link': item.get('displayLink', '')
                    })
                
                return results
            
            elif response.status_code == 429:
                print(f"   ⚠️  Rate limit exceeded for query: {query[:50]}...")
                return []
            
            else:
                print(f"   ⚠️  Search failed (HTTP {response.status_code}): {query[:50]}...")
                return []
                
        except requests.exceptions.Timeout:
            print(f"   ⚠️  Search timeout: {query[:50]}...")
            return []
        
        except Exception as e:
            print(f"   ⚠️  Search error: {e}")
            return []

    def _format_search_results(self, results: List[Dict], category: str) -> str:
        """Format search results for inclusion in prompt context."""
        if not results:
            return ""
        
        # Make category name more readable
        category_names = {
            'ultra_recent_incidents': 'Ultra-Recent Incidents (Last 30-60 Days)',
            'breach_statistics': 'Current Breach Cost Statistics',
            'federal_advisories': 'Recent CISA Advisories',
            'regional_incidents': 'Regional Incident Reports'
        }
        
        display_category = category_names.get(category, category.replace('_', ' ').title())
        formatted = [f"### {display_category}"]
        
        for i, result in enumerate(results, 1):
            formatted.append(f"\n**Result {i}:**")
            formatted.append(f"Title: {result['title']}")
            formatted.append(f"Source: {result['display_link']}")
            formatted.append(f"Summary: {result['snippet']}")
            formatted.append(f"URL: {result['link']}")
        
        return "\n".join(formatted)

    def _assemble_card_grounding(self, card) -> str:
        """Assemble a cascade-archetype card into a verbatim grounding block.

        Card facts enter the prompt VERBATIM (no LLM, no paraphrase). The body is
        already presentation-ready markdown holding the cascade and the
        likelihood/impact mitigation split; we wrap it with a header and clear
        delimiters so it occupies the foundational/authoritative slot.
        """
        fm = card.frontmatter or {}
        header_lines = [
            "=" * 70,
            "AUTHORITATIVE CASCADE ARCHETYPE (grounding base - do not alter)",
            "=" * 70,
            f"Archetype ID: {card.id}",
            f"Label: {card.label}",
        ]
        if card.domain:
            header_lines.append(f"Domain: {card.domain.upper()}")
        if card.entry:
            header_lines.append(f"Entry: {card.entry}")
        if card.terminal_impact:
            header_lines.append(f"Terminal impact: {card.terminal_impact}")
        if fm.get("applies_when"):
            header_lines.append(f"Applies when: {fm.get('applies_when')}")
        if card.anchor_incident:
            header_lines.append(f"Anchor incident: {card.anchor_incident}")
        header_lines.append("=" * 70)

        return "\n".join(header_lines) + "\n\n" + (card.body or "") + "\n" + ("=" * 70)

    def _generate_card_grounded_queries(
        self,
        industry: str,
        region: str,
        card,
        rag_analysis: Dict,
        max_queries: int = 4
    ) -> List[Tuple[str, str]]:
        """Compose web-search queries grounded on the cascade card + industry.

        The card already owns the attack; these queries target INDUSTRY CONTEXT
        for this archetype (prevalence, loss magnitude, regulation, recency) so
        the search enriches frequency/magnitude framing without re-discovering
        the threat. Replaces the RAG-gap queries when an archetype is selected.
        """
        queries: List[Tuple[str, str]] = []
        current_year = datetime.now().year
        current_month = datetime.now().strftime('%B')
        pattern = card.dbir_pattern or "cyberattack"

        # 1) Sector prevalence / recent incidents for this archetype pattern.
        queries.append((
            f"{industry} {pattern} incidents {region} {current_month} {current_year}",
            "archetype_prevalence"
        ))
        # 2) Loss magnitude / breach cost for the sector.
        queries.append((
            f"cost of data breach {industry} {current_year} loss magnitude IBM Ponemon",
            "breach_statistics"
        ))
        # 3) Regulatory drivers for the sector + region.
        queries.append((
            f"{industry} {region} cybersecurity regulatory requirements {current_year}",
            "regulatory_drivers"
        ))
        # 4) Frequency / prevalence signal anchored to the documented campaign.
        anchor = card.anchor_incident or card.label
        queries.append((
            f"{industry} attacks like {anchor} frequency {current_year}",
            "archetype_frequency"
        ))

        return queries[:max_queries]

    def _perform_intelligent_web_search(
        self,
        industry: str,
        region: str,
        rag_analysis: Dict,
        user_id: Optional[str] = None,
        card=None
    ) -> Tuple[str, List[Dict]]:
        """
        Perform intelligent, currated-context informed web searches targeting identified gaps.
        
        Args:
            industry: Target industry
            region: Geographic region
            rag_analysis: Analysis of currated-context content and gaps
            user_id: Optional user ID for tracking
            
        Returns:
            Tuple of (formatted_context_string, list_of_search_metadata)
        """
        if not self.enable_web_search:
            return "", []
        
        if card is not None:
            print("🔍 Performing intelligent web search (cascade-grounded)...")
            queries = self._generate_card_grounded_queries(industry, region, card, rag_analysis)
        else:
            print("🔍 Performing intelligent web search (currated-context informed)...")
            queries = self._generate_targeted_queries(industry, region, rag_analysis)
        
        print(f"   currated-context Analysis: {len(rag_analysis.get('gaps', []))} gaps identified")
        print(f"   Generated {len(queries)} targeted search queries")
        
        search_results = []
        web_context_parts = []
        
        # Execute each targeted query
        for i, (query, category) in enumerate(queries, 1):
            print(f"   Search {i}/{len(queries)}: {query}")
            
            # Determine result count based on priority
            max_results = 4 if i == 1 else 3  # More results for first query
            
            results = self._execute_google_search(query, max_results=max_results)
            
            if results:
                search_results.append({
                    'query': query,
                    'category': category,
                    'results_count': len(results),
                    'sources': [r['link'] for r in results]
                })
                formatted = self._format_search_results(results, category)
                web_context_parts.append(formatted)
                print(f"      ✓ Found {len(results)} results")
            else:
                print(f"      ✗ No results")
        
        # Compile formatted context
        if web_context_parts:
            formatted_context = "\n\n".join([
                "=" * 70,
                "🌐 TARGETED WEB SEARCH RESULTS (currated-context informed Intelligence)",
                "=" * 70,
                f"Note: These searches target gaps in the currated-context corpus knowledge base.",
                f"currated-context provides foundational knowledge; web search adds recent updates.",
                "=" * 70,
                "\n\n".join(web_context_parts),
                "=" * 70
            ])
            total_results = sum(r.get('results_count', 0) for r in search_results)
            print(f"✅ Intelligent search completed: {len(queries)} targeted queries, {total_results} results")
        else:
            formatted_context = ""
            print("⚠️  No web search results obtained")
        
        return formatted_context, search_results

    def generate_questionnaire(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        user_id: Optional[str] = None,
        max_retries: int = 3,
        archetype_card=None,
        custom_scenario: Optional[str] = None
    ) -> Dict:
        """
        Generate risk assessment questionnaire WITH intelligent web search + currated-context + rationales.
        
        Args:
            industry: Target industry
            region: Geographic region
            organization_size: Optional organization size
            user_id: Optional user ID for tracking
            max_retries: Maximum retry attempts
            archetype_card: Optional cascade-archetype Card. When provided, the
                card grounds generation (authoritative foundational block) and
                the web search is cascade-grounded instead of RAG-grounded.
            custom_scenario: Optional user-specified risk scenario. When provided,
                directs the LLM to generate exactly ONE threat path focused on it.
            
        Returns:
            Generated questionnaire dictionary with source-backed rationales
        """
        print(f"\nGenerating questionnaire for {industry} in {region}")
        if archetype_card is not None:
            print(f"   Cascade-grounded mode: archetype {archetype_card.id}")
        else:
            print("   Using intelligent currated-context informed web search + grounding...")
        
        # STEP 1: Build foundational grounding context FIRST (card takes authoritative slot).
        grounding_context = ""
        grounding_sources = []
        rag_contexts = []  # Kept for gap analysis shim (mode 3) or empty (modes 1/2)
        grounding_mode = "web_only"

        if archetype_card is not None:
            # Cascade card takes the foundational/authoritative slot.
            grounding_mode = "cascade"
            grounding_context = self._assemble_card_grounding(archetype_card)
            # Shim so gap-analysis runs over the card text (web search targets gaps).
            rag_contexts = [type("Ctx", (), {"content": grounding_context})()]
            print(f"\u2705 Grounded on cascade archetype {archetype_card.id}")
        # Note: Old elif branch removed — retriever no longer feeds foundational slot.

        # STEP 1.5: Fetch pillar likelihood in ALL modes (new layer, not foundational).
        pillar_likelihood_block = ""
        pillar_sources = []
        if self.grounding_retriever and self.grounding_retriever.enabled:
            try:
                docs = self.grounding_retriever.retrieve_risk_identification_context(
                    industry=industry, region=region, organization_size=organization_size
                )
                if docs:
                    pillar_likelihood_block = self.grounding_retriever.format_context_for_prompt(docs)
                    pillar_sources = [{"source": d.source, "relevance": d.relevance_score} for d in docs]
                    print(f"✅ Pillar likelihood retrieved ({len(docs)} doc(s))")
            except Exception as e:
                print(f"⚠️  Pillar likelihood retrieval failed: {e}")  # Never fatal
        
        # STEP 2: Analyze grounding content to identify gaps (includes card + pillar data)
        rag_analysis = self._analyze_rag_content(
            rag_contexts, industry, region, pillar_context=pillar_likelihood_block
        )
        
        if rag_analysis['has_content']:
            print(f"📊 currated-context Analysis:")
            print(f"   Threats mentioned: {len(rag_analysis.get('threats_mentioned', set()))}")
            print(f"   Newest year in RAG: {rag_analysis.get('newest_year_found', 'unknown')}")
            print(f"   Identified gaps: {', '.join(rag_analysis.get('gaps', ['none']))}")
        
        # STEP 3: Perform intelligent web search targeting gaps
        web_context = ""
        web_search_metadata = []
        
        if self.enable_web_search:
            web_context, web_search_metadata = self._perform_intelligent_web_search(
                industry=industry,
                region=region,
                rag_analysis=rag_analysis,
                user_id=user_id,
                card=archetype_card
            )
        
        # STEP 4: Build user message with ALL contexts assembled before the LLM call:
        #         foundational grounding (card if mode 3) FIRST,
        #         pillar likelihood SECOND,
        #         web context THIRD.
        user_message = self._build_user_message_with_contexts(
            industry=industry,
            region=region,
            organization_size=organization_size,
            web_context=web_context,
            grounding_context=grounding_context,
            pillar_likelihood_block=pillar_likelihood_block,
            cascade_mode=(archetype_card is not None),
            custom_scenario=custom_scenario
        )
        
        # STEP 5: Generate with Claude (with retries)
        # Custom-scenario path uses OIC_MODEL_DEEP for higher fidelity on the
        # single focused scenario; cascade and default paths use self.model.
        generation_model = OIC_MODEL_DEEP if custom_scenario else self.model
        print(f"🤖 Generating questionnaire with Claude ({generation_model})...")
        
        for attempt in range(max_retries):
            try:
                # Get user tracking metadata
                metadata = create_api_metadata(user_id)
                original_user_id = metadata.pop('_original_user_id')
                
                # Call Claude API
                response = self.client.messages.create(
                    model=generation_model,
                    max_tokens=16000,
                    system=build_system(self.system_prompt),
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
                
                # In cascade mode, ENFORCE the single-path contract in code
                # (do not trust the model): keep one threat + its question tree.
                if archetype_card is not None:
                    self._trim_to_single_threat(questionnaire)
                
                # Add metadata
                if 'metadata' not in questionnaire:
                    questionnaire['metadata'] = {}
                
                questionnaire['metadata']['web_search_enabled'] = self.enable_web_search
                questionnaire['metadata']['web_search_queries'] = len(web_search_metadata)
                questionnaire['metadata']['web_search_mode'] = 'intelligent_rag_informed'
                # Legacy currated-context keys preserved (now refer to card/cascade grounding)
                questionnaire['metadata']['rag_grounding_enabled'] = bool(grounding_context)
                questionnaire['metadata']['rag_sources_count'] = len(grounding_sources)
                questionnaire['metadata']['rag_analysis'] = {
                    'gaps_identified': rag_analysis.get('gaps', []),
                    'threats_found': list(rag_analysis.get('threats_mentioned', set())),
                    'newest_year': rag_analysis.get('newest_year_found', 0)
                }
                # New pillar keys (additive only)
                questionnaire['metadata']['pillar_grounding_enabled'] = bool(pillar_likelihood_block)
                if pillar_sources:
                    questionnaire['metadata']['pillar_sources'] = pillar_sources

                questionnaire['metadata']['rationale_included'] = True
                questionnaire['metadata']['grounding_mode'] = grounding_mode
                if archetype_card is not None:
                    questionnaire['metadata']['selected_archetype_id'] = archetype_card.id
                    questionnaire['metadata']['selected_card_ids'] = [archetype_card.id]

                if web_search_metadata:
                    questionnaire['metadata']['web_search_metadata'] = web_search_metadata

                if grounding_sources:
                    questionnaire['metadata']['rag_sources'] = grounding_sources
                
                # Log API call
                tracker = get_tracker()
                tracker.log_api_call(
                    user_id=original_user_id,
                    hashed_user_id=metadata['user_id'],
                    api_type='questionnaire_generation_intelligent_web_rag',
                    model=generation_model,
                    request_id=response.id,
                    metadata={
                        'industry': industry,
                        'region': region,
                        'web_search_enabled': self.enable_web_search,
                        'web_search_queries': len(web_search_metadata),
                        'web_search_mode': 'intelligent',
                        'rag_enabled': bool(grounding_context),
                        'rag_sources': len(grounding_sources),
                        'rag_gaps': len(rag_analysis.get('gaps', [])),
                        'rationale_enabled': True
                    }
                )
                
                print(f"✅ Questionnaire generated successfully")
                if web_search_metadata:
                    total_results = sum(r.get('results_count', 0) for r in web_search_metadata)
                    print(f"   Intelligent search: {len(web_search_metadata)} targeted queries, {total_results} results")
                if grounding_sources:
                    print(f"   Cascade grounding: {len(grounding_sources)} authoritative sources")
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
    
    def _trim_to_single_threat(self, questionnaire: Dict) -> None:
        """Enforce the single-threat contract for cascade mode (in place).

        Keeps the first threat choice in the start (threat-selection) question and
        drops every question node not reachable from it, so the model cannot
        smuggle extra threats into the cascade-grounded output. The JSON schema is
        unchanged - the same structure simply contains exactly one threat path.
        """
        questions = questionnaire.get('questions')
        start_id = questionnaire.get('start_question_id')
        if not isinstance(questions, dict) or start_id not in (questions or {}):
            return

        start_q = questions[start_id]
        choices = start_q.get('choices')
        if not isinstance(choices, list) or len(choices) <= 1:
            return  # already single-path (or no choices to trim)

        dropped = len(choices) - 1
        kept_choice = choices[0]
        start_q['choices'] = [kept_choice]

        def _next_ids(q: Dict) -> List[str]:
            ids = []
            nid = q.get('next_question_id')
            if nid:
                ids.append(nid)
            for ch in q.get('choices', []) or []:
                cnid = ch.get('next_question_id')
                if cnid:
                    ids.append(cnid)
            return ids

        # BFS the reachable question tree from the single kept choice.
        reachable = {start_id}
        frontier = [cid for cid in [kept_choice.get('next_question_id')] if cid]
        while frontier:
            qid = frontier.pop()
            if qid in reachable or qid not in questions:
                continue
            reachable.add(qid)
            frontier.extend(_next_ids(questions[qid]))

        removed = [qid for qid in list(questions.keys()) if qid not in reachable]
        for qid in removed:
            del questions[qid]

        kept_label = kept_choice.get('text') or kept_choice.get('id') or '?'
        print(
            f"⚠️  Cascade mode: model returned {dropped + 1} threats; trimmed to 1 "
            f"('{kept_label}'). Removed {len(removed)} orphan question nodes."
        )
    
    def _build_user_message_with_contexts(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str],
        web_context: str,
        grounding_context: str,
        pillar_likelihood_block: str = "",
        cascade_mode: bool = False,
        custom_scenario: Optional[str] = None
    ) -> str:
        """Build user message with foundational grounding + web search contexts.

        When ``cascade_mode`` is True the foundational block is an authoritative
        cascade archetype; the framing enforces precedence (industry/web context
        informs frequency/magnitude only and must NOT alter the cascade).
        When ``custom_scenario`` is provided the LLM is directed to generate
        exactly ONE threat path focused on that scenario.

        Structure:
            [grounding_context (card, if cascade)] — FIRST, authoritative
            [pillar_likelihood_block]             — SECOND, subordinate context
            [web_context]                         — THIRD, recent supplements
        """

        message_parts = []

        # Add foundational grounding FIRST (card takes authoritative slot in cascade mode).
        if grounding_context:
            message_parts.append(grounding_context)
            message_parts.append("\n" + "="*70)
            if cascade_mode:
                message_parts.append("IMPORTANT: The cascade archetype above is AUTHORITATIVE and FIXED.")
                message_parts.append("Generate the questionnaire's exposure questions from the cascade's")
                message_parts.append("chokepoints (the 'Succeeds when ...' prerequisites). The industry/web")
                message_parts.append("context that follows may inform HOW OFTEN this occurs in this sector,")
                message_parts.append("HOW COSTLY it tends to be, and which regulations apply - it must NOT")
                message_parts.append("change, add, or remove cascade steps, prerequisites, or mitigations.")
                message_parts.append("CITE the archetype and its anchor incident in your rationale_summary fields.")
            else:
                message_parts.append("IMPORTANT: The above grounding context contains authoritative knowledge.")
                message_parts.append("Use this context for framework guidance and established threat patterns.")
                message_parts.append("CITE these sources in your rationale_summary fields.")
            message_parts.append("="*70 + "\n")

        # Add pillar likelihood SECOND (subordinate to card, informs framing only).
        if pillar_likelihood_block:
            message_parts.append(pillar_likelihood_block)
            message_parts.append("\n" + "="*70)
            if cascade_mode:
                message_parts.append("NOTE: The industry likelihood grounding above shows what is currently")
                message_parts.append("observed in this sector. It may inform HOW OFTEN or HOW CREDIBLE the")
                message_parts.append("cascade threat is, but must NOT add, remove, or alter cascade steps.")
            else:
                message_parts.append("NOTE: The industry likelihood grounding above is from Verizon DBIR.")
                message_parts.append("Prioritise these sector-credible threats; cite the publisher.")
            message_parts.append("="*70 + "\n")

        # Add web search context THIRD (recent supplements).
        if web_context:
            message_parts.append(web_context)
            message_parts.append("\n" + "="*70)
            message_parts.append("IMPORTANT: The above web search results contain RECENT information")
            message_parts.append("that supplements the currated-context corpus. These searches targeted specific gaps")
            message_parts.append("in the knowledge base (ultra-recent incidents, current statistics, etc.).")
            message_parts.append("PRIORITIZE these sources for current incidents and statistics.")
            message_parts.append("CITE these sources in your rationale_summary fields with URLs when available.")
            message_parts.append("="*70 + "\n")
        
        # Threat-count directive branches on generation mode:
        #   cascade  -> one fixed threat path from the archetype
        #   custom   -> one threat path focused on the user-specified scenario
        #   default  -> 3-4 threats relevant to industry/region
        if cascade_mode:
            threat_directive = (
                "Generate EXACTLY ONE threat scenario: the cascade archetype provided "
                "above. Do NOT invent or add any other threats. Derive this threat's "
                "questions from the cascade's chokepoints (the 'Succeeds when ...' "
                "prerequisites) - one exposure question per chokepoint."
            )
        elif custom_scenario:
            threat_directive = (
                f"Generate EXACTLY ONE threat scenario focused on the user-selected "
                f"risk scenario: '{custom_scenario}'. Do NOT generate other unrelated "
                f"threat scenarios. All questions must be directly relevant to this "
                f"specific scenario."
            )
        else:
            threat_directive = (
                "Generate 3-4 threat scenarios relevant to this industry/region."
            )

        # Add generation request with rationale requirements
        message_parts.append(f"""Generate a risk assessment questionnaire for:

**Target Organization:**
- Industry: {industry}
- Region: {region}
- Organization Size: {organization_size or 'Not specified'}

**Instructions:**
1. Use grounding context for foundational threat intelligence and framework guidance
2. PRIORITIZE web search results for recent incidents and current statistics
3. The web searches were intelligently selected to fill gaps in grounding knowledge
4. {threat_directive}
5. For EACH threat, include a rationale_summary (100-150 tokens) explaining:
   - Which specific sources support this threat (with names, dates, IDs)
   - Why it's relevant to this industry/region
   - What data informed your probability/impact estimates
6. Include PERT estimates for Loss Event Frequency and Loss Magnitude
7. Reference specific MITRE ATT&CK techniques

    **CRITICAL: You MUST use this exact JSON structure:**
    
    ```json
    {{
        "version": "1.0",
        "metadata": {{
            "industry": "{industry}",
            "region": "{region}",
            "approach": "industry-region-threat-tree",
            "framework": "FAIR + MITRE ATT&CK",
            "generation_date": "{datetime.now().strftime('%Y-%m-%d')}",
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
                        "rationale_summary": "MUST include 100-150 token rationale citing specific sources from provided context with dates, advisory IDs, and quantitative data.",
                        "next_question_id": "threat_ransomware_assets"
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
                    }}
                ]
            }},
            "threat_ransomware_controls": {{
                "id": "threat_ransomware_controls",
                "text": "What is your organization's ability to resist ransomware attacks?",
                "type": "multiple_choice",
                "help_text": "Select the option that best describes your defensive controls. This determines what percentage of attack attempts successfully cause a loss event.",
                "fair_component": "Vulnerability",
                "choices": [
                    {{
                        "id": "controls_basic",
                        "text": "Basic - Antivirus + some email security",
                        "description": "Antivirus, email filtering, but no EDR or backup verification",
                        "vulnerability": 0.40,
                        "vulnerability_display": "40% of attacks succeed (moderate resistance)",
                        "next_question_id": "threat_ransomware_tef"
                    }},
                    {{
                        "id": "controls_intermediate",
                        "text": "Intermediate - EDR + email security + some training",
                        "description": "EDR/XDR, advanced email security, quarterly security training, tested backups",
                        "vulnerability": 0.15,
                        "vulnerability_display": "15% of attacks succeed (good resistance)",
                        "next_question_id": "threat_ransomware_tef"
                    }}
                ]
            }},
            "threat_ransomware_tef": {{
                "id": "threat_ransomware_tef",
                "text": "How often do threat actors ATTEMPT ransomware attacks against organizations like yours?",
                "type": "pert_estimate",
                "estimate_type": "threat_event_frequency",
                "help_text": "This is the frequency of ATTEMPTS, not successful breaches. Based on your threat intelligence, how often do attackers try to compromise you?",
                "fair_component": "TEF",
                "guidance": {{
                    "minimum": "Best case - rare targeting (e.g., 0.5 = once every 2 years)",
                    "most_likely": "Realistic estimate based on industry data (e.g., 4 = 4 attempts/year)",
                    "maximum": "Worst case - heavy targeting (e.g., 12 = monthly attempts)"
                }},
                "next_question_id": "threat_ransomware_lef_result"
            }},
            "threat_ransomware_lef_result": {{
                "id": "threat_ransomware_lef_result",
                "text": "Based on your inputs, here is the calculated Loss Event Frequency:",
                "type": "calculated_display",
                "calculation": "LEF = TEF * Vulnerability",
                "display_format": {{
                    "tef": "{{tef_mle}} attack attempts per year",
                    "vulnerability": "{{vulnerability}}% success rate",
                    "lef": "{{lef_mle}} successful breaches per year",
                    "interpretation": "On average, 1 successful breach every {{1/lef_mle}} years"
                }},
                "editable": true,
                "help_text": "This is automatically calculated from your threat frequency and control effectiveness. You can adjust if you have better data.",
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
3. Must cite at least 2 specific sources with names/dates from provided context
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
    print("AI Question Generator v2.1.4 - Intelligent currated-context informed Search")
    print("="*70)
    
    try:
        # Initialize generator with intelligent search
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
        
        # Show currated-context analysis
        rag_analysis = questionnaire['metadata'].get('rag_analysis', {})
        if rag_analysis:
            print(f"\n📊 currated-context Analysis:")
            print(f"   Gaps identified: {', '.join(rag_analysis.get('gaps_identified', []))}")
            print(f"   Threats found in RAG: {', '.join(rag_analysis.get('threats_found', []))}")
            print(f"   Newest year in RAG: {rag_analysis.get('newest_year', 'unknown')}")
        
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
            queries = questionnaire['metadata'].get('web_search_queries', 0)
            mode = questionnaire['metadata'].get('web_search_mode', 'unknown')
            print(f"✅ Intelligent Search: {queries} targeted queries ({mode})")
        
        if questionnaire['metadata'].get('rag_grounding_enabled'):
            print(f"✅ currated-context Grounding: {questionnaire['metadata'].get('rag_sources_count', 0)} sources")
        
        # Save to file
        filename = "questionnaire_v214_intelligent_search.json"
        with open(filename, 'w') as f:
            json.dump(questionnaire, f, indent=2)
        
        print(f"\n✅ Saved to {filename}")
        
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease set required environment variables:")
        print("  - ANTHROPIC_API_KEY")
        print("  - GOOGLE_SEARCH_API_KEY (for Google Custom Search)")
        print("  - GOOGLE_SEARCH_CSE_ID (for Google Custom Search)")
        print("  - GOOGLE_CLOUD_PROJECT (for RAG)")
        print("  - VERTEX_RAG_CORPUS (for RAG)")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
