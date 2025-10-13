"""
AI-powered question generator for risk assessment questionnaires.
Uses Claude API to generate context-aware FAIR-based questions.
Starts with industry/region to identify specific threats.
"""

import os
import json
import anthropic
from typing import Dict, List, Optional
from pprint import pprint

class AIQuestionGenerator:
    """Generates risk assessment questions using Claude AI with industry/region context."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the question generator.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that defines AI's role and knowledge."""
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

Output valid JSON only."""

    def generate_questionnaire(
        self,
        industry: str,
        region: str,
        # Additional context parameters that could be added:
        organization_size: Optional[str] = None,  # e.g., "50 employees", "500 employees", "5000+ employees"
        annual_revenue: Optional[str] = None,      # e.g., "$5M", "$50M", "$500M+"
        security_maturity: Optional[str] = None,   # e.g., "Basic", "Moderate", "Advanced"
        critical_assets: Optional[List[str]] = None,  # e.g., ["customer data", "payment systems"]
        compliance_requirements: Optional[List[str]] = None,  # e.g., ["GDPR", "HIPAA", "PCI-DSS"]
    ) -> Dict:
        """
        Generate a context-aware questionnaire for specific industry and region.
        
        Args:
            industry: The industry sector (e.g., "Construction", "Healthcare")
            region: Geographic region (e.g., "Canada", "United States", "Europe")
            organization_size: Optional size indicator (employees or revenue)
            annual_revenue: Optional revenue range
            security_maturity: Optional security program maturity level
            critical_assets: Optional list of critical assets to protect
            compliance_requirements: Optional list of regulatory requirements
            
        Returns:
            Dictionary containing the complete questionnaire structure
        """
        # Build context dictionary from provided parameters
        context = {
            "industry": industry,
            "region": region
        }
        
        # Add optional parameters if provided
        if organization_size:
            context["organization_size"] = organization_size
        if annual_revenue:
            context["annual_revenue"] = annual_revenue
        if security_maturity:
            context["security_maturity"] = security_maturity
        if critical_assets:
            context["critical_assets"] = critical_assets
        if compliance_requirements:
            context["compliance_requirements"] = compliance_requirements
        
        user_prompt = self._build_contextual_prompt(context)
        
        print(f"\nGenerating questionnaire for:")
        print(f"  Industry: {industry}")
        print(f"  Region: {region}")
        if organization_size:
            print(f"  Size: {organization_size}")
        if annual_revenue:
            print(f"  Revenue: {annual_revenue}")
        print("\nThis may take 20-30 seconds...\n")
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            response_text = message.content[0].text
            questionnaire = self._extract_json(response_text)
            
            # Add context to questionnaire metadata
            if "metadata" not in questionnaire:
                questionnaire["metadata"] = {}
            questionnaire["metadata"]["generation_context"] = context
            
            if not self._validate_questionnaire(questionnaire):
                raise ValueError("Generated questionnaire failed validation")
            
            return questionnaire
            
        except Exception as e:
            print(f"Error generating questionnaire: {e}")
            raise
    
    def _build_contextual_prompt(self, context: Dict) -> str:
        """Build a contextual prompt based on provided industry/region and optional parameters."""
        
        industry = context["industry"]
        region = context["region"]
        
        # Build optional context string
        optional_context = ""
        if "organization_size" in context:
            optional_context += f"\n- Organization Size: {context['organization_size']}"
        if "annual_revenue" in context:
            optional_context += f"\n- Annual Revenue: {context['annual_revenue']}"
        if "security_maturity" in context:
            optional_context += f"\n- Security Maturity: {context['security_maturity']}"
        if "critical_assets" in context:
            optional_context += f"\n- Critical Assets: {', '.join(context['critical_assets'])}"
        if "compliance_requirements" in context:
            optional_context += f"\n- Compliance Requirements: {', '.join(context['compliance_requirements'])}"
        
        return f"""Create a comprehensive risk assessment questionnaire for the following organization:

**Organization Context:**
- Industry: {industry}
- Region: {region}{optional_context}

**Your Task:**

**STEP 1: RESEARCH PHASE (MANDATORY WEB SEARCH WITH VERIFICATION)**

Before generating ANY questions, you MUST perform thorough research and verification:

1. **Initial Threat Landscape Search:**
   - Query: "{industry} cybersecurity threats {region} 2024 2025"
   - Query: "{region} cyber threat landscape 2024"
   - Query: "ACSC threats {industry}" (or relevant regional CERT)

2. **Verify Specific Advisories and Reports:**
   - If you plan to cite a CISA advisory, search: "CISA [advisory-number] full text"
   - Read the advisory to verify it discusses your industry/region
   - DO NOT cite advisory numbers you cannot verify through search
   - Example search: "CISA AA24-249A education sector" - verify industry relevance

3. **Search for Documented Incidents:**
   - Query: "{industry} data breach {region} 2023 2024"
   - Query: "{industry} ransomware attack {region}"
   - Only include incidents you can verify from search results

4. **Verify Statistics and Data:**
   - Query: "Verizon DBIR 2024 {industry} sector statistics"
   - Query: "IBM Cost of Data Breach 2024 {industry}"
   - Query: "{region} breach statistics {industry}"
   - Only use statistics that appear in search results

5. **Verify MITRE ATT&CK Techniques:**
   - Search for techniques to ensure they're valid and relevant
   - Only cite techniques that genuinely apply to the threat scenario

**CRITICAL VERIFICATION RULES:**

⛔ **DO NOT:**
- Cite advisory numbers without searching and verifying the content
- Reference "multiple incidents" without finding specific examples
- Include statistics without verifiable sources
- Invent URLs or advisory numbers
- Claim an advisory discusses your industry if search shows it doesn't

✅ **DO:**
- Search for and read any advisory before citing it
- Be transparent when specific industry/region data is limited
- Use verified adjacent data (e.g., broader sector, nearby region) when direct data unavailable
- Note data limitations: "Based on broader cybersecurity trends; specific {industry} data for {region} limited"
- Only include sources that search results confirm are relevant

**If Search Results Are Insufficient:**

When you cannot find adequate verified data for the specific industry/region:
1. Be honest: "Specific threat intelligence for {industry} in {region} is limited in public sources"
2. Use verified adjacent information: "Based on general {industry} threats globally" or "Regional data from {region} across sectors"
3. Make appropriate generalizations with clear caveats
4. Still provide value by using verified broader threat intelligence

**REQUIRED: Document your verification process in metadata**

Include in metadata:
- "verification_status": "All sources verified through web search" or "Limited industry-specific data; used adjacent verified sources"
- "verification_notes": "Searched for CISA advisories related to {industry} in {region}; found limited specific advisories. Using broader cybersecurity threat data."

**STEP 2: THREAT IDENTIFICATION**
Based on your search results, identify 3-5 REAL, DOCUMENTED cyber threats:
- Each threat must reference an authoritative source (CISA, ENISA, Verizon DBIR, etc.)
- Each threat must cite specific MITRE ATT&CK techniques
- Each threat should reference actual incidents from the past 2-3 years when possible
- Prioritize threats that are actively exploited or trending in threat intelligence

**STEP 3: QUESTION STRUCTURE**
Create a tree-based questionnaire with this flow:
   
```
Threat Selection (multiple choice of 3-5 specific, documented threats)
  ├─ Threat Deep Dive Questions
  │   ├─ Asset at Risk
  │   ├─ Current Controls Assessment
  │   └─ Threat Actor Context
  ├─ Loss Event Frequency Estimation (PERT)
  └─ Loss Magnitude Estimation (PERT)
```

**STEP 4: ENSURE SPECIFICITY AND CITATIONS**
   
❌ BAD: "Ransomware attack"
✅ GOOD: "Ransomware targeting construction project management systems (e.g., Procore, Buildertrend) - Multiple incidents reported in CISA advisory AA23-158A affecting Canadian contractors, utilizing T1486 (Data Encrypted for Impact) and T1490 (Inhibit System Recovery)"
   
❌ BAD: "Data breach"
✅ GOOD: "Business Email Compromise (BEC) targeting subcontractor payments - FBI IC3 reports $2.4B in losses (2023), common in construction sector. Utilizes T1566.002 (Spearphishing Link) and T1078 (Valid Accounts)"

**STEP 5: PROVIDE REALISTIC ESTIMATES**
Base your example frequency and magnitude estimates on:
- Industry breach cost reports (IBM Cost of Data Breach Report, specific to industry/region)
- Regional regulatory fines (search for recent GDPR penalties, CCPA settlements, provincial fines)
- Incident response costs from industry reports (Verizon DBIR, Ponemon Institute)
- Business disruption costs relevant to organization size (search for industry-specific downtime costs)

**JSON Schema:**

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
            "List ALL sources you searched and referenced",
            "Include URLs to specific reports, advisories, or articles",
            "Example: CISA Advisory AA23-158A - https://www.cisa.gov/...",
            "Example: Verizon 2024 DBIR - {industry} Sector Analysis"
        ],
        "search_queries_used": [
            "List the search queries you used to find this information"
        ]
    }},
    "start_question_id": "threat_selection",
    "questions": {{
        "threat_selection": {{
            "id": "threat_selection",
            "text": "Based on current threat intelligence for {industry} organizations in {region}, which risk scenario do you want to analyze?",
            "type": "multiple_choice",
            "help_text": "These threats are based on recent advisories and documented incidents affecting {industry} in {region}",
            "context": "Threat data current as of [date from search results]",
            "choices": [
                {{
                    "id": "threat_1_id",
                    "text": "Specific threat name with current context",
                    "description": "2-3 sentence description with incident reference, MITRE techniques, and source citation",
                    "mitre_techniques": ["T1566.001", "T1078"],
                    "mitre_technique_links": [
                        "https://attack.mitre.org/techniques/T1566/001/",
                        "https://attack.mitre.org/techniques/T1078/"
                    ],
                    "incident_reference": "Specific reference with source (e.g., 'CISA Advisory AA23-158A, October 2023')",
                    "source_url": "Direct link to advisory or report if available",
                    "threat_intel_summary": "Brief summary of why this is relevant NOW based on search results",
                    "next_question_id": "threat_1_assets"
                }},
                {{
                    "id": "threat_2_id",
                    "text": "Another specific, documented threat...",
                    "description": "...",
                    "mitre_techniques": ["T1190", "T1489"],
                    "mitre_technique_links": ["https://attack.mitre.org/techniques/T1190/", ...],
                    "incident_reference": "...",
                    "source_url": "...",
                    "threat_intel_summary": "...",
                    "next_question_id": "threat_2_assets"
                }}
                // Include 3-5 threat choices based on your research
            ]
        }},
        
        "threat_1_assets": {{
            "id": "threat_1_assets",
            "text": "What critical assets would be impacted by this threat?",
            "type": "multiple_choice",
            "help_text": "Consider which systems or data are most commonly targeted in {industry} based on threat intelligence",
            "choices": [
                {{
                    "id": "asset_type_1",
                    "text": "Specific asset relevant to industry (based on search results showing common targets)",
                    "description": "Why this asset is commonly targeted",
                    "next_question_id": "threat_1_controls"
                }}
            ]
        }},
        
        "threat_1_controls": {{
            "id": "threat_1_controls",
            "text": "What security controls do you currently have in place to mitigate this threat?",
            "type": "multiple_choice",
            "help_text": "Select the option that best describes your current security posture against this specific threat",
            "choices": [
                {{
                    "id": "controls_minimal",
                    "text": "Basic/Minimal controls",
                    "description": "Basic endpoint protection, limited monitoring - represents baseline security",
                    "risk_multiplier": 1.5,
                    "next_question_id": "threat_1_frequency"
                }},
                {{
                    "id": "controls_moderate",
                    "text": "Moderate controls",
                    "description": "EDR, SIEM, regular patching, security awareness training - industry standard",
                    "risk_multiplier": 1.0,
                    "next_question_id": "threat_1_frequency"
                }},
                {{
                    "id": "controls_advanced",
                    "text": "Advanced controls",
                    "description": "Comprehensive security program with threat hunting, zero trust, regular pen testing - above industry standard",
                    "risk_multiplier": 0.5,
                    "next_question_id": "threat_1_frequency"
                }}
            ]
        }},
        
        "threat_1_frequency": {{
            "id": "threat_1_frequency",
            "text": "How often might this threat materialize as a loss event?",
            "type": "pert_estimate",
            "fair_component": "LEF",
            "unit": "events per year",
            "prompt": "Estimate the number of times per year this specific threat could result in a loss event for your organization",
            "help_text": "Consider your security controls, industry trends from search results, and threat actor activity in {region}",
            "threat_context": {{
                "threat_name": "Specific threat from choice",
                "mitre_techniques": ["T1566.001", "T1078"],
                "industry_relevance": "Why this matters to {industry} in {region} based on search findings",
                "current_trends": "What search results show about recent activity",
                "source_data": "Reference to frequency data from Verizon DBIR or similar"
            }},
            "examples": [
                {{
                    "label": "Strong security posture (Advanced controls)",
                    "values": {{"min": 0.1, "mle": 0.5, "max": 2}},
                    "description": "Comprehensive security program with threat detection and response",
                    "basis": "Based on industry benchmarks from [source]"
                }},
                {{
                    "label": "Moderate security posture",
                    "values": {{"min": 1, "mle": 3, "max": 8}},
                    "description": "Basic controls in place, some monitoring",
                    "basis": "Industry average from [source]"
                }},
                {{
                    "label": "Weak security posture (Minimal controls)",
                    "values": {{"min": 5, "mle": 12, "max": 30}},
                    "description": "Limited security controls, high vulnerability",
                    "basis": "High-risk profile from [source]"
                }}
            ],
            "outputs": {{"min": "lef_min", "mle": "lef_mle", "max": "lef_max"}},
            "next_question_id": "threat_1_magnitude"
        }},
        
        "threat_1_magnitude": {{
            "id": "threat_1_magnitude",
            "text": "What would be the financial impact of a single occurrence of this threat?",
            "type": "pert_estimate",
            "fair_component": "LM",
            "unit": "USD",
            "prompt": "Estimate the total cost per incident, including all categories below",
            "help_text": "Include direct costs (response, recovery) and indirect costs (business disruption, reputation). Based on current industry data.",
            "impact_categories": [
                "Incident response and forensics",
                "Legal and regulatory costs",
                "Business disruption and downtime",
                "Data recovery and system restoration",
                "Notification costs (if applicable)",
                "Regulatory fines (consider {region} requirements from search results)",
                "Reputation damage and customer loss",
                "Insurance deductible"
            ],
            "threat_context": {{
                "threat_name": "Specific threat from choice",
                "typical_costs": "Reference industry cost benchmarks from IBM Cost of Data Breach or similar",
                "regulatory_factors": "Regional compliance considerations for {region} with specific fine examples from search",
                "recent_incidents": "Examples of similar incidents and their costs from search results"
            }},
            "examples": [
                {{
                    "label": "Minor incident",
                    "values": {{"min": 10000, "mle": 50000, "max": 150000}},
                    "description": "Limited scope, quick recovery, minimal business disruption",
                    "basis": "Based on [source] for small-scale incidents in {industry}"
                }},
                {{
                    "label": "Moderate incident",
                    "values": {{"min": 150000, "mle": 500000, "max": 2000000}},
                    "description": "Significant impact, multi-day recovery, some data loss or exposure",
                    "basis": "Industry median from [source]"
                }},
                {{
                    "label": "Severe incident",
                    "values": {{"min": 2000000, "mle": 5000000, "max": 15000000}},
                    "description": "Major breach, extended downtime, regulatory fines, significant reputation damage",
                    "basis": "Based on documented major incidents: [example with source]"
                }}
            ],
            "outputs": {{"min": "lm_min", "mle": "lm_mle", "max": "lm_max"}},
            "next_question_id": null
        }}
        
        // Repeat similar structure for other threat paths (threat_2, threat_3, etc.)
        // Ensure each path is based on your search findings
    }}
}}
```

**Critical Requirements:**
1. YOU MUST USE WEB SEARCH before generating the questionnaire
2. Document ALL sources in metadata.threat_research_sources with URLs when available
3. Base ALL threats on documented incidents or authoritative threat intelligence
4. Include MITRE ATT&CK technique IDs with links to attack.mitre.org
5. Provide cost estimates based on authoritative industry reports (IBM, Verizon DBIR, Ponemon)
6. Reference recent (2023-2025) incidents when available
7. Generate complete paths for at least 2-3 different threats
8. Ensure all next_question_id references point to actual questions
9. Tailor ALL content to the specific {industry} and {region} combination based on your research
"""

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from AI response text."""
        # Remove markdown code blocks if present
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_str = text[start:end].strip()
        else:
            # Find JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            json_str = text[start:end].strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"JSON string: {json_str[:500]}...")
            raise
    
    def _validate_questionnaire(self, questionnaire: Dict) -> bool:
        """Validate generated questionnaire structure."""
        # Check required top-level fields
        if "start_question_id" not in questionnaire:
            print("Validation failed: Missing 'start_question_id'")
            return False
        
        if "questions" not in questionnaire:
            print("Validation failed: Missing 'questions'")
            return False
        
        questions = questionnaire.get("questions", {})
        if not questions:
            print("Validation failed: 'questions' dict is empty")
            return False
        
        # Verify start question exists
        start_id = questionnaire.get("start_question_id")
        if start_id not in questions:
            print(f"Validation failed: start_question_id '{start_id}' not found in questions")
            return False
        
        # Validate each question has required fields
        for q_id, q_data in questions.items():
            if "text" not in q_data:
                print(f"Validation failed: Question '{q_id}' missing 'text'")
                return False
            
            if "type" not in q_data:
                print(f"Validation failed: Question '{q_id}' missing 'type'")
                return False
            
            q_type = q_data.get("type")
            
            # Type-specific validation
            if q_type == "multiple_choice":
                if "choices" not in q_data or not q_data["choices"]:
                    print(f"Validation failed: Multiple choice question '{q_id}' has no choices")
                    return False
                
                # Validate each choice has next_question_id
                for choice in q_data["choices"]:
                    if "next_question_id" not in choice:
                        print(f"Validation failed: Choice in '{q_id}' missing next_question_id")
                        return False
            
            elif q_type == "pert_estimate":
                if "outputs" not in q_data:
                    print(f"Validation failed: PERT question '{q_id}' missing 'outputs'")
                    return False
                
                outputs = q_data["outputs"]
                required_outputs = ["min", "mle", "max"]
                if not all(key in outputs for key in required_outputs):
                    print(f"Validation failed: PERT question '{q_id}' outputs missing required keys")
                    return False
        
        print("✓ Questionnaire validation passed")
        return True
    
    def save_questionnaire(self, questionnaire: Dict, filename: str = "generated_questions.json"):
        """Save questionnaire to JSON file."""
        with open(filename, 'w') as f:
            json.dump(questionnaire, f, indent=2)
        print(f"\n✓ Questionnaire saved to: {filename}")


def display_menu():
    """Display the main menu."""
    print("\n" + "="*70)
    print("AI Risk Assessment Questionnaire Generator")
    print("="*70)
    print("\nOptions:")
    print("  1. Generate questionnaire")
    print("  2. View recent questionnaires")
    print("  3. Exit")
    print("="*70)


def get_user_input():
    """Get industry and region from user with helpful prompts."""
    print("\n" + "-"*70)
    print("Organization Context")
    print("-"*70)
    
    print("\nCommon Industries:")
    industries = [
        "Healthcare", "Financial Services", "Retail/E-commerce",
        "Construction", "Manufacturing", "Technology/Software",
        "Education", "Legal Services", "Energy/Utilities",
        "Transportation/Logistics", "Hospitality", "Real Estate"
    ]
    
    for i, ind in enumerate(industries, 1):
        print(f"  {i:2d}. {ind}")
    
    industry = input("\nEnter industry name (or number): ").strip()
    
    # Convert number to industry name if needed
    if industry.isdigit():
        idx = int(industry) - 1
        if 0 <= idx < len(industries):
            industry = industries[idx]
        else:
            print("Invalid number, using as-is")
    
    print("\nCommon Regions:")
    regions = [
        "Canada", "United States", "United Kingdom", "European Union",
        "Australia", "Japan", "Singapore", "India", "Brazil", "Mexico"
    ]
    
    for i, reg in enumerate(regions, 1):
        print(f"  {i:2d}. {reg}")
    
    region = input("\nEnter region/country (or number): ").strip()
    
    # Convert number to region name if needed
    if region.isdigit():
        idx = int(region) - 1
        if 0 <= idx < len(regions):
            region = regions[idx]
        else:
            print("Invalid number, using as-is")
    
    # Optional: Get additional context
    print("\n" + "-"*70)
    print("Additional Context (Optional - press Enter to skip)")
    print("-"*70)
    
    org_size = input("Organization size (e.g., '50 employees', '500 employees'): ").strip()
    
    # TODO: Could add more optional parameters here:
    # revenue = input("Annual revenue (e.g., '$5M', '$50M'): ").strip()
    # maturity = input("Security maturity (Basic/Moderate/Advanced): ").strip()
    # assets = input("Critical assets (comma-separated): ").strip().split(',')
    # compliance = input("Compliance requirements (comma-separated): ").strip().split(',')
    
    return industry, region, org_size if org_size else None


def main():
    """Command-line interface with interactive loop."""
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n" + "="*70)
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("="*70)
        print("\nTo set it:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr add to ~/.zshrc or ~/.bashrc to make permanent")
        return
    
    try:
        # Initialize generator
        generator = AIQuestionGenerator(api_key=api_key)
        
        # Main loop
        while True:
            display_menu()
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "1":
                # Generate new questionnaire
                industry, region, org_size = get_user_input()
                
                print("\n" + "="*70)
                print("Generating Questionnaire")
                print("="*70)
                
                # Generate with optional parameters
                # You can expand this to include more parameters:
                questionnaire = generator.generate_questionnaire(
                    industry=industry,
                    region=region,
                    organization_size=org_size,
                    # annual_revenue=revenue,
                    # security_maturity=maturity,
                    # critical_assets=assets,
                    # compliance_requirements=compliance
                )
                
                print("\n" + "="*70)
                print("Generated Questionnaire")
                print("="*70)
                print()
                
                # Pretty print the result
                pprint(questionnaire, width=100, depth=5)
                
                # Save to file with industry/region in filename
                safe_industry = industry.replace("/", "-").replace(" ", "_")
                safe_region = region.replace("/", "-").replace(" ", "_")
                filename = f"questions_{safe_industry}_{safe_region}.json"
                
                print("\n" + "="*70)
                generator.save_questionnaire(questionnaire, filename)
                
                # Print summary
                print("\n" + "="*70)
                print("Summary")
                print("="*70)
                num_questions = len(questionnaire.get("questions", {}))
                print(f"Total questions: {num_questions}")
                
                # Count PERT questions
                pert_count = sum(1 for q in questionnaire.get("questions", {}).values() 
                                if q.get("type") == "pert_estimate")
                print(f"PERT estimate questions: {pert_count}")
                
                # Count multiple choice questions
                mc_count = sum(1 for q in questionnaire.get("questions", {}).values() 
                              if q.get("type") == "multiple_choice")
                print(f"Multiple choice questions: {mc_count}")
                
                # Show MITRE references if present
                mitre_refs = []
                for q in questionnaire.get("questions", {}).values():
                    if "threat_context" in q and "mitre_techniques" in q["threat_context"]:
                        mitre_refs.extend(q["threat_context"]["mitre_techniques"])
                    # Also check in choices
                    if "choices" in q:
                        for choice in q["choices"]:
                            if "mitre_techniques" in choice:
                                mitre_refs.extend(choice["mitre_techniques"])
                
                if mitre_refs:
                    unique_mitre = list(set(mitre_refs))
                    print(f"\nMITRE ATT&CK techniques referenced: {len(unique_mitre)}")
                    print(f"Techniques: {', '.join(sorted(unique_mitre))}")
                
                # Show threat research sources if available
                if "metadata" in questionnaire and "threat_research_sources" in questionnaire["metadata"]:
                    sources = questionnaire["metadata"]["threat_research_sources"]
                    print(f"\nThreat Research Sources:")
                    for source in sources:
                        print(f"  - {source}")
                
            elif choice == "2":
                # List recent questionnaires
                import glob
                files = sorted(glob.glob("questions_*.json"), key=os.path.getmtime, reverse=True)
                
                if not files:
                    print("\nNo questionnaires found.")
                else:
                    print("\n" + "="*70)
                    print("Recent Questionnaires")
                    print("="*70)
                    for i, f in enumerate(files[:10], 1):  # Show last 10
                        stat = os.stat(f)
                        size_kb = stat.st_size / 1024
                        print(f"  {i:2d}. {f} ({size_kb:.1f} KB)")
                    
                    view = input("\nEnter number to view (or Enter to skip): ").strip()
                    if view.isdigit():
                        idx = int(view) - 1
                        if 0 <= idx < len(files):
                            with open(files[idx], 'r') as f:
                                data = json.load(f)
                                print("\n" + "="*70)
                                pprint(data, width=100, depth=5)
            
            elif choice == "3":
                print("\nGoodbye!")
                break
            
            else:
                print("\nInvalid choice. Please enter 1, 2, or 3.")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()