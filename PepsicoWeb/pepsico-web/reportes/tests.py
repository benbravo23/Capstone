from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario
from vehiculos.models import Vehiculo
from ingresos.models import IngresoTaller


class ReportesPermisosTest(TestCase):
	def setUp(self):
		# Usuarios con roles
		self.admin = Usuario.objects.create_user(email='admin@example.com', nombre='Admin', rut='1', password='pass')
		self.admin.rol = 'ADMIN'
		self.admin.is_staff = True
		self.admin.save()

		self.supervisor = Usuario.objects.create_user(email='sup@example.com', nombre='Supervisor', rut='2', password='pass')
		self.supervisor.rol = 'SUPERVISOR'
		self.supervisor.save()

		self.bodega = Usuario.objects.create_user(email='bode@example.com', nombre='Bodega', rut='3', password='pass')
		self.bodega.rol = 'BODEGA'
		self.bodega.save()

		# Crear datos mínimos necesarios para que la vista pueda renderizar
		self.vehiculo = Vehiculo.objects.create(patente='ZZZ999', marca='M', modelo='X', año=2020)
		self.ingreso = IngresoTaller.objects.create(vehiculo=self.vehiculo, fecha_programada=timezone.now(), motivo='test')

	def test_reportes_repuestos_admin_supervisor_acceso(self):
		url = reverse('reporte_repuestos')

		# Admin
		self.client.force_login(self.admin)
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.client.logout()

		# Supervisor
		self.client.force_login(self.supervisor)
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.client.logout()

	def test_reportes_repuestos_bodega_denegado(self):
		url = reverse('reporte_repuestos')
		self.client.force_login(self.bodega)
		resp = self.client.get(url)
		# Esperamos 403 por permisos (o redirect si la app maneja así)
		self.assertIn(resp.status_code, (302, 403))

