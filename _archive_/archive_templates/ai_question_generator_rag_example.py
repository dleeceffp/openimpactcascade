"""
Example: AI Question Generator with Vertex AI RAG Integration

This file demonstrates how to integrate RAG grounding into the existing
ai_question_generator.py module. This is a reference implementation showing
the key integration points.

To integrate into production:
1. Add RAG imports to ai_question_generator.py
2. Modify _build_contextual_prompt() to include RAG context
3. Update _generate_with_retry() to log RAG usage
4. Add RAG status to error handling
"""

from typing import Dict, Optional
from vertex_rag import get_rag_engine
import logging

logger = logging.getLogger(__name__)


def build_contextual_prompt_with_rag(
    context: Dict,
    enable_rag: bool = True
) -> str:
    """
    Enhanced version of _build_contextual_prompt() with RAG grounding.
    
    This shows how to integrate RAG context retrieval into the existing
    prompt building logic.
    
    Args:
        context: Dictionary with industry, region, and optional parameters
        enable_rag: Whether to use RAG grounding (default: True)
        
    Returns:
        Prompt string with RAG grounding context
    """
    
    industry = context["industry"]
    region = context["region"]
    
    # Build optional context string (existing logic)
    optional_context = ""
    if "organization_size" in context:
        optional_context += f"\n- Organization Size: {context['organization_size']}"
    if "annual_revenue" in context:
        optional_context += f"\n- Annual Revenue: {context['annual_revenue']}"
    
    # === NEW: RAG INTEGRATION ===
    rag_grounding = ""
    if enable_rag:
        try:
            # Get RAG engine
            rag_engine = get_rag_engine(enable_fallback=True)
            
            if rag_engine.enabled:
                logger.info("Retrieving RAG grounding context...")
                
                # Retrieve risk identification context
                rag_contexts = rag_engine.retrieve_risk_identification_context(
                    industry=industry,
                    region=region,
                    organization_size=context.get('organization_size'),
                    max_results=5
                )
                
                if rag_contexts:
                    logger.info(f"Retrieved {len(rag_contexts)} RAG contexts")
                    
                    # Format for prompt injection
                    rag_grounding = "\n\n" + rag_engine.format_context_for_prompt(rag_contexts)
                    rag_grounding += "\n**IMPORTANT: Use the above grounding context to inform your threat identification and ensure all threats are based on documented sources.**\n"
                else:
                    logger.warning("No RAG contexts retrieved, proceeding without grounding")
            else:
                logger.info("RAG engine disabled, using web search only")
                
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            # Continue without RAG grounding (graceful degradation)
    # === END RAG INTEGRATION ===
    
    # Build the full prompt (existing structure with RAG injection)
    prompt = f"""Create a comprehensive risk assessment questionnaire for the following organization:

**Organization Context:**
- Industry: {industry}
- Region: {region}{optional_context}
{rag_grounding}

**Your Task:**

**STEP 1: RESEARCH PHASE (MANDATORY WEB SEARCH WITH VERIFICATION)**

Before generating ANY questions, you MUST perform thorough research and verification:

1. **Initial Threat Landscape Search:**
   - Query: "{industry} cybersecurity threats {region} 2024 2025"
   - Query: "{region} cyber threat landscape 2024"
   - Query: "ACSC threats {industry}" (or relevant regional CERT)

[... rest of existing prompt structure ...]

**STEP 2: THREAT IDENTIFICATION**
Based on your search results AND the grounding context provided above, identify 3-5 REAL, DOCUMENTED cyber threats:
- Each threat must reference an authoritative source (CISA, ENISA, Verizon DBIR, etc.)
- Each threat must cite specific MITRE ATT&CK techniques
- Each threat should reference actual incidents from the past 2-3 years when possible
- Prioritize threats that are actively exploited or trending in threat intelligence

[... rest of existing prompt ...]
"""
    
    return prompt


def example_usage():
    """
    Example of how to use RAG-enhanced questionnaire generation.
    """
    
    print("=== RAG-Enhanced Questionnaire Generation Example ===\n")
    
    # Example context
    context = {
        "industry": "Healthcare",
        "region": "Canada",
        "organization_size": "500 employees"
    }
    
    # Build prompt with RAG grounding
    prompt = build_contextual_prompt_with_rag(context, enable_rag=True)
    
    print("Generated Prompt Preview:")
    print("=" * 60)
    print(prompt[:1000])
    print("...")
    print("=" * 60)
    
    print("\nRAG Integration Points:")
    print("  ✓ RAG context retrieved before prompt construction")
    print("  ✓ Grounding context injected into prompt")
    print("  ✓ Graceful fallback if RAG unavailable")
    print("  ✓ Logging for monitoring and debugging")
    
    print("\nNext Steps:")
    print("  1. Review vertex_rag.py implementation")
    print("  2. Populate knowledge base with documents")
    print("  3. Integrate into ai_question_generator.py")
    print("  4. Test with real questionnaire generation")
    print("  5. Monitor RAG retrieval quality")


def chat_assist_with_rag_example(
    user_message: str,
    context: Dict
) -> str:
    """
    Example of RAG integration for chat assistance.
    
    This shows how to enhance the chat_assist() endpoint in flask_app_chat.py
    with RAG coaching context.
    
    Args:
        user_message: User's question
        context: Chat context (industry, region, FAIR component, etc.)
        
    Returns:
        Enhanced system prompt with RAG grounding
    """
    
    # Get RAG coaching context
    rag_grounding = ""
    
    try:
        rag_engine = get_rag_engine(enable_fallback=True)
        
        if rag_engine.enabled:
            logger.info("Retrieving RAG coaching context...")
            
            rag_contexts = rag_engine.retrieve_coaching_context(
                user_question=user_message,
                industry=context.get('industry', 'General'),
                region=context.get('region', 'Global'),
                fair_component=context.get('fair_component'),
                max_results=3
            )
            
            if rag_contexts:
                logger.info(f"Retrieved {len(rag_contexts)} coaching contexts")
                rag_grounding = "\n\n" + rag_engine.format_context_for_prompt(rag_contexts)
                rag_grounding += "\n**Use this grounding context to provide accurate, evidence-based coaching.**\n"
    
    except Exception as e:
        logger.error(f"RAG coaching retrieval failed: {e}")
    
    # Build enhanced system prompt
    base_system_prompt = f"""You are an expert cybersecurity risk consultant helping a user understand their risk analysis.

**Context:**
- Industry: {context.get('industry', 'Unknown')}
- Region: {context.get('region', 'Unknown')}
- FAIR Component: {context.get('fair_component', 'General')}
{rag_grounding}

**Your Role:**
Provide clear, practical guidance based on the grounding context and your expertise.
"""
    
    return base_system_prompt


def monitoring_example():
    """
    Example of monitoring RAG integration.
    """
    
    print("\n=== RAG Monitoring Example ===\n")
    
    from vertex_rag import get_rag_engine
    
    # Get RAG engine status
    rag = get_rag_engine()
    status = rag.get_status()
    
    print("RAG Engine Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Example: Track RAG usage in logs
    if status['enabled']:
        print("\n✅ RAG is operational")
        print("\nMonitoring Metrics to Track:")
        print("  - RAG queries per hour")
        print("  - Average relevance scores")
        print("  - Context retrieval latency")
        print("  - Fallback rate (when RAG fails)")
        print("  - User satisfaction with RAG-grounded responses")
    else:
        print("\n⚠️  RAG is disabled (fallback mode)")
        print("  Application continues with web search only")


if __name__ == '__main__':
    # Run examples
    example_usage()
    
    print("\n" + "=" * 60)
    
    # Chat assistance example
    print("\n=== Chat Assistance with RAG Example ===\n")
    
    chat_context = {
        "industry": "Healthcare",
        "region": "Canada",
        "fair_component": "LEF"
    }
    
    enhanced_prompt = chat_assist_with_rag_example(
        user_message="How often do ransomware attacks happen?",
        context=chat_context
    )
    
    print("Enhanced Chat System Prompt:")
    print(enhanced_prompt[:500])
    print("...")
    
    print("\n" + "=" * 60)
    
    # Monitoring example
    monitoring_example()
    
    print("\n=== Examples Complete ===")
