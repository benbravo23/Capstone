from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from vehiculos.models import Vehiculo
from usuarios.models import Usuario


class Maquina(models.Model):
    """
    Modelo de máquinas del taller para revisión de vehículos.
    El taller cuenta con 4 máquinas: 2 elevadores 3D y 2 elevadores de tijera.
    """
    
    class Tipo(models.TextChoices):
        ELEVADOR_3D = 'ELEVADOR_3D', _('Elevador 3D')
        ELEVADOR_TIJERA = 'ELEVADOR_TIJERA', _('Elevador de Tijera')
    
    nombre = models.CharField(_('nombre de la máquina'), max_length=100)
    tipo = models.CharField(
        _('tipo de máquina'),
        max_length=20,
        choices=Tipo.choices
    )
    numero = models.PositiveIntegerField(_('número de máquina'), help_text=_('Identificador numérico de la máquina'))
    activa = models.BooleanField(_('activa'), default=True)
    descripcion = models.TextField(_('descripción'), blank=True)
    fecha_creacion = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('máquina')
        verbose_name_plural = _('máquinas')
        ordering = ['tipo', 'numero']
        unique_together = [['tipo', 'numero']]
    
    def __str__(self):
        return f"{self.get_tipo_display()} #{self.numero} - {self.nombre}"


class IngresoTaller(models.Model):
    """
    Modelo de ingreso de vehículo al taller.
    """
    
    class Estado(models.TextChoices):
        PROGRAMADO = 'PROGRAMADO', _('Programado')
        EN_PROCESO = 'EN_PROCESO', _('En Proceso')
        EN_PAUSA = 'EN_PAUSA', _('En Pausa')
        TERMINADO = 'TERMINADO', _('Terminado')
        RETIRADO = 'RETIRADO', _('Retirado')
        CANCELADO = 'CANCELADO', _('Cancelado')
    
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name='ingresos',
        verbose_name=_('vehículo')
    )
    fecha_programada = models.DateTimeField(_('fecha programada'))
    fecha_llegada = models.DateTimeField(_('fecha de llegada'), null=True, blank=True)
    fecha_inicio = models.DateTimeField(_('fecha de inicio'), null=True, blank=True)
    fecha_termino = models.DateTimeField(_('fecha de término'), null=True, blank=True)
    estado = models.CharField(
        _('estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PROGRAMADO
    )
    motivo = models.TextField(_('motivo del ingreso'))
    observaciones = models.TextField(_('observaciones'), blank=True)
    repuesto_necesario = models.CharField(_('repuesto necesario'), max_length=255, blank=True)
    kilometraje_ingreso = models.PositiveIntegerField(_('kilometraje al ingreso'), null=True, blank=True)
    
    # Usuarios involucrados
    chofer = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_como_chofer',
        verbose_name=_('chofer')
    )
    supervisor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_supervisados',
        verbose_name=_('supervisor')
    )
    
    # Registro de guardia (control de acceso)
    registro_guardia = models.ForeignKey(
        'RegistroGuardia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_taller',
        verbose_name=_('registro de guardia')
    )
    
    # Máquina asignada para la revisión
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos',
        verbose_name=_('máquina asignada')
    )
    
    fecha_creacion = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    fecha_modificacion = models.DateTimeField(_('fecha de modificación'), auto_now=True)
    
    class Meta:
        verbose_name = _('ingreso al taller')
        verbose_name_plural = _('ingresos al taller')
        ordering = ['-fecha_programada']
        indexes = [
            models.Index(fields=['vehiculo', 'estado']),
            models.Index(fields=['fecha_programada']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"{self.vehiculo.patente} - {self.fecha_programada.strftime('%Y-%m-%d %H:%M')}"
    
    def clean(self):
        """Validación para evitar solapamientos de agenda por máquina."""
        if self.fecha_programada and self.maquina:
            # Buscar ingresos que se solapen en la misma máquina
            inicio = self.fecha_programada
            fin = self.fecha_programada + timedelta(hours=1)
            
            solapamientos = IngresoTaller.objects.filter(
                fecha_programada__gte=inicio,
                fecha_programada__lt=fin,
                maquina=self.maquina,
                estado__in=['PROGRAMADO', 'EN_PROCESO']
            ).exclude(pk=self.pk)
            
            if solapamientos.exists():
                raise ValidationError(
                    _('La máquina %(maquina)s ya está ocupada en ese horario. Por favor, elija otra máquina u otro horario.'),
                    code='maquina_ocupada',
                    params={'maquina': self.maquina.nombre}
                )
    
    @property
    def duracion_total_minutos(self):
        """Calcula la duración total del ingreso en minutos."""
        if self.fecha_inicio and self.fecha_termino:
            delta = self.fecha_termino - self.fecha_inicio
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def tiempo_en_pausas_minutos(self):
        """Calcula el tiempo total en pausas."""
        total = 0
        for pausa in self.pausas.all():
            if pausa.duracion_minutos:
                total += pausa.duracion_minutos
        return total
    
    @property
    def tiempo_efectivo_minutos(self):
        """Tiempo efectivo = tiempo total - tiempo en pausas."""
        if self.duracion_total_minutos:
            return self.duracion_total_minutos - self.tiempo_en_pausas_minutos
        return None


class Pausa(models.Model):
    """
    Modelo de pausas durante el proceso de reparación.
    """
    
    ingreso = models.ForeignKey(
        IngresoTaller,
        on_delete=models.CASCADE,
        related_name='pausas',
        verbose_name=_('ingreso')
    )
    motivo = models.CharField(_('motivo de la pausa'), max_length=255)
    descripcion = models.TextField(_('descripción'), blank=True)
    fecha_inicio = models.DateTimeField(_('fecha de inicio'))
    fecha_fin = models.DateTimeField(_('fecha de fin'), null=True, blank=True)
    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pausas_registradas',
        verbose_name=_('registrado por')
    )
    
    class Meta:
        verbose_name = _('pausa')
        verbose_name_plural = _('pausas')
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"Pausa: {self.motivo} - {self.ingreso}"
    
    @property
    def duracion_minutos(self):
        """Calcula la duración de la pausa en minutos."""
        if self.fecha_fin:
            delta = self.fecha_fin - self.fecha_inicio
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def esta_activa(self):
        """Verifica si la pausa está activa (sin fecha de fin)."""
        return self.fecha_fin is None


class Tarea(models.Model):
    """
    Modelo de tareas realizadas durante el ingreso.
    """
    
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', _('Pendiente')
        EN_PROCESO = 'EN_PROCESO', _('En Proceso')
        PAUSADA = 'PAUSADA', _('Pausada')
        COMPLETADA = 'COMPLETADA', _('Completada')
        CANCELADA = 'CANCELADA', _('Cancelada')
    
    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', _('Baja')
        MEDIA = 'MEDIA', _('Media')
        ALTA = 'ALTA', _('Alta')
        URGENTE = 'URGENTE', _('Urgente')
    
    ingreso = models.ForeignKey(
        IngresoTaller,
        on_delete=models.CASCADE,
        related_name='tareas',
        verbose_name=_('ingreso')
    )
    titulo = models.CharField(_('título'), max_length=255)
    descripcion = models.TextField(_('descripción'), blank=True)
    estado = models.CharField(
        _('estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    prioridad = models.CharField(
        _('prioridad'),
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        blank=True
    )
    mecanico = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tareas_asignadas',
        verbose_name=_('mecánico')
    )
    tiempo_estimado_minutos = models.PositiveIntegerField(_('tiempo estimado (min)'), null=True, blank=True)
    tiempo_invertido_minutos = models.PositiveIntegerField(_('tiempo invertido (min)'), default=0)
    repuestos_utilizados = models.TextField(_('repuestos utilizados'), blank=True)
    observaciones = models.TextField(_('observaciones'), blank=True)
    fecha_creacion = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    fecha_asignacion = models.DateTimeField(_('fecha de asignación'), auto_now_add=True)
    fecha_inicio = models.DateTimeField(_('fecha de inicio'), null=True, blank=True)
    fecha_completada = models.DateTimeField(_('fecha completada'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('tarea')
        verbose_name_plural = _('tareas')
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.ingreso}"
    
    @property
    def tiempo_transcurrido_minutos(self):
        """Calcula el tiempo transcurrido desde que la tarea fue iniciada."""
        if self.fecha_inicio:
            if self.fecha_completada:
                delta = self.fecha_completada - self.fecha_inicio
            else:
                delta = timezone.now() - self.fecha_inicio
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def porcentaje_tiempo(self):
        """Calcula el porcentaje de tiempo usado vs estimado."""
        if self.tiempo_estimado_minutos and self.tiempo_estimado_minutos > 0:
            return int((self.tiempo_transcurrido_minutos / self.tiempo_estimado_minutos) * 100)
        return 0



class Documento(models.Model):
    """
    Modelo de documentos y fotos asociados a ingresos o vehículos.
    """
    
    class TipoDocumento(models.TextChoices):
        FOTO_INGRESO = 'FOTO_INGRESO', _('Foto de Ingreso')
        FOTO_DAÑO = 'FOTO_DAÑO', _('Foto de Daño')
        INFORME_SINIESTRO = 'INFORME_SINIESTRO', _('Informe de Siniestro')
        ORDEN_TRABAJO = 'ORDEN_TRABAJO', _('Orden de Trabajo')
        FACTURA = 'FACTURA', _('Factura')
        OTRO = 'OTRO', _('Otro')
    
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name=_('vehículo'),
        null=True,
        blank=True
    )
    ingreso = models.ForeignKey(
        IngresoTaller,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name=_('ingreso'),
        null=True,
        blank=True
    )
    tipo = models.CharField(
        _('tipo de documento'),
        max_length=30,
        choices=TipoDocumento.choices
    )
    archivo = models.FileField(_('archivo'), upload_to='documentos/%Y/%m/%d/')
    nombre_original = models.CharField(_('nombre original'), max_length=255)
    descripcion = models.TextField(_('descripción'), blank=True)
    subido_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documentos_subidos',
        verbose_name=_('subido por')
    )
    fecha_subida = models.DateTimeField(_('fecha de subida'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('documento')
        verbose_name_plural = _('documentos')
        ordering = ['-fecha_subida']
        indexes = [
            models.Index(fields=['vehiculo', 'tipo']),
            models.Index(fields=['ingreso']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre_original}"


class HistorialTarea(models.Model):
    """
    Modelo para rastrear el historial de cambios en las tareas.
    """
    
    class TipoCambio(models.TextChoices):
        CREACION = 'CREACION', _('Creación')
        ASIGNACION = 'ASIGNACION', _('Asignación')
        CAMBIO_ESTADO = 'CAMBIO_ESTADO', _('Cambio de Estado')
        CAMBIO_PRIORIDAD = 'CAMBIO_PRIORIDAD', _('Cambio de Prioridad')
        MODIFICACION = 'MODIFICACION', _('Modificación')
        COMENTARIO = 'COMENTARIO', _('Comentario')
    
    tarea = models.ForeignKey(
        Tarea,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name=_('tarea')
    )
    tipo_cambio = models.CharField(
        _('tipo de cambio'),
        max_length=30,
        choices=TipoCambio.choices
    )
    campo_modificado = models.CharField(_('campo modificado'), max_length=100, blank=True)
    valor_anterior = models.TextField(_('valor anterior'), blank=True)
    valor_nuevo = models.TextField(_('valor nuevo'), blank=True)
    descripcion = models.TextField(_('descripción del cambio'), blank=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cambios_tareas',
        verbose_name=_('usuario')
    )
    fecha = models.DateTimeField(_('fecha del cambio'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('historial de tarea')
        verbose_name_plural = _('historiales de tareas')
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['tarea', '-fecha']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.tarea.titulo} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"


class SolicitudIngreso(models.Model):
    """
    Modelo para solicitudes de ingreso de vehículos al taller.
    Los choferes solicitan ingreso y los supervisores aprueban o rechazan.
    """
    
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', _('Pendiente')
        APROBADA = 'APROBADA', _('Aprobada')
        RECHAZADA = 'RECHAZADA', _('Rechazada')
        COMPLETADA = 'COMPLETADA', _('Completada')
        RETIRADA = 'RETIRADA', _('Retirada')
        CANCELADA = 'CANCELADA', _('Cancelada')
    
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name='solicitudes_ingreso',
        verbose_name=_('vehículo')
    )
    chofer = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitudes_ingreso',
        verbose_name=_('chofer'),
        limit_choices_to={'rol': 'CHOFER'}
    )
    supervisor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_aprobadas',
        verbose_name=_('supervisor que aprobó'),
        limit_choices_to={'rol': 'SUPERVISOR'}
    )
    
    # Información de la solicitud
    fecha_solicitud = models.DateTimeField(_('fecha de solicitud'), auto_now_add=True)
    # La fecha estimada puede ser propuesta por el supervisor al aprobar
    # (los choferes no deben estimarla al crear la solicitud), por eso
    # permitimos null/blank para que la solicitud pueda crearse sin ella.
    fecha_estimada_ingreso = models.DateTimeField(_('fecha estimada de ingreso'), null=True, blank=True)
    motivo = models.TextField(_('motivo del ingreso'), blank=True)

    # Información de contacto opcional del chofer para pruebas y seguimiento
    telefono = models.CharField(_('teléfono de contacto'), max_length=30, blank=True)
    ruta = models.CharField(_('ruta (opcional)'), max_length=255, blank=True)
    
    # Estado
    estado = models.CharField(
        _('estado'),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    
    # Respuesta del supervisor
    fecha_respuesta = models.DateTimeField(_('fecha de respuesta'), null=True, blank=True)
    observaciones_supervisor = models.TextField(_('observaciones del supervisor'), blank=True)
    
    # Relación con ingreso creado
    ingreso_taller = models.OneToOneField(
        IngresoTaller,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitud_origen',
        verbose_name=_('ingreso al taller')
    )
    
    class Meta:
        verbose_name = _('solicitud de ingreso')
        verbose_name_plural = _('solicitudes de ingreso')
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['vehiculo', 'estado']),
            models.Index(fields=['chofer', 'estado']),
            models.Index(fields=['estado']),
            models.Index(fields=['-fecha_solicitud']),
        ]
        # Evitar múltiples solicitudes pendientes para el mismo vehículo
        constraints = [
            models.UniqueConstraint(
                fields=['vehiculo', 'estado'],
                condition=models.Q(estado='PENDIENTE'),
                name='unique_pending_request_per_vehicle'
            )
        ]
    
    def __str__(self):
        patente = self.vehiculo.patente if self.vehiculo_id else "Sin vehículo"
        return f"Solicitud {patente} - {self.get_estado_display()}"
    
    def clean(self):
        """Validar que no haya solicitudes activas para el mismo vehículo."""
        # Si vehiculo no está asignado, no hacer validación (será validado en el formulario)
        if not self.vehiculo_id:
            return
        
        solicitudes_activas = SolicitudIngreso.objects.filter(
            vehiculo=self.vehiculo,
            estado__in=['PENDIENTE', 'APROBADA']
        ).exclude(pk=self.pk)
        
        if solicitudes_activas.exists():
            raise ValidationError(
                _('Ya existe una solicitud activa para este vehículo.')
            )
    
    @property
    def dias_desde_solicitud(self):
        """Calcula los días desde que se hizo la solicitud."""
        delta = timezone.now() - self.fecha_solicitud
        return delta.days
    
    @property
    def esta_vencida(self):
        """Verifica si la solicitud tiene más de 7 días sin respuesta."""
        if self.estado == 'PENDIENTE':
            return self.dias_desde_solicitud > 7
        return False


class RegistroGuardia(models.Model):
    """
    Modelo para registrar controles de entrada/salida de vehículos a la planta por parte del guardia.
    IMPORTANTE: Este registro NO crea un IngresoTaller. Es solo un control de acceso.
    """
    
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name='registros_guardia',
        verbose_name=_('vehículo')
    )
    
    fecha_entrada = models.DateTimeField(_('fecha de entrada'), auto_now_add=True)
    fecha_salida = models.DateTimeField(_('fecha de salida'), null=True, blank=True, default=None)
    
    patente = models.CharField(_('patente'), max_length=20)
    marca = models.CharField(_('marca'), max_length=100, blank=True)
    modelo = models.CharField(_('modelo'), max_length=100, blank=True)
    
    motivo = models.TextField(_('motivo'), blank=True, help_text=_('Razón del ingreso a la planta'))
    
    chofer_nombre = models.CharField(_('nombre del chofer'), max_length=200, blank=True)
    chofer = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_como_chofer',
        verbose_name=_('chofer')
    )
    
    observaciones = models.TextField(_('observaciones'), blank=True)
    
    registrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registros_guardados',
        verbose_name=_('registrado por (guardia)')
    )
    
    class Meta:
        verbose_name = _('registro de guardia')
        verbose_name_plural = _('registros de guardia')
        ordering = ['-fecha_entrada']
        indexes = [
            models.Index(fields=['vehiculo', '-fecha_entrada']),
            models.Index(fields=['-fecha_entrada']),
        ]
    
    def __str__(self):
        return f"{self.patente} - {self.fecha_entrada.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duracion_minutos(self):
        """Calcula duración de la permanencia en la planta."""
        if self.fecha_salida and self.fecha_entrada:
            delta = self.fecha_salida - self.fecha_entrada
            minutos = int(delta.total_seconds() / 60)
            return max(0, minutos)  # Asegurar que no sea negativo
        return 0  # Retornar 0 en lugar de None
    
    @property
    def duracion_formateada(self):
        """Retorna la duración en formato legible (ej: '1h 30min')."""
        duracion = self.duracion_minutos
        if duracion == 0:
            return None
        horas = duracion // 60
        minutos = duracion % 60
        if horas > 0:
            return f"{horas}h {minutos}min"
        return f"{minutos}min"

# List of common spare parts
REPUESTOS_COMUNES = [
    "Filtro de aceite",
    "Filtro de aire",
    "Filtro de combustible",
    "Pastillas de freno",
    "Discos de freno",
    "Bujías",
    "Amortiguadores",
    "Correa de distribución",
    "Batería",
    "Radiador"
]