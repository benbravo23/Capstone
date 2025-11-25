#!/usr/bin/env python
"""
Script to test guard dashboard rendering and JavaScript visibility
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from ingresos.models import RegistroGuardia
from django.utils import timezone

User = get_user_model()

# Create test user if doesn't exist
user, created = User.objects.get_or_create(
    username='guardia_test',
    defaults={
        'email': 'guardia@test.local',
        'first_name': 'Guard',
        'last_name': 'Test',
    }
)

if created:
    user.set_password('testpass123')
    user.save()
    print(f"✓ Created test user: guardia_test")
else:
    print(f"✓ Using existing user: guardia_test")

# Create test client
client = Client()

# Login
login_success = client.login(username='guardia_test', password='testpass123')
if login_success:
    print("✓ Successfully logged in as guardia_test")
else:
    print("✗ Failed to login")
    sys.exit(1)

# Access guard dashboard
response = client.get('/ingresos/guardia/')

if response.status_code == 200:
    print(f"✓ Guard dashboard loaded successfully (status: 200)")
    
    # Check if JavaScript is visible in the response
    content = response.content.decode('utf-8')
    
    # Check for improperly exposed JavaScript code
    if 'document.addEventListener' in content and '<script>' not in content.split('document.addEventListener')[0][-200:]:
        print("✗ WARNING: JavaScript code may be visible (addEventListener found without preceding <script>)")
    else:
        print("✓ JavaScript appears to be properly wrapped in <script> tags")
    
    # Check for critical form elements
    checks = {
        'Form patente field': 'id_patente_entrada',
        'Form marca field': 'id_marca',
        'Form modelo field': 'id_modelo',
        'Submit button': 'Registrar',
        'Script tag': '<script>',
        'Closing script tag': '</script>',
        'API endpoint': 'api_vehiculo_por_patente',
    }
    
    print("\nContent checks:")
    for check_name, check_string in checks.items():
        if check_string in content:
            print(f"  ✓ {check_name}: Found")
        else:
            print(f"  ✗ {check_name}: NOT FOUND")
    
    # Check for col-md-2 button
    if 'class="col-md-2"' in content and 'Registrar</button>' in content:
        # Find the button section
        button_section = content[content.find('class="col-md-2"'):content.find('class="col-md-2"')+500]
        if 'Registrar</button>' in button_section or 'Registrar Entrada</button>' in button_section:
            print("\n✓ Button is now sized as col-md-2 (fixed from col-md-10)")
        else:
            print("\n✗ Button sizing might still be incorrect")
    
    # Check table structure
    if '<table class="table table-sm table-hover">' in content:
        print("✓ Data table properly structured")
        if 'Modelo' in content:
            print("✓ Modelo column present in table")
    
else:
    print(f"✗ Failed to load guard dashboard (status: {response.status_code})")
    sys.exit(1)

print("\n✓ All tests completed!")
