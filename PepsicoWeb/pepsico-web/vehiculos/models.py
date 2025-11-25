
from django.db import models
from django.utils.translation import gettext_lazy as _


class Vehiculo(models.Model):
    """
    Modelo de vehículo de la flota PepsiCo.
    """
    
    class TipoVehiculo(models.TextChoices):
        CAMION = 'CAMION', _('Camión')
        CAMIONETA = 'CAMIONETA', _('Camioneta')
        FURGON = 'FURGON', _('Furgón')
        OTRO = 'OTRO', _('Otro')
    
    patente = models.CharField(_('patente'), max_length=10, unique=True)
    marca = models.CharField(_('marca'), max_length=50)
    modelo = models.CharField(_('modelo'), max_length=50)
    año = models.PositiveIntegerField(_('año'))
    vin = models.CharField(_('VIN'), max_length=17, unique=True, blank=True, null=True)
    tipo = models.CharField(
        _('tipo de vehículo'),
        max_length=20,
        choices=TipoVehiculo.choices,
        default=TipoVehiculo.CAMION
    )
    flota = models.CharField(_('flota'), max_length=50, blank=True)
    kilometraje = models.PositiveIntegerField(_('kilometraje'), default=0)
    activo = models.BooleanField(_('activo'), default=True)
    fecha_creacion = models.DateTimeField(_('fecha de creación'), auto_now_add=True)
    fecha_modificacion = models.DateTimeField(_('fecha de modificación'), auto_now=True)
    
    class Meta:
        verbose_name = _('vehículo')
        verbose_name_plural = _('vehículos')
        ordering = ['patente']
        indexes = [
            models.Index(fields=['patente']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"
    

    @property
    def nombre_completo(self):
        return f"{self.marca} {self.modelo} ({self.año})"


# Modelo para documentos asociados a vehículos

class DocumentoVehiculo(models.Model):
    """Documento asociado a un vehículo (ej: SOAP, siniestros, etc)."""
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='documentos_vehiculo')
    tipo_documento = models.CharField(_('tipo de documento'), max_length=50)
    archivo = models.FileField(_('archivo'), upload_to='vehiculos/')
    descripcion = models.TextField(_('descripción'), blank=True)
    fecha_subida = models.DateTimeField(_('fecha de subida'), auto_now_add=True)

    class Meta:
        verbose_name = _('documento de vehículo')
        verbose_name_plural = _('documentos de vehículo')
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.tipo_documento} - {self.vehiculo.patente}"