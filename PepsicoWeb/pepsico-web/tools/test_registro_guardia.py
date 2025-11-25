"""
Test para verificar que el guardia crea RegistroGuardia (no IngresoTaller).
"""
import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from datetime import datetime, timedelta
from django.test import Client
from usuarios.models import Usuario
from vehiculos.models import Vehiculo
from ingresos.models import RegistroGuardia, IngresoTaller

print("=== Test: Guardia crea RegistroGuardia (no IngresoTaller) ===\n")

# Crear vehículo test
patente = 'GUARD001'
veh, _ = Vehiculo.objects.get_or_create(
    patente=patente,
    defaults={'marca': 'TestMarca', 'modelo': 'X', 'año': 2020, 'vin': 'VINGUARD01', 'activo': True}
)
print(f"✓ Vehículo: {veh.patente}")

# Crear guardia
guardia_email = 'guardia_test@test.com'
try:
    guardia = Usuario.objects.get(email=guardia_email)
except Usuario.DoesNotExist:
    guardia = Usuario.objects.create_user(
        email=guardia_email,
        nombre='Guardia Test',
        rut='RUTGUARDIA001',
        password='testpass123',
        rol='GUARDIA',
        activo=True
    )
print(f"✓ Guardia: {guardia.email}")

# Contar registros antes
registros_antes = RegistroGuardia.objects.count()
ingresos_antes = IngresoTaller.objects.filter(vehiculo=veh).count()

print(f"\nAntes del test:")
print(f"  - RegistroGuardia count: {registros_antes}")
print(f"  - IngresoTaller (para veh {patente}): {ingresos_antes}\n")

# Simular POST del guardia
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

client = Client()
client.login(email=guardia_email, password='testpass123')

post_data = {
    'patente': patente,
    'marca': 'TestMarca',
    'motivo': 'Reparación de motor',
    'chofer_nombre': 'Juan Pérez',
}

response = client.post('/ingresos/guardia/', post_data)

print(f"Response status: {response.status_code}")
print(f"Response redirect: {response.url if response.status_code in [301, 302] else 'Sin redirect'}\n")

# Verificar resultados
registros_despues = RegistroGuardia.objects.count()
ingresos_despues = IngresoTaller.objects.filter(vehiculo=veh).count()

print(f"Después del test:")
print(f"  - RegistroGuardia count: {registros_despues}")
print(f"  - IngresoTaller (para veh {patente}): {ingresos_despues}\n")

# Validar resultados
if registros_despues > registros_antes:
    print("✅ ¡ÉXITO! Se creó un RegistroGuardia")
    registro = RegistroGuardia.objects.filter(vehiculo=veh).last()
    print(f"   - ID: {registro.pk}")
    print(f"   - Patente: {registro.patente}")
    print(f"   - Chofer: {registro.chofer_nombre}")
    print(f"   - Registrado por: {registro.registrado_por.nombre}")
else:
    print("❌ FALLO: No se creó RegistroGuardia")

if ingresos_despues == ingresos_antes:
    print("\n✅ ¡CORRECTO! NO se creó IngresoTaller (como debe ser)")
else:
    print(f"\n❌ ERROR: Se crearon {ingresos_despues - ingresos_antes} IngresoTaller(s) - esto NO debería pasar")

print("\n=== Test End ===")
