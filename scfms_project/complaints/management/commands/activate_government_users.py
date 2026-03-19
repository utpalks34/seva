# complaints/management/commands/activate_government_users.py

from django.core.management.base import BaseCommand
from complaints.models import User


class Command(BaseCommand):
    help = 'Activate all government official users (is_active=True, is_verified=True)'

    def handle(self, *args, **options):
        # Update all GO users
        inactive_go_users = User.objects.filter(role='GO', is_active=False)
        count = inactive_go_users.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No inactive government users found.')
            )
            return
        
        inactive_go_users.update(is_active=True, is_verified=True)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Activated {count} government official(s)'
            )
        )
        
        # List all active GO users
        active_go_users = User.objects.filter(role='GO', is_active=True)
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Total active government officials: {active_go_users.count()}'
            )
        )
        
        for user in active_go_users:
            self.stdout.write(f"   - {user.email} (ID: {user.govt_id})")
