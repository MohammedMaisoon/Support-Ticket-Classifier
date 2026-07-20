from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime


class ClassificationResult(BaseModel):
    """Structured output schema for ticket classification"""
    
    issue_category: Literal[
        "delivery_issue",
        "payment_issue", 
        "login_broken",
        "double_charged",
        "other"
    ] = Field(
        description="The primary category of the customer issue"
    )
    
    assigned_team: Literal[
        "logistics_team",
        "payments_team",
        "customer_support",
        "technical_team"
    ] = Field(
        description="The team that should handle this ticket"
    )
    
    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="Priority level based on urgency and sentiment"
    )
    
    user_sentiment: Literal["positive", "neutral", "negative", "angry"] = Field(
        description="Customer's emotional tone in the message"
    )
    
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of the classification (0-1)"
    )
    
    reasoning: str = Field(
        description="Explanation of why this classification was chosen"
    )
    
    requires_human_review: bool = Field(
        default=False,
        description="Flag if the ticket needs human review due to complexity or low confidence"
    )
    
    detected_entity_types: Optional[list[str]] = Field(
        default=None,
        description="Types of PII detected in the original message"
    )
    
    @field_validator('confidence_score')
    @classmethod
    def set_human_review_flag(cls, v, info):
        """Automatically flag for human review if confidence is low"""
        if v < 0.85:
            info.data['requires_human_review'] = True
        return v


class TicketInput(BaseModel):
    """Input schema for ticket submission"""
    
    subject: str = Field(
        min_length=1,
        max_length=500,
        description="Ticket subject line"
    )
    
    message: str = Field(
        min_length=1,
        max_length=5000,
        description="Ticket message body"
    )
    
    source: Literal["email", "web_form", "chat"] = Field(
        default="web_form",
        description="Channel through which ticket was submitted"
    )


class ClassificationResponse(BaseModel):
    """Complete response including metadata"""
    
    ticket_id: Optional[str] = None
    classification: ClassificationResult
    original_subject: str
    redacted_message: str
    pii_detected: bool = False
    injection_attempt_blocked: bool = False
    
    # Metadata
    model_used: str
    prompt_version: str
    processing_time_ms: float
    tokens_used: Optional[dict] = None
    estimated_cost: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TKT-12345",
                "classification": {
                    "issue_category": "payment_issue",
                    "assigned_team": "payments_team",
                    "priority": "high",
                    "user_sentiment": "angry",
                    "confidence_score": 0.95,
                    "reasoning": "Customer reporting double charge, expressing frustration",
                    "requires_human_review": False
                },
                "original_subject": "Double charge on my account",
                "redacted_message": "Hello, I noticed I was charged twice...",
                "pii_detected": True,
                "injection_attempt_blocked": False,
                "model_used": "gpt-4o-mini",
                "prompt_version": "v2",
                "processing_time_ms": 850.5,
                "tokens_used": {"input": 71, "output": 62, "total": 133},
                "estimated_cost": 0.000048
            }
        }
