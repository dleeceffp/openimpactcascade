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

**Your Approach:**
1. Start with industry and region to establish context
2. Research and identify REAL, DOCUMENTED threats for that industry/region
3. Create a tree-based questionnaire that narrows from general to specific
4. Reference specific MITRE ATT&CK techniques with proper IDs
5. Provide concrete, realistic examples based on actual incidents
6. Use business-friendly language for executives

**Critical Instructions:**
- Never use generic scenarios like "ransomware attack" without industry context
- Always cite specific MITRE ATT&CK techniques by ID (e.g., T1566.001)
- Base threat scenarios on real-world incidents in that industry/region
- Build a logical tree where each answer leads to more specific questions
- Provide realistic three-point estimates based on industry benchmarks
- Include helpful context about WHY this threat matters to their industry

Output valid JSON only."""

    def generate_questionnaire(self) -> Dict:
        """
        Generate a context-aware questionnaire starting with industry/region.
        Returns complete questionnaire as a dictionary.
        """
        user_prompt = self._build_initial_prompt()
        
        print("Generating questionnaire with Claude AI...")
        print("This may take 20-30 seconds...\n")
        
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
            
            if not self._validate_questionnaire(questionnaire):
                raise ValueError("Generated questionnaire failed validation")
            
            return questionnaire
            
        except Exception as e:
            print(f"Error generating questionnaire: {e}")
            raise
    
    def _build_initial_prompt(self) -> str:
        """Build the initial prompt for question generation."""
        return """Create a risk assessment questionnaire that uses a TREE-BASED approach starting with industry and region.

**Requirements:**

1. **Start with Context Questions:**
   - First question: Ask for industry (provide 8-10 diverse options)
   - Second question: Ask for region/country
   - Third question: Based on industry + region, present REAL documented threats

2. **Threat Selection:**
   - Research actual cyber threats for each industry/region combination
   - Reference specific incidents or threat intelligence reports
   - Cite relevant MITRE ATT&CK techniques
   - Example: "Home construction in Canada" should reference specific threats like:
     * Construction industry supply chain attacks (MITRE T1195)
     * Payment fraud targeting subcontractors (T1566.002)
     * BEC attacks on project financing (T1598)
     * Credential theft from remote site offices (T1078)

3. **Question Flow:**
   ```
   Industry Selection → Region Selection → Threat Identification → 
   Threat Details → Asset Identification → Control Assessment → 
   Frequency Estimation → Impact Estimation
   ```

4. **For Each Path:**
   - Provide 2-4 realistic threat scenarios specific to that industry/region
   - Include context about recent incidents or trends
   - Reference MITRE ATT&CK techniques
   - Ask contextual questions before frequency/magnitude estimates

**JSON Schema:**

```json
{
    "version": "1.0",
    "metadata": {
        "approach": "industry-region-threat-tree",
        "framework": "FAIR + MITRE ATT&CK"
    },
    "start_question_id": "industry_selection",
    "questions": {
        "question_id": {
            "id": "question_id",
            "text": "Question text for the user",
            "type": "multiple_choice" | "pert_estimate" | "text",
            "help_text": "Guidance and context",
            "context": "Why this question matters (optional)",
            
            // For multiple_choice:
            "choices": [
                {
                    "id": "choice_id",
                    "text": "Choice text",
                    "description": "Additional context (optional)",
                    "next_question_id": "next_question_id"
                }
            ],
            
            // For pert_estimate:
            "fair_component": "LEF" | "LM",
            "unit": "events per year" | "USD",
            "prompt": "What to estimate",
            "threat_context": {
                "threat_name": "Specific threat",
                "mitre_techniques": ["T1566.001", "T1078"],
                "industry_relevance": "Why this matters to their industry"
            },
            "examples": [
                {
                    "label": "Scenario description",
                    "values": {"min": 0, "mle": 0, "max": 0},
                    "description": "Context for these numbers"
                }
            ],
            "outputs": {"min": "lef_min", "mle": "lef_mle", "max": "lef_max"},
            "next_question_id": "next_question_id" | null
        }
    }
}
```

**Example Industries to Include:**
- Healthcare / Medical Services
- Financial Services / Banking
- Retail / E-commerce
- Manufacturing / Industrial
- Professional Services (Legal, Accounting, Consulting)
- Construction / Real Estate
- Technology / Software
- Energy / Utilities
- Education
- Transportation / Logistics

**Example Regions:**
- North America (USA, Canada, Mexico)
- Europe (UK, Germany, France, etc.)
- Asia Pacific (Japan, Australia, Singapore, etc.)
- Latin America
- Middle East
- Africa

Generate a complete questionnaire with at least 3 industry options, and for ONE sample path (your choice of industry/region), follow through to the complete frequency and magnitude questions."""

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


def main():
    """Command-line interface for question generation."""
    print("="*70)
    print("AI Risk Assessment Questionnaire Generator")
    print("="*70)
    print()
    
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("\nTo set it:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    try:
        # Initialize generator
        generator = AIQuestionGenerator(api_key=api_key)
        
        # Generate questionnaire
        questionnaire = generator.generate_questionnaire()
        
        print("\n" + "="*70)
        print("Generated Questionnaire")
        print("="*70)
        print()
        
        # Pretty print the result
        pprint(questionnaire, width=100, depth=5)
        
        # Save to file
        print("\n" + "="*70)
        generator.save_questionnaire(questionnaire)
        
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
        
        if mitre_refs:
            unique_mitre = list(set(mitre_refs))
            print(f"\nMITRE ATT&CK techniques referenced: {len(unique_mitre)}")
            print(f"Techniques: {', '.join(unique_mitre)}")
        
        print("\n" + "="*70)
        print("Next Steps")
        print("="*70)
        print("1. Review the generated questionnaire in 'generated_questions.json'")
        print("2. Test it with your Flask application")
        print("3. Iterate on the prompts to improve question quality")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()