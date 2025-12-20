from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
import sys
import traceback

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin superuser if it does not exist'

    def handle(self, *args, **options):
        print("=" * 50, flush=True)
        print("CREATE_ADMIN: Starting...", flush=True)

        try:
            username = os.environ.get('ADMIN_USERNAME', 'admin')
            password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

            print(f"CREATE_ADMIN: Checking for user '{username}'...", flush=True)

            if User.objects.filter(username=username).exists():
                print(f"CREATE_ADMIN: User '{username}' already exists", flush=True)
                # Update existing user to ensure is_approved and role are set
                user = User.objects.get(username=username)
                user.is_approved = True
                user.role = 'admin'
                user.save()
                print(f"CREATE_ADMIN: Updated existing user with is_approved=True", flush=True)
                return

            print(f"CREATE_ADMIN: Creating new superuser '{username}'...", flush=True)
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            print(f"CREATE_ADMIN: Superuser created, setting is_approved and role...", flush=True)
            user.is_approved = True
            user.role = 'admin'
            user.save()
            print(f"CREATE_ADMIN: Admin user '{username}' created successfully!", flush=True)

        except Exception as e:
            print(f"CREATE_ADMIN ERROR: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            sys.exit(1)

        print("=" * 50, flush=True)
