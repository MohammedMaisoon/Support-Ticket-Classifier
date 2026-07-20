#!/usr/bin/env python3
"""Test classification with a sample ticket"""

from classifier import TicketClassifier

print("Testing classification...\n")

classifier = TicketClassifier()

# Test with the exact input from the screenshot
try:
    result = classifier.classify(
        subject='Double charge on my account',
        message='''I noticed I was charged twice for the same order (#44321) placed on March 15th. Both charges of $89.99 appeared on my bank statement. Please refund one of the charges immediately. This is very concerning.

Thank you,
A frustrated customer''',
        source='email'
    )
    
    print('✅ Classification successful!\n')
    print('='*70)
    print(f'Category: {result.classification.issue_category}')
    print(f'Team: {result.classification.assigned_team}')
    print(f'Priority: {result.classification.priority}')
    print(f'Sentiment: {result.classification.user_sentiment}')
    print(f'Confidence: {result.classification.confidence_score:.2%}')
    print(f'Reasoning: {result.classification.reasoning}')
    print('='*70)
    print(f'\nPII Detected: {result.pii_detected}')
    print(f'Injection Blocked: {result.injection_attempt_blocked}')
    print(f'Processing Time: {result.processing_time_ms:.2f}ms')
    if result.estimated_cost:
        print(f'Cost: ${result.estimated_cost:.6f}')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
