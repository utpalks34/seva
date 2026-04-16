#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


if not User.objects.filter(email='admin@govt.com').exists():
    user = User.objects.create_superuser(
        email='admin@govt.com',
        password='Admin@12345'
    )
    user.role = 'AD'
    user.govt_id = 'GOVT-001'
    user.is_active = True
    user.is_verified = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Administrator superuser created successfully.")
    print("Email: admin@govt.com")
    print("Password: Admin@12345")
    print("Role: Administrator (AD)")
    print("Government ID: GOVT-001")
else:
    user = User.objects.get(email='admin@govt.com')
    user.role = 'AD'
    if not user.govt_id:
        user.govt_id = 'GOVT-001'
    user.is_active = True
    user.is_verified = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("Existing admin user updated.")
    print("Email: admin@govt.com")
    print("Role: Administrator (AD)")
    print("Government ID:", user.govt_id)
