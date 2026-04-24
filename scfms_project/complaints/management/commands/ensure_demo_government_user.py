from django.conf import settings
from django.core.management.base import BaseCommand

from complaints.models import User


class Command(BaseCommand):
    help = "Create or update the default demo government account."

    def handle(self, *args, **options):
        email = settings.DEMO_GOV_EMAIL
        password = settings.DEMO_GOV_PASSWORD
        govt_id = settings.DEMO_GOV_GOVT_ID

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "role": "GO",
                "govt_id": govt_id,
                "is_staff": True,
                "is_active": True,
                "is_verified": True,
                "first_name": "Demo Government",
            },
        )

        user.role = "GO"
        user.govt_id = user.govt_id or govt_id
        user.is_staff = True
        user.is_active = True
        user.is_verified = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo government user: {email}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated demo government user: {email}"))
        self.stdout.write(f"Government ID: {user.govt_id}")
