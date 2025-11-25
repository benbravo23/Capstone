import os
import django
from django.utils import timezone

essential_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure project root is in path
import sys
if essential_path not in sys.path:
    sys.path.insert(0, essential_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from usuarios.models import Usuario
from vehiculos.models import Vehiculo
from ingresos.forms import SolicitudIngresoForm
from ingresos.models import SolicitudIngreso, IngresoTaller
from django.utils import timezone
from datetime import datetime, timedelta

print('=== Test script start ===')

# Create or get test vehiculo
patente = 'ZZZTEST'
veh, created = Vehiculo.objects.get_or_create(patente=patente, defaults={'marca':'TestMarca','modelo':'X','año':2020,'vin':'VIN'+patente,'activo':True})
print(f'Vehiculo: {veh.patente} (created={created})')

# Create or get chofer (usuario usa email como identificador)
chofer_email = 'chofer_test@example.com'
try:
    chofer = Usuario.objects.get(email=chofer_email)
    c_created = False
except Usuario.DoesNotExist:
    # usar create_user del manager para validar campos requeridos
    unique_rut = 'RUT' + timezone.now().strftime('%Y%m%d%H%M%S')
    chofer = Usuario.objects.create_user(email=chofer_email, nombre='Chofer Test', rut=unique_rut, password='testpass', rol='CHOFER', activo=True)
    c_created = True
print(f'Chofer: {chofer.email} (created={c_created})')

# Create or get supervisor
sup_email = 'supervisor_test@example.com'
try:
    sup = Usuario.objects.get(email=sup_email)
    s_created = False
except Usuario.DoesNotExist:
    unique_rut = 'RUT' + (timezone.now() + timedelta(seconds=1)).strftime('%Y%m%d%H%M%S')
    sup = Usuario.objects.create_user(email=sup_email, nombre='Supervisor Test', rut=unique_rut, password='testpass', rol='SUPERVISOR', activo=True)
    s_created = True
print(f'Supervisor: {sup.email} (created={s_created})')

# Create a solicitud via form (simulate chofer)
form_data = {'patente': patente, 'motivo': 'Prueba automatizada', 'telefono': '', 'ruta': ''}
form = SolicitudIngresoForm(data=form_data, chofer=chofer)
if form.is_valid():
    solicitud = form.save()
    print('Solicitud creada id=', solicitud.pk, 'estado=', solicitud.estado)
else:
    print('Formulario inválido:', form.errors.as_json())
    sys.exit(1)

# Supervisor intenta agendar un slot mañana a las 09:00
mañana = timezone.localtime(timezone.now()).date() + timedelta(days=1)
chosen_dt = datetime(mañana.year, mañana.month, mañana.day, 9, 0, 0)
from django.utils.timezone import make_aware
chosen_dt = make_aware(chosen_dt)

# Verificar ocupación
inicio = chosen_dt
fin = chosen_dt + timedelta(hours=1)
ocupado = IngresoTaller.objects.filter(fecha_programada__gte=inicio, fecha_programada__lt=fin, estado__in=['PROGRAMADO','EN_PROCESO']).exists()
if ocupado:
    print('Slot ocupado; test cannot continue.')
else:
    ingreso = IngresoTaller.objects.create(
        vehiculo=solicitud.vehiculo,
        fecha_programada=chosen_dt,
        motivo=solicitud.motivo or 'Solicitud automatizada',
        chofer=solicitud.chofer,
        supervisor=sup,
        estado=IngresoTaller.Estado.PROGRAMADO,
    )
    solicitud.estado = 'APROBADA'
    solicitud.supervisor = sup
    solicitud.fecha_respuesta = timezone.now()
    solicitud.ingreso_taller = ingreso
    solicitud.fecha_estimada_ingreso = chosen_dt
    solicitud.save()
    print('Ingreso creado id=', ingreso.pk, 'y solicitud aprobada id=', solicitud.pk)

print('=== Test script end ===')
