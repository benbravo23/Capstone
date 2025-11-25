from django.db import models
from django.utils.translation import gettext_lazy as _
from usuarios.models import Usuario


class Notificacion(models.Model):
    """
    Modelo de notificaciones para usuarios.
    """
    
    class TipoNotificacion(models.TextChoices):
        INGRESO_PROGRAMADO = 'INGRESO_PROGRAMADO', _('Ingreso Programado')
        INGRESO_INICIADO = 'INGRESO_INICIADO', _('Ingreso Iniciado')
        TAREA_ASIGNADA = 'TAREA_ASIGNADA', _('Tarea Asignada')
        TAREA_COMPLETADA = 'TAREA_COMPLETADA', _('Tarea Completada')
        PAUSA_REGISTRADA = 'PAUSA_REGISTRADA', _('Pausa Registrada')
        INGRESO_TERMINADO = 'INGRESO_TERMINADO', _('Ingreso Terminado')
        DOCUMENTO_SUBIDO = 'DOCUMENTO_SUBIDO', _('Documento Subido')
        VEHICULO_LISTO_RETIRO = 'VEHICULO_LISTO_RETIRO', _('Vehículo Listo para Retiro')
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        verbose_name=_('usuario')
    )
    tipo = models.CharField(
        _('tipo'),
        max_length=30,
        choices=TipoNotificacion.choices
    )
    titulo = models.CharField(_('título'), max_length=255)
    mensaje = models.TextField(_('mensaje'))
    leida = models.BooleanField(_('leída'), default=False)
    url = models.CharField(_('URL'), max_length=500, blank=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    fecha_creacion = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    fecha_leida = models.DateTimeField(_('fecha leída'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('notificación')
        verbose_name_plural = _('notificaciones')
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['usuario', 'leida']),
            models.Index(fields=['-fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.nombre}"
    
    def marcar_como_leida(self):
        """Marca la notificación como leída."""
        if not self.leida:
            from django.utils import timezone
            self.leida = True
            self.fecha_leida = timezone.now()
            self.save()