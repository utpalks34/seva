from django.conf import settings
from django.core.management.base import BaseCommand

from complaints.models import User


class Command(BaseCommand):
    help = "Create or update the default admin superuser for demo and Render deployments."

    def handle(self, *args, **options):
        email = settings.DEMO_ADMIN_EMAIL
        password = settings.DEMO_ADMIN_PASSWORD
        govt_id = settings.DEMO_ADMIN_GOVT_ID

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "role": "AD",
                "govt_id": govt_id,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "is_verified": True,
                "first_name": "Demo Admin",
            },
        )

        user.role = "AD"
        user.govt_id = user.govt_id or govt_id
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.is_verified = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} demo admin user: {email}"))
        self.stdout.write(f"Government ID: {user.govt_id}")
