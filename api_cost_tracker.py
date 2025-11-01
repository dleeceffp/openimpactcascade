"""
API Cost Tracker for OpenImpactCascade

Tracks costs for external API calls (Anthropic, OpenAI, etc.) with FinOps tagging
for multi-project cost attribution and reporting.

This module provides cost tracking for services outside GCP that cannot be
tracked via GCP labels, enabling complete cost visibility across code streams.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class APICostTracker:
    """
    Track external API costs with FinOps tagging for cost attribution.
    
    Supports multiple code streams (prod-paid, prod-free, dev-free, test-free)
    and provides structured logging for cost analysis and reporting.
    """
    
    # Cost per 1M tokens (USD) - Update these based on current pricing
    PRICING = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
            "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        },
        "openai": {
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        },
        "google": {
            "gemini-pro": {"input": 0.50, "output": 1.50},
            "gemini-ultra": {"input": 10.00, "output": 30.00},
        }
    }
    
    def __init__(
        self,
        code_stream: str,
        environment: str,
        subscription_tier: str,
        cost_center: str,
        budget_category: str,
        log_dir: str = "./logs/api_costs"
    ):
        """
        Initialize API Cost Tracker.
        
        Args:
            code_stream: Code stream (prod-paid, prod-free, dev-free, test-free)
            environment: Environment (prod, dev, test)
            subscription_tier: Subscription tier (paid, free)
            cost_center: Cost center (revenue, development, qa)
            budget_category: Budget category (high, medium, low)
            log_dir: Directory for cost log files
        """
        self.code_stream = code_stream
        self.environment = environment
        self.subscription_tier = subscription_tier
        self.cost_center = cost_center
        self.budget_category = budget_category
        self.log_dir = Path(log_dir)
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate code stream
        valid_streams = ["prod-paid", "prod-free", "dev-free", "test-free"]
        if code_stream not in valid_streams:
            logger.warning(f"Invalid code_stream: {code_stream}. Expected one of {valid_streams}")
    
    def log_api_call(
        self,
        service: str,
        model: str,
        operation: str,
        tokens_input: int,
        tokens_output: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log an external API call with cost calculation.
        
        Args:
            service: Service name (anthropic, openai, google)
            model: Model identifier
            operation: Operation type (questionnaire, analysis, chat, embedding)
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Optional additional metadata
            
        Returns:
            Log entry dictionary with calculated cost
        """
        # Calculate cost
        cost_usd = self._calculate_cost(service, model, tokens_input, tokens_output)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": self._generate_request_id(),
            
            # Code stream identification
            "code_stream": self.code_stream,
            "environment": self.environment,
            "subscription": self.subscription_tier,
            
            # Service details
            "service": service.lower(),
            "model": model,
            "operation": operation,
            
            # Usage metrics
            "usage": {
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "tokens_total": tokens_input + tokens_output
            },
            
            # Cost tracking
            "cost": {
                "amount_usd": round(cost_usd, 6),
                "cost_center": self.cost_center,
                "budget_category": self.budget_category,
                "currency": "USD"
            },
            
            # User context
            "user_context": {
                "user_id": user_id,
                "session_id": session_id
            },
            
            # Additional metadata
            "metadata": metadata or {}
        }
        
        # Write to log file
        self._write_log(log_entry)
        
        # Log summary
        logger.info(
            f"API Cost: {service}/{model} - {operation} - "
            f"{tokens_input + tokens_output} tokens - ${cost_usd:.4f} - "
            f"{self.code_stream}"
        )
        
        return log_entry
    
    def _calculate_cost(
        self,
        service: str,
        model: str,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """
        Calculate cost for API call based on token usage.
        
        Args:
            service: Service name
            model: Model identifier
            tokens_input: Input tokens
            tokens_output: Output tokens
            
        Returns:
            Cost in USD
        """
        service = service.lower()
        
        # Get pricing for service and model
        if service not in self.PRICING:
            logger.warning(f"Unknown service: {service}. Using default pricing.")
            input_price = 1.00
            output_price = 3.00
        elif model not in self.PRICING[service]:
            logger.warning(f"Unknown model: {model} for {service}. Using default pricing.")
            input_price = 1.00
            output_price = 3.00
        else:
            pricing = self.PRICING[service][model]
            input_price = pricing["input"]
            output_price = pricing["output"]
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (tokens_input / 1_000_000) * input_price
        output_cost = (tokens_output / 1_000_000) * output_price
        
        return input_cost + output_cost
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().isoformat()
        random_data = os.urandom(16)
        hash_input = f"{timestamp}{random_data}".encode()
        return hashlib.sha256(hash_input).hexdigest()[:16]
    
    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Write log entry to file.
        
        Args:
            log_entry: Log entry dictionary
        """
        # Create daily log file
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"api_costs_{self.code_stream}_{date_str}.jsonl"
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write cost log: {e}")
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cost summary for a specific day.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Summary dictionary with costs by service and operation
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        log_file = self.log_dir / f"api_costs_{self.code_stream}_{date}.jsonl"
        
        if not log_file.exists():
            return {
                "date": date,
                "code_stream": self.code_stream,
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_tokens": 0,
                "by_service": {},
                "by_operation": {}
            }
        
        # Parse log file
        total_cost = 0.0
        total_requests = 0
        total_tokens = 0
        by_service = {}
        by_operation = {}
        
        try:
            with open(log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    
                    cost = entry["cost"]["amount_usd"]
                    tokens = entry["usage"]["tokens_total"]
                    service = entry["service"]
                    operation = entry["operation"]
                    
                    total_cost += cost
                    total_requests += 1
                    total_tokens += tokens
                    
                    # By service
                    if service not in by_service:
                        by_service[service] = {"cost": 0.0, "requests": 0, "tokens": 0}
                    by_service[service]["cost"] += cost
                    by_service[service]["requests"] += 1
                    by_service[service]["tokens"] += tokens
                    
                    # By operation
                    if operation not in by_operation:
                        by_operation[operation] = {"cost": 0.0, "requests": 0, "tokens": 0}
                    by_operation[operation]["cost"] += cost
                    by_operation[operation]["requests"] += 1
                    by_operation[operation]["tokens"] += tokens
        
        except Exception as e:
            logger.error(f"Failed to read cost log: {e}")
        
        return {
            "date": date,
            "code_stream": self.code_stream,
            "total_cost_usd": round(total_cost, 2),
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "by_service": by_service,
            "by_operation": by_operation
        }


def get_cost_tracker(
    code_stream: Optional[str] = None,
    environment: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    cost_center: Optional[str] = None,
    budget_category: Optional[str] = None
) -> APICostTracker:
    """
    Get or create API cost tracker instance.
    
    Reads configuration from environment variables if not provided.
    
    Args:
        code_stream: Code stream identifier
        environment: Environment name
        subscription_tier: Subscription tier
        cost_center: Cost center
        budget_category: Budget category
        
    Returns:
        APICostTracker instance
    """
    # Get from environment if not provided
    code_stream = code_stream or os.environ.get("CODE_STREAM", "dev-free")
    environment = environment or os.environ.get("ENVIRONMENT", "dev")
    subscription_tier = subscription_tier or os.environ.get("SUBSCRIPTION_TIER", "free")
    cost_center = cost_center or os.environ.get("COST_CENTER", "development")
    budget_category = budget_category or os.environ.get("BUDGET_CATEGORY", "low")
    
    return APICostTracker(
        code_stream=code_stream,
        environment=environment,
        subscription_tier=subscription_tier,
        cost_center=cost_center,
        budget_category=budget_category
    )


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create tracker for dev-free code stream
    tracker = APICostTracker(
        code_stream="dev-free",
        environment="dev",
        subscription_tier="free",
        cost_center="development",
        budget_category="low"
    )
    
    # Log some example API calls
    tracker.log_api_call(
        service="anthropic",
        model="claude-3-5-sonnet-20241022",
        operation="questionnaire",
        tokens_input=1500,
        tokens_output=800,
        user_id="eval-wsa-abc123",
        session_id="session-xyz789",
        metadata={"industry": "healthcare", "region": "canada"}
    )
    
    tracker.log_api_call(
        service="anthropic",
        model="claude-3-5-sonnet-20241022",
        operation="analysis",
        tokens_input=2000,
        tokens_output=1200,
        user_id="eval-wsa-abc123",
        session_id="session-xyz789"
    )
    
    # Get daily summary
    summary = tracker.get_daily_summary()
    print("\nDaily Cost Summary:")
    print(json.dumps(summary, indent=2))
