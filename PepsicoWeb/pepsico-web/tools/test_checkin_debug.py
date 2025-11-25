import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from ingresos.models import IngresoTaller

# Obtener el ingreso 23
ingreso = IngresoTaller.objects.get(pk=23)
print("Ingreso 23:")
print("  Estado actual: %s" % ingreso.estado)
print("  Puede hacer check-in: %s" % (ingreso.estado == 'PROGRAMADO'))

if ingreso.estado == 'PROGRAMADO':
    print("\nIntentando check-in...")
    ingreso.estado = 'EN_PROCESO'
    ingreso.fecha_inicio = timezone.now()
    ingreso.save()
    print("  Check-in exitoso! Nuevo estado: %s" % ingreso.estado)
else:
    print("  No puede hacer check-in. Estado: %s" % ingreso.estado)

# Comparar con ingreso 20 (que ya está EN_PROCESO)
print("\n" + "="*50)
ingreso20 = IngresoTaller.objects.get(pk=20)
print("Ingreso 20 (para comparar):")
print("  Estado: %s" % ingreso20.estado)
print("  Puede hacer check-in: %s" % (ingreso20.estado == 'PROGRAMADO'))
