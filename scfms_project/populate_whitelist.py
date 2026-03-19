#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scfms_backend.settings')
django.setup()

from complaints.models import GovernmentWhitelist

# Sample government IDs to whitelist
govt_ids = [
    'GOVT-001',
    'GOVT-002',
    'GOVT-003',
    'GOVT-004',
    'GOVT-005',
    'MCD-101',
    'MCD-102',
    'MCD-103',
    'POLICE-001',
    'POLICE-002',
]

for govt_id in govt_ids:
    obj, created = GovernmentWhitelist.objects.get_or_create(
        gov_id=govt_id,
        defaults={'is_used': False}
    )
    if created:
        print(f"✅ Added to whitelist: {govt_id}")
    else:
        print(f"⚠️ Already exists: {govt_id}")

print("\n✅ Government whitelist populated successfully!")
