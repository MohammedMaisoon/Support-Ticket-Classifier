import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
    
    # Feature Flags
    PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v2")
    PII_REDACTION_ENABLED = os.getenv("PII_REDACTION_ENABLED", "true").lower() == "true"
    COST_TRACKING_ENABLED = os.getenv("COST_TRACKING_ENABLED", "true").lower() == "true"
    
    # Model Pricing (per 1M tokens)
    MODEL_PRICING = {
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }
    
    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Classification Categories
    ISSUE_CATEGORIES = [
        "delivery_issue",
        "payment_issue",
        "login_broken",
        "double_charged",
        "other"
    ]
    
    ASSIGNED_TEAMS = [
        "logistics_team",
        "payments_team",
        "customer_support",
        "technical_team"
    ]
    
    PRIORITIES = ["low", "medium", "high", "critical"]
    SENTIMENTS = ["positive", "neutral", "negative", "angry"]
