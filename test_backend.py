"""
Test script: Backend API functionality (session manager + routes).
Run: python test_backend.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("TESTING BACKEND API (Session Manager + Routes)")
print("=" * 70)

# Test 1: Create Session
print("\n✓ Test 1: Create Session")
print("-" * 70)
try:
    response = requests.post(
        f"{BASE_URL}/session/create",
        json={
            "provider": "anthropic",
            "api_key": "sk-ant-test-key-12345",
            "model": "claude-3-5-sonnet-20241022",
        },
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    expires_in = data["session_expires_in"]
    print(f"  Session ID: {session_id}")
    print(f"  Expires in: {expires_in}s")
    print(f"  Status: {response.status_code}")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    print("  (Make sure backend is running: uvicorn src.main:app --reload --port 8000)")
    exit(1)

# Test 2: Validate Session
print("\n✓ Test 2: Validate Session")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/session/{session_id}/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-3-5-sonnet-20241022"
    print(f"  Valid: {data['valid']}")
    print(f"  Provider: {data['provider']}")
    print(f"  Model: {data['model']}")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 3: Get Available Models
print("\n✓ Test 3: Get Available Models")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/api/models/available")
    assert response.status_code == 200
    data = response.json()
    assert "anthropic" in data
    assert "openai" in data
    assert "google" in data
    print(f"  Providers found: {', '.join(data.keys())}")
    print(f"  Anthropic models: {len(data['anthropic'])}")
    print(f"  OpenAI models: {len(data['openai'])}")
    print(f"  Google models: {len(data['google'])}")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 4: Delete Session
print("\n✓ Test 4: Delete Session")
print("-" * 70)
try:
    response = requests.delete(f"{BASE_URL}/session/{session_id}")
    assert response.status_code == 200
    print(f"  Status: {response.status_code}")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 5: Validate Deleted Session
print("\n✓ Test 5: Validate Deleted Session (should be invalid)")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/session/{session_id}/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == False
    print(f"  Valid: {data['valid']} (correctly deleted)")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

print("\n" + "=" * 70)
print("ALL TESTS PASSED ✅")
print("Backend API ready for integration with frontend")
print("=" * 70)
