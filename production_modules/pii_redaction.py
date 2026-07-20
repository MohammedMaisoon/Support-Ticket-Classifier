import re
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class PIIDetectionResult:
    """Result of PII detection"""
    redacted_text: str
    detected_types: List[str]
    redaction_count: int
    original_text: str


class PIIRedactor:
    """
    Detects and redacts Personally Identifiable Information (PII)
    from customer support tickets to protect privacy.
    """
    
    def __init__(self):
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Credit card patterns (various formats)
        self.credit_card_pattern = re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        )
        
        # Phone number patterns (US and international)
        self.phone_pattern = re.compile(
            r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        )
        
        # Social Security Number pattern
        self.ssn_pattern = re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )
        
        # Order/Account number pattern (common formats)
        self.order_number_pattern = re.compile(
            r'\b(?:order|account|transaction|ref)(?:\s+)?(?:#|number|no\.?|num)?:?\s*([A-Z0-9]{6,})\b',
            re.IGNORECASE
        )
        
        # IP Address pattern
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )
        
        # Physical address pattern (basic)
        self.address_pattern = re.compile(
            r'\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|way)\b',
            re.IGNORECASE
        )
    
    def detect_and_redact(self, text: str) -> PIIDetectionResult:
        """
        Detects and redacts all PII from the input text.
        
        Args:
            text: Original text that may contain PII
            
        Returns:
            PIIDetectionResult with redacted text and metadata
        """
        redacted_text = text
        detected_types = []
        redaction_count = 0
        
        # Redact emails
        email_matches = self.email_pattern.findall(redacted_text)
        if email_matches:
            detected_types.append("EMAIL")
            for email in email_matches:
                redacted_text = redacted_text.replace(
                    email, 
                    f"[EMAIL REDACTED]"
                )
                redaction_count += 1
        
        # Redact credit cards
        cc_matches = self.credit_card_pattern.findall(redacted_text)
        if cc_matches:
            detected_types.append("CREDIT_CARD")
            for cc in cc_matches:
                redacted_text = redacted_text.replace(
                    cc,
                    "[CREDIT CARD REDACTED]"
                )
                redaction_count += 1
        
        # Redact phone numbers
        phone_matches = self.phone_pattern.findall(redacted_text)
        if phone_matches:
            detected_types.append("PHONE")
            redacted_text = self.phone_pattern.sub(
                "[PHONE REDACTED]",
                redacted_text
            )
            redaction_count += len(phone_matches)
        
        # Redact SSN
        ssn_matches = self.ssn_pattern.findall(redacted_text)
        if ssn_matches:
            detected_types.append("SSN")
            for ssn in ssn_matches:
                redacted_text = redacted_text.replace(
                    ssn,
                    "[SSN REDACTED]"
                )
                redaction_count += 1
        
        # Redact IP addresses
        ip_matches = self.ip_pattern.findall(redacted_text)
        if ip_matches:
            detected_types.append("IP_ADDRESS")
            for ip in ip_matches:
                # Only redact if it looks like a real IP (not version numbers like 1.2.3)
                if all(0 <= int(octet) <= 255 for octet in ip.split('.') if octet.isdigit()):
                    redacted_text = redacted_text.replace(
                        ip,
                        "[IP REDACTED]"
                    )
                    redaction_count += 1
        
        # Remove duplicates from detected_types
        detected_types = list(set(detected_types))
        
        return PIIDetectionResult(
            redacted_text=redacted_text,
            detected_types=detected_types,
            redaction_count=redaction_count,
            original_text=text
        )
    
    def has_pii(self, text: str) -> bool:
        """Quick check if text contains any PII"""
        result = self.detect_and_redact(text)
        return result.redaction_count > 0
    
    def get_redacted_preview(self, text: str, max_length: int = 200) -> str:
        """Get a truncated preview of redacted text"""
        result = self.detect_and_redact(text)
        redacted = result.redacted_text
        if len(redacted) > max_length:
            return redacted[:max_length] + "..."
        return redacted


# Example usage and testing
if __name__ == "__main__":
    redactor = PIIRedactor()
    
    # Test cases
    test_texts = [
        "My email is sanjay@xyz.com and my card is 1234567890123456",
        "Call me at 555-123-4567 or email john.doe@example.com",
        "Order #98765, my SSN is 123-45-6789",
        "I am absolutely furious! My package was supposed to arrive 5 days ago and it still hasn't shown up. I've been waiting at home all week. This is completely unacceptable. Order #98765. I want an immediate update or a full refund!\n\nEmail: sanjay@xyzmail.com\nCredit card number: 1234567890123456"
    ]
    
    for text in test_texts:
        result = redactor.detect_and_redact(text)
        print(f"Original: {text}")
        print(f"Redacted: {result.redacted_text}")
        print(f"Detected PII types: {result.detected_types}")
        print(f"Redaction count: {result.redaction_count}")
        print("-" * 80)
