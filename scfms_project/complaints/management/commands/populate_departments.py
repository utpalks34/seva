# complaints/management/commands/populate_departments.py

from django.core.management.base import BaseCommand
from complaints.models import Department


class Command(BaseCommand):
    help = 'Populate default government departments'

    def handle(self, *args, **options):
        departments_data = [
            {
                'category': 'RO',
                'department_name': 'Public Works Department (PWD)',
                'department_head_name': 'Road Commissioner',
                'department_head_email': 'roads@govt.local',
                'department_head_phone': '+91-1234567890',
                'office_address': '123 Main Street, Municipal Building, City Center',
            },
            {
                'category': 'GA',
                'department_name': 'Sanitation & Waste Management Department',
                'department_head_name': 'Sanitation Manager',
                'department_head_email': 'sanitation@govt.local',
                'department_head_phone': '+91-1234567891',
                'office_address': '45 Waste Management Road, City Outskirts',
            },
            {
                'category': 'UT',
                'department_name': 'Water Supply & Electricity Board',
                'department_head_name': 'Utilities Director',
                'department_head_email': 'utilities@govt.local',
                'department_head_phone': '+91-1234567892',
                'office_address': '789 Utilities Avenue, Industrial Zone',
            },
            {
                'category': 'PB',
                'department_name': 'Public Order & Police Department',
                'department_head_name': 'Police Commissioner',
                'department_head_email': 'police@govt.local',
                'department_head_phone': '+91-1234567893',
                'office_address': '456 Police Plaza, Security District',
            },
            {
                'category': 'OT',
                'department_name': 'General Grievances Department',
                'department_head_name': 'General Manager',
                'department_head_email': 'general@govt.local',
                'department_head_phone': '+91-1234567894',
                'office_address': '999 Government Square, Administrative Block',
            },
        ]

        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                category=dept_data['category'],
                defaults=dept_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Created department: {dept.department_name} ({dept.get_category_display()})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"ℹ️  Department already exists: {dept.department_name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS('✅ Department population complete!')
        )
