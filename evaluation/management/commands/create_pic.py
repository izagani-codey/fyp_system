"""
Management command to create a PIC (Programme-In-Charge) user.

Usage:
    python manage.py create_pic --username pic_admin --email pic@unikl.edu.my --password Admin@1234

PIC users are staff users (is_staff=True) with a UserProfile role='pic'.
They are NOT superusers — superusers also work as PIC via the pic_required decorator.
Multiple PIC users can be created.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from evaluation.models import UserProfile


class Command(BaseCommand):
    help = 'Create a PIC (Programme-In-Charge) user account'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Username for the PIC account')
        parser.add_argument('--email',    required=True, help='Email address for the PIC account')
        parser.add_argument('--password', required=True, help='Password for the PIC account')

    def handle(self, *args, **options):
        username = options['username']
        email    = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            raise CommandError(f"A user with username '{username}' already exists.")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,   # PIC can access Django admin
        )
        UserProfile.objects.create(user=user, role='pic')

        self.stdout.write(
            self.style.SUCCESS(
                f"PIC user '{username}' created successfully. "
                f"Login at /login/ with this username and password."
            )
        )
