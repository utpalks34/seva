#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Check if admin already exists
if not User.objects.filter(email='admin@govt.com').exists():
    user = User.objects.create_superuser(
        email='admin@govt.com',
        password='Admin@12345'
    )
    # Set role to Government Official
    user.role = 'GO'
    user.govt_id = 'GOVT-001'
    user.is_active = True
    user.is_verified = True
    user.save()
    print("✅ Government Official Superuser created successfully!")
    print("Email: admin@govt.com")
    print("Password: Admin@12345")
    print("Role: Government Official (GO)")
    print("Government ID: GOVT-001")
else:
    # Update existing user to be GO role
    user = User.objects.get(email='admin@govt.com')
    user.role = 'GO'
    if not user.govt_id:
        user.govt_id = 'GOVT-001'
    user.is_active = True
    user.is_verified = True
    user.save()
    print("✅ User updated to Government Official role!")
    print("Email: admin@govt.com")
    print("Role: Government Official (GO)")
    print("Government ID:", user.govt_id)
