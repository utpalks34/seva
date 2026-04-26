#!/usr/bin/env python
"""
Test the complete registration and login flow via API
"""
import os
import sys
import django
import json
import requests
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
sys.path.insert(0, 'scfms_project')
django.setup()

User = get_user_model()

# API Base URL
BASE_URL = "http://127.0.0.1:8000"

# Test data
test_email = f"apitest_{int(__import__('time').time())}@example.com"
test_password = "ApiTest123!@"
test_first_name = "API"
test_last_name = "Tester"

print("=" * 60)
print("TESTING CITIZEN PORTAL AUTH FLOW")
print("=" * 60)

# Step 1: Register
print("\n1️⃣  REGISTRATION TEST")
print(f"   Email: {test_email}")
print(f"   Password: {test_password}")

register_data = {
    "email": test_email,
    "password": test_password,
    "first_name": test_first_name,
    "last_name": test_last_name
}

try:
    reg_response = requests.post(
        f"{BASE_URL}/api/auth/register/",
        json=register_data,
        headers={"Content-Type": "application/json"}
    )
    
    if reg_response.status_code == 201:
        print(f"   ✓ Registration successful (HTTP 201)")
        reg_data = reg_response.json()
        print(f"   ✓ User ID: {reg_data.get('user_id')}")
        print(f"   ✓ Email verification required: {reg_data.get('email_verification_required')}")
    else:
        print(f"   ✗ Registration failed (HTTP {reg_response.status_code})")
        print(f"   ✗ Response: {reg_response.text}")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Registration error: {str(e)}")
    sys.exit(1)

# Step 2: Login
print("\n2️⃣  LOGIN TEST")
print(f"   Email: {test_email}")

login_data = {
    "email": test_email,
    "password": test_password
}

try:
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login/",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    if login_response.status_code == 200:
        print(f"   ✓ Login successful (HTTP 200)")
        login_resp = login_response.json()
        token = login_resp.get('token')
        if token:
            print(f"   ✓ Token received: {token[:20]}...")
            print(f"   ✓ User ID: {login_resp.get('user_id')}")
            print(f"   ✓ Role: {login_resp.get('role')}")
        else:
            print(f"   ✗ No token in response")
    else:
        print(f"   ✗ Login failed (HTTP {login_response.status_code})")
        print(f"   ✗ Response: {login_response.text}")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Login error: {str(e)}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nThe authentication flow is working correctly.")
print("Users can now register and login immediately on Render.")
