import tiktoken
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from config import Config


@dataclass
class TokenUsage:
    """Token usage breakdown"""
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class CostEstimate:
    """Cost estimation with breakdown"""
    input_cost: float
    output_cost: float
    total_cost: float
    token_usage: TokenUsage
    model: str
    pricing_per_1m: Dict[str, float]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "input_tokens": self.token_usage.input_tokens,
            "output_tokens": self.token_usage.output_tokens,
            "total_tokens": self.token_usage.total_tokens,
            "input_cost_usd": round(self.input_cost, 6),
            "output_cost_usd": round(self.output_cost, 6),
            "total_cost_usd": round(self.total_cost, 6),
            "model": self.model
        }


class CostCalculator:
    """
    Calculates token usage and estimates API costs for OpenAI models.
    Tracks costs per request and provides cumulative statistics.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize cost calculator.
        
        Args:
            model_name: OpenAI model name (defaults to Config.MODEL_NAME)
        """
        self.model_name = model_name or Config.MODEL_NAME
        
        # Validate model pricing exists
        if self.model_name not in Config.MODEL_PRICING:
            raise ValueError(
                f"Unknown model '{self.model_name}'. "
                f"Available models: {list(Config.MODEL_PRICING.keys())}"
            )
        
        self.pricing = Config.MODEL_PRICING[self.model_name]
        
        # Initialize tokenizer for the model
        try:
            # Map model names to tiktoken encodings
            encoding_map = {
                "gpt-4o-mini": "o200k_base",
                "gpt-4o": "o200k_base",
                "gpt-3.5-turbo": "cl100k_base",
                "gpt-4": "cl100k_base",
            }
            encoding_name = encoding_map.get(self.model_name, "cl100k_base")
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            # Fallback to cl100k_base if specific encoding not found
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Track cumulative statistics
        self.total_requests = 0
        self.cumulative_input_tokens = 0
        self.cumulative_output_tokens = 0
        self.cumulative_cost = 0.0
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Text to tokenize
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_message_tokens(self, messages: list) -> int:
        """
        Count tokens in a list of messages (OpenAI format).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Approximate number of tokens
        """
        # Base tokens for message formatting
        tokens = 3  # Every reply is primed with <|start|>assistant<|message|>
        
        for message in messages:
            tokens += 3  # Every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens += self.count_tokens(message.get("content", ""))
            
            # Add tokens for role
            if "role" in message:
                tokens += self.count_tokens(message["role"])
            
            # Add tokens for name if present
            if "name" in message:
                tokens += self.count_tokens(message["name"])
                tokens -= 1  # Role is omitted if name is present
        
        return tokens
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None
    ) -> CostEstimate:
        """
        Calculate cost based on token usage.
        
        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            model: Optional model name (uses instance model if not provided)
            
        Returns:
            CostEstimate with detailed breakdown
        """
        model = model or self.model_name
        pricing = Config.MODEL_PRICING.get(model, self.pricing)
        
        # Costs are per 1M tokens, convert to per-token
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        # Update cumulative statistics
        self.total_requests += 1
        self.cumulative_input_tokens += input_tokens
        self.cumulative_output_tokens += output_tokens
        self.cumulative_cost += total_cost
        
        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens
            ),
            model=model,
            pricing_per_1m=pricing
        )
    
    def estimate_cost_from_messages(
        self,
        messages: list,
        estimated_output_tokens: int = 500
    ) -> CostEstimate:
        """
        Estimate cost before making an API call.
        
        Args:
            messages: List of message dicts for OpenAI API
            estimated_output_tokens: Estimated completion length
            
        Returns:
            CostEstimate with projected costs
        """
        input_tokens = self.count_message_tokens(messages)
        return self.calculate_cost(input_tokens, estimated_output_tokens)
    
    def calculate_from_response(
        self,
        response: dict
    ) -> CostEstimate:
        """
        Calculate actual cost from OpenAI API response.
        
        Args:
            response: OpenAI API response object with usage data
            
        Returns:
            CostEstimate with actual costs
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return self.calculate_cost(input_tokens, output_tokens)
    
    def get_statistics(self) -> dict:
        """
        Get cumulative statistics for all requests.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.cumulative_input_tokens,
            "total_output_tokens": self.cumulative_output_tokens,
            "total_tokens": self.cumulative_input_tokens + self.cumulative_output_tokens,
            "cumulative_cost_usd": round(self.cumulative_cost, 4),
            "average_cost_per_request": round(
                self.cumulative_cost / max(self.total_requests, 1), 6
            ),
            "average_tokens_per_request": round(
                (self.cumulative_input_tokens + self.cumulative_output_tokens) / 
                max(self.total_requests, 1),
                2
            ),
            "model": self.model_name,
            "pricing": self.pricing
        }
    
    def reset_statistics(self):
        """Reset cumulative statistics"""
        self.total_requests = 0
        self.cumulative_input_tokens = 0
        self.cumulative_output_tokens = 0
        self.cumulative_cost = 0.0
    
    def format_cost_report(self, cost_estimate: CostEstimate) -> str:
        """
        Format a cost estimate as a readable report.
        
        Args:
            cost_estimate: CostEstimate object
            
        Returns:
            Formatted string report
        """
        return f"""
Cost Report - {cost_estimate.model}
{'='*50}
Input Tokens:    {cost_estimate.token_usage.input_tokens:,} (${cost_estimate.input_cost:.6f})
Output Tokens:   {cost_estimate.token_usage.output_tokens:,} (${cost_estimate.output_cost:.6f})
Total Tokens:    {cost_estimate.token_usage.total_tokens:,}
Total Cost:      ${cost_estimate.total_cost:.6f}
{'='*50}
Pricing (per 1M tokens):
  Input:  ${cost_estimate.pricing_per_1m['input']:.2f}
  Output: ${cost_estimate.pricing_per_1m['output']:.2f}
"""


# Example usage and testing
if __name__ == "__main__":
    calculator = CostCalculator(model_name="gpt-4o-mini")
    
    # Test with sample messages
    test_messages = [
        {
            "role": "system",
            "content": "You are a support ticket classifier."
        },
        {
            "role": "user",
            "content": "Classify this ticket: My package is delayed. Order #12345."
        }
    ]
    
    print("Testing Cost Calculator")
    print("="*50)
    
    # Estimate cost before API call
    estimate = calculator.estimate_cost_from_messages(
        test_messages,
        estimated_output_tokens=150
    )
    
    print(calculator.format_cost_report(estimate))
    
    # Simulate multiple requests
    for i in range(5):
        calculator.calculate_cost(input_tokens=100, output_tokens=50)
    
    print("\nCumulative Statistics:")
    print("="*50)
    stats = calculator.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
