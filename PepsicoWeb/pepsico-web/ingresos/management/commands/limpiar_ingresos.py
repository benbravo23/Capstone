from django.core.management.base import BaseCommand
from ingresos.models import IngresoTaller, Pausa, HistorialTarea, SolicitudIngreso, RegistroGuardia
from django.db import transaction


class Command(BaseCommand):
    help = 'Limpia todos los datos de ingresos, solicitudes, registros de guardia e historiales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar la eliminación sin preguntar',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        confirm = options.get('confirm', False)

        # Contar registros
        ingresos_count = IngresoTaller.objects.count()
        pausas_count = Pausa.objects.count()
        historial_count = HistorialTarea.objects.count()
        solicitudes_count = SolicitudIngreso.objects.count()
        registros_guardia_count = RegistroGuardia.objects.count()

        total = ingresos_count + pausas_count + historial_count + solicitudes_count + registros_guardia_count

        if total == 0:
            self.stdout.write(self.style.WARNING('No hay datos para limpiar.'))
            return

        # Mostrar confirmación
        self.stdout.write(self.style.WARNING(f'\n⚠️  Se van a eliminar:'))
        self.stdout.write(f'   • {ingresos_count} Ingresos al Taller')
        self.stdout.write(f'   • {pausas_count} Pausas')
        self.stdout.write(f'   • {historial_count} Historiales de Tareas')
        self.stdout.write(f'   • {solicitudes_count} Solicitudes de Ingreso (Chofer)')
        self.stdout.write(f'   • {registros_guardia_count} Registros de Entrada/Salida (Guardia)')
        self.stdout.write(f'\n   Total: {total} registros\n')

        if not confirm:
            respuesta = input('¿Estás seguro de que deseas continuar? (s/n): ')
            if respuesta.lower() != 's':
                self.stdout.write(self.style.ERROR('Operación cancelada.'))
                return

        # Eliminar datos (en orden, respetando relaciones)
        try:
            # Las pausas se eliminarán en cascada con ingresos, pero lo hacemos explícito
            Pausa.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ {pausas_count} pausas eliminadas'))

            HistorialTarea.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ {historial_count} historiales eliminados'))

            IngresoTaller.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ {ingresos_count} ingresos eliminados'))

            SolicitudIngreso.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ {solicitudes_count} solicitudes de ingreso eliminadas'))

            RegistroGuardia.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ {registros_guardia_count} registros de guardia eliminados'))

            self.stdout.write(self.style.SUCCESS(f'\n✅ Limpieza completada exitosamente. {total} registros eliminados.\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error al limpiar: {str(e)}\n'))
            raise
