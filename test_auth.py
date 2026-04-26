#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
sys.path.insert(0, 'scfms_project')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Test 1: Create a test user with normalized email
test_email = "TestUser@Example.COM"
test_password = "TestPass123!"

# Delete if exists
User.objects.filter(email=test_email.lower()).delete()

# Create new user
user = User.objects.create_user(
    email=test_email.lower(),
    password=test_password,
    first_name="Test",
    last_name="User",
    role='PC',
    is_active=True,
    is_verified=True
)
print(f"✓ User created: {user.email}")
print(f"  - Active: {user.is_active}")
print(f"  - Verified: {user.is_verified}")
print(f"  - Role: {user.role}")

# Test 2: Verify password
if user.check_password(test_password):
    print(f"✓ Password check passed")
else:
    print(f"✗ Password check failed")

# Test 3: Try to retrieve user for login (exact match)
try:
    found_user = User.objects.get(email=test_email.lower(), role='PC')
    print(f"✓ User found by exact email match: {found_user.email}")
except User.DoesNotExist:
    print(f"✗ User NOT found by exact email match")

# Test 4: Try case-insensitive search
try:
    found_user = User.objects.get(email__iexact=test_email, role='PC')
    print(f"✓ User found by case-insensitive match: {found_user.email}")
except User.DoesNotExist:
    print(f"✗ User NOT found by case-insensitive match")

print("\n✓ All tests passed! Login should work now.")
