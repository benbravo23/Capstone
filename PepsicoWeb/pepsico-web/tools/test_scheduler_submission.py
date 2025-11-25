"""
Script para probar que el scheduler relleña correctamente fecha_programada_scheduler
y que el servidor lo procesa para crear un IngresoTaller.
"""
import os
import sys
import django

# Agregar el directorio padre (proyecto) al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Ajustar ALLOWED_HOSTS para el test
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.utils import timezone
from datetime import datetime, timedelta
from django.test import Client
from usuarios.models import Usuario
from vehiculos.models import Vehiculo
from ingresos.models import IngresoTaller

print("=== Test Scheduler Submission ===\n")

# Crear o obtener vehiculo
patente = 'TST001'
veh, _ = Vehiculo.objects.get_or_create(
    patente=patente,
    defaults={'marca': 'Test', 'modelo': 'X', 'año': 2020, 'vin': 'VIN001', 'activo': True}
)
print(f"✓ Vehículo: {veh.patente}")

# Limpiar ingresos previos para este vehículo
IngresoTaller.objects.filter(vehiculo=veh).delete()
print(f"  (Limpié ingresos previos del vehículo)\n")

# Crear o obtener admin/supervisor
admin_email = 'admin_scheduler_test@test.com'
try:
    admin = Usuario.objects.get(email=admin_email)
except Usuario.DoesNotExist:
    admin = Usuario.objects.create_user(
        email=admin_email,
        nombre='Admin Scheduler Test',
        rut='RUTSCHED001',
        password='testpass123',
        rol='ADMIN',
        activo=True
    )
print(f"✓ Admin: {admin.email}")

# Crear chofer
chofer_email = 'chofer_scheduler_test@test.com'
try:
    chofer = Usuario.objects.get(email=chofer_email)
except Usuario.DoesNotExist:
    chofer = Usuario.objects.create_user(
        email=chofer_email,
        nombre='Chofer Scheduler Test',
        rut='RUTSCHED002',
        password='testpass123',
        rol='CHOFER',
        activo=True
    )
print(f"✓ Chofer: {chofer.email}")

# Crear supervisor
sup_email = 'supervisor_scheduler_test@test.com'
try:
    sup = Usuario.objects.get(email=sup_email)
except Usuario.DoesNotExist:
    sup = Usuario.objects.create_user(
        email=sup_email,
        nombre='Supervisor Scheduler Test',
        rut='RUTSCHED003',
        password='testpass123',
        rol='SUPERVISOR',
        activo=True
    )
print(f"✓ Supervisor: {sup.email}\n")

# Preparar cliente HTTP
client = Client()
client.login(email=admin_email, password='testpass123')

# Simular selección de slot: mañana a las 18:00 (fin del día)
tomorrow = timezone.localtime(timezone.now()).date() + timedelta(days=1)
slot_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 18, 0, 0)
from django.utils.timezone import make_aware
slot_aware = make_aware(slot_dt)
# Formato que Django espera para datetime-local: YYYY-MM-DDTHH:MM:SS
slot_iso_full = slot_aware.strftime('%Y-%m-%dT%H:%M:%S')
# También probar sin segundos
slot_iso = slot_aware.isoformat()[:16]  # Formato YYYY-MM-DDTHH:MM

print(f"Slot elegido (ISO corto): {slot_iso}")
print(f"Slot elegido (ISO completo): {slot_iso_full}")
print(f"Slot en datetime: {slot_aware}\n")

# POST a ingreso_create con los datos del formulario + fecha_programada_scheduler
post_data = {
    'vehiculo': veh.pk,
    'fecha_programada': '',  # Vacío, el scheduler lo llena
    'motivo': 'Test scheduler submission',
    'observaciones': 'Test',
    'supervisor': sup.pk,
    'chofer': chofer.pk,
    'kilometraje_ingreso': 10000,
    'fecha_programada_scheduler': slot_iso_full,  # Usar formato completo con segundos
}

print("POST data:")
for k, v in post_data.items():
    print(f"  {k}: {v}")

response = client.post('/ingresos/crear/', post_data)

print(f"\nResponse status: {response.status_code}")
print(f"Response content type: {response.get('Content-Type', 'Unknown')}")
print(f"Response redirect URL: {response.url if response.status_code in [301, 302] else 'No redirect'}\n")

# Verificar que se creó el IngresoTaller
ingreso_count = IngresoTaller.objects.filter(vehiculo=veh).count()
if ingreso_count > 0:
    ingreso = IngresoTaller.objects.filter(vehiculo=veh).last()
    print(f"✓ ¡ÉXITO! Ingreso creado:")
    print(f"  - ID: {ingreso.pk}")
    print(f"  - Vehículo: {ingreso.vehiculo.patente}")
    print(f"  - Fecha programada: {ingreso.fecha_programada}")
    print(f"  - Estado: {ingreso.estado}")
    print(f"  - Supervisor: {ingreso.supervisor.nombre if ingreso.supervisor else 'N/A'}")
else:
    print("✗ FALLO: No se creó el IngresoTaller")
    # Si response tiene contexto, mostrar errores del formulario
    if response.context:
        form = response.context.get('form')
        if form:
            print(f"\nErrores del formulario:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
    else:
        print("  (Sin contexto de respuesta)")
        # Imprimir parte del HTML para ver qué pasó
        if 'Asignar fecha' in response.content.decode('utf-8', errors='ignore'):
            print("  → La página renderizó el formulario (no redirigió)")
        else:
            print("  → No sabemos qué pasó")

print("\n=== Test End ===")
