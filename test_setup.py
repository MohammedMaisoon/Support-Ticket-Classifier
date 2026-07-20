#!/usr/bin/env python3
"""Test script to verify the installation"""

print("Testing Support Ticket Classifier setup...\n")
print("="*70)

# Test 1: Import modules
print("\n1. Testing module imports...")
try:
    import openai
    import fastapi
    import pydantic
    import tiktoken
    print("   ✅ All dependencies imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Import classifier
print("\n2. Testing classifier import...")
try:
    from classifier import TicketClassifier
    print("   ✅ Classifier module imported successfully")
except Exception as e:
    print(f"   ❌ Classifier import failed: {e}")
    exit(1)

# Test 3: Initialize classifier
print("\n3. Testing classifier initialization...")
try:
    classifier = TicketClassifier()
    print("   ✅ Classifier initialized successfully")
    print(f"      Model: {classifier.model_name}")
    print(f"      Prompt Version: {classifier.prompt_version}")
    print(f"      PII Redaction: {classifier.enable_pii_redaction}")
    print(f"      Cost Tracking: {classifier.enable_cost_tracking}")
except Exception as e:
    print(f"   ❌ Classifier initialization failed: {e}")
    print("\n   Make sure your OpenAI API key is set in .env file")
    exit(1)

# Test 4: Import FastAPI app
print("\n4. Testing FastAPI app...")
try:
    from app import app
    print("   ✅ FastAPI app loaded successfully")
except Exception as e:
    print(f"   ❌ FastAPI app failed: {e}")
    exit(1)

print("\n" + "="*70)
print("\n✅ ALL TESTS PASSED!\n")
print("Your Support Ticket Classifier is ready to use!")
print("\nTo start the server, run:")
print("   python3 app.py")
print("\nThen open your browser to:")
print("   http://127.0.0.1:5178/demo")
print("\n" + "="*70)
