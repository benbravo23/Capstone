from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario
from vehiculos.models import Vehiculo
from .models import IngresoTaller, Tarea, Documento
from .views import MAX_PHOTOS, MAX_PHOTO_SIZE_MB

from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
import shutil
import io
from PIL import Image


class TareaCreateViewTest(TestCase):
	def setUp(self):
		# Crear usuario con rol permitido
		self.user = Usuario.objects.create_user(
			email='meca@example.com', nombre='Mecánico Test', rut='12345678-9', password='testpass'
		)
		self.user.rol = 'MECANICO'
		self.user.save()

		# Crear vehículo e ingreso
		self.vehiculo = Vehiculo.objects.create(
			patente='ABC123', marca='Marca', modelo='Modelo', año=2020
		)

		self.ingreso = IngresoTaller.objects.create(
			vehiculo=self.vehiculo,
			fecha_programada=timezone.now(),
			motivo='Motivo de prueba'
		)

	def test_crear_tarea_post_crea_y_redirige(self):
		self.client.force_login(self.user)

		url = reverse('tarea_create', args=[self.ingreso.pk])
		data = {
			'titulo': 'Cambio de prueba',
			# no enviamos 'estado' porque en la creación la plantilla no lo muestra
		}

		response = self.client.post(url, data)

		# Debe redirigir al detalle del ingreso
		self.assertEqual(response.status_code, 302)

		# Verificar que la tarea fue creada
		tarea_exists = Tarea.objects.filter(ingreso=self.ingreso, titulo='Cambio de prueba').exists()
		self.assertTrue(tarea_exists)


class GuardRegistroUploadTest(TestCase):
	def setUp(self):
		# crear usuario guardia
		self.user = Usuario.objects.create_user(
			email='guard@example.com', nombre='Guard Test', rut='98765432-1', password='guardpass', rol='GUARDIA'
		)
		# preparar media temp
		self._media_root = tempfile.mkdtemp(prefix='test_media_')
		self._override = override_settings(MEDIA_ROOT=self._media_root)
		self._override.enable()

	def tearDown(self):
		# desactivar override y limpiar media
		try:
			self._override.disable()
		finally:
			shutil.rmtree(self._media_root, ignore_errors=True)

	def _create_image_bytes(self, fmt='PNG'):
		buf = io.BytesIO()
		img = Image.new('RGB', (10, 10), color=(255, 255, 255))
		img.save(buf, format=fmt)
		return buf.getvalue()

	def test_guard_registro_con_imagenes_crea_ingreso_y_documentos(self):
		self.client.force_login(self.user)

		url = reverse('guard_dashboard')
		patente = 'TEST123'
		data = {
			'patente': patente,
			'marca': 'MarcaTest',
			'motivo': 'Chequeo ingreso',
			'chofer_nombre': 'Chofer Prueba',
		}

		# crear dos imágenes en memoria
		img1 = SimpleUploadedFile('img1.png', self._create_image_bytes(), content_type='image/png')
		img2 = SimpleUploadedFile('img2.png', self._create_image_bytes(), content_type='image/png')

		# Incluir archivos en la petición
		response = self.client.post(url, data={'patente': data['patente'], 'marca': data['marca'], 'motivo': data['motivo'], 'chofer_nombre': data['chofer_nombre'], 'photos': [img1, img2]}, follow=True)

		# debe redirigir y mostrar dashboard (follow=True => 200)
		self.assertEqual(response.status_code, 200)

		# verificar ingreso creado
		ingreso_qs = IngresoTaller.objects.filter(vehiculo__patente__iexact=patente)
		self.assertTrue(ingreso_qs.exists(), 'No se creó el IngresoTaller')
		ingreso = ingreso_qs.first()
		self.assertEqual(ingreso.estado, 'EN_PROCESO')

		# verificar documentos creados
		docs = Documento.objects.filter(ingreso=ingreso, tipo='FOTO_INGRESO')
		self.assertEqual(docs.count(), 2, f'Esperado 2 documentos, encontró {docs.count()}')

	def test_guard_registro_too_many_images_is_rejected(self):
		self.client.force_login(self.user)
		url = reverse('guard_dashboard')
		patente = 'TOOMANY1'
		data = {'patente': patente, 'marca': 'M', 'motivo': 'motivo', 'chofer_nombre': 'Chofer'}

		imgs = [SimpleUploadedFile(f'img{i}.png', self._create_image_bytes(), content_type='image/png') for i in range(6)]

		response = self.client.post(url, data={'patente': data['patente'], 'marca': data['marca'], 'motivo': data['motivo'], 'chofer_nombre': data['chofer_nombre'], 'photos': imgs}, follow=True)
		# Should re-render form with errors and not create ingreso
		self.assertEqual(response.status_code, 200)
		self.assertFalse(IngresoTaller.objects.filter(vehiculo__patente__iexact=patente).exists())

	def test_guard_registro_large_image_is_rejected(self):
		self.client.force_login(self.user)
		url = reverse('guard_dashboard')
		patente = 'LARGE1'
		data = {'patente': patente, 'marca': 'M', 'motivo': 'motivo', 'chofer_nombre': 'Chofer'}

		# create a fake large file > MAX_PHOTO_SIZE_MB
		big_bytes = b'a' * ((MAX_PHOTO_SIZE_MB * 1024 * 1024) + 1)
		big_file = SimpleUploadedFile('big.png', big_bytes, content_type='image/png')

		response = self.client.post(url, data={'patente': data['patente'], 'marca': data['marca'], 'motivo': data['motivo'], 'chofer_nombre': data['chofer_nombre'], 'photos': [big_file]}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(IngresoTaller.objects.filter(vehiculo__patente__iexact=patente).exists())


class RoleCaseInsensitiveTest(TestCase):
	"""Verifica que las comprobaciones de rol sean insensibles a mayúsculas/minúsculas."""

	def setUp(self):
		# usuario guardia con capitalización diferente
		self.guard_user = Usuario.objects.create_user(
			email='guard_case@example.com', nombre='Guard Case', rut='55555555-5', password='guardpass'
		)
		self.guard_user.rol = 'Guardia'  # capitalización distinta
		self.guard_user.save()

		# usuario admin con minúsculas
		self.admin_user = Usuario.objects.create_user(
			email='admin_case@example.com', nombre='Admin Case', rut='66666666-6', password='adminpass'
		)
		self.admin_user.rol = 'admin'
		self.admin_user.save()

		# crear vehículo e ingreso para endpoints que lo requieran
		self.vehiculo = Vehiculo.objects.create(patente='CASE1', marca='M', modelo='X', año=2021)

	def test_guard_access_with_mixed_case(self):
		# El dashboard de guardia está protegido por @role_required(['GUARDIA'])
		self.client.force_login(self.guard_user)
		url = reverse('guard_dashboard')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

	def test_admin_access_with_lowercase(self):
		# La vista de crear ingreso requiere ADMIN o SUPERVISOR
		self.client.force_login(self.admin_user)
		url = reverse('ingreso_create')
		resp = self.client.get(url)
		# admin debería tener acceso (200)
		self.assertEqual(resp.status_code, 200)

