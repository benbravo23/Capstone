#!/usr/bin/env python
"""Vincular RegistroGuardia con IngresoTaller para GWXL25"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/'.join(__file__.split('/')[:-1]))
django.setup()

from ingresos.models import IngresoTaller, RegistroGuardia
from vehiculos.models import Vehiculo

# Buscar vehículo
v = Vehiculo.objects.filter(patente='GWXL25').first()
if not v:
    print("Vehículo GWXL25 no encontrado")
    sys.exit(1)

# Buscar RegistroGuardia más reciente
r = RegistroGuardia.objects.filter(patente__iexact='GWXL25').order_by('-fecha_entrada').first()
if not r:
    print("RegistroGuardia para GWXL25 no encontrado")
    sys.exit(1)

# Buscar IngresoTaller programado
i = IngresoTaller.objects.filter(vehiculo=v, estado='PROGRAMADO').first()
if not i:
    print("IngresoTaller programado para GWXL25 no encontrado")
    sys.exit(1)

# Vincular
i.registro_guardia = r
i.save()

print(f"✅ Vinculado exitosamente:")
print(f"   Vehículo: {v.patente}")
print(f"   IngresoTaller ID: {i.pk}")
print(f"   RegistroGuardia ID: {r.pk}")
print(f"   Ahora puedes hacer check-in para {v.patente}")
