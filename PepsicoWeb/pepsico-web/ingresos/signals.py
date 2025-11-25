from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Tarea, HistorialTarea
from django.utils import timezone


# Diccionario para almacenar el estado anterior de la tarea
_tarea_anterior = {}


@receiver(pre_save, sender=Tarea)
def guardar_estado_anterior(sender, instance, **kwargs):
    """Guarda el estado anterior de la tarea antes de modificarla."""
    if instance.pk:
        try:
            tarea_anterior = Tarea.objects.get(pk=instance.pk)
            _tarea_anterior[instance.pk] = {
                'estado': tarea_anterior.estado,
                'prioridad': tarea_anterior.prioridad,
                'mecanico': tarea_anterior.mecanico,
                'titulo': tarea_anterior.titulo,
                'descripcion': tarea_anterior.descripcion,
            }
        except Tarea.DoesNotExist:
            pass


@receiver(post_save, sender=Tarea)
def registrar_cambios_tarea(sender, instance, created, **kwargs):
    """Registra automáticamente los cambios en el historial de la tarea."""
    
    # Obtener el usuario del contexto (si está disponible)
    usuario = getattr(instance, '_usuario_modificador', None)
    
    if created:
        # Registrar creación de la tarea
        HistorialTarea.objects.create(
            tarea=instance,
            tipo_cambio='CREACION',
            descripcion=f'Tarea "{instance.titulo}" creada',
            usuario=usuario
        )
        
        # Si se asignó un mecánico al crear
        if instance.mecanico:
            HistorialTarea.objects.create(
                tarea=instance,
                tipo_cambio='ASIGNACION',
                campo_modificado='mecanico',
                valor_nuevo=instance.mecanico.nombre,
                descripcion=f'Tarea asignada a {instance.mecanico.nombre}',
                usuario=usuario
            )
    else:
        # Verificar cambios en tarea existente
        if instance.pk in _tarea_anterior:
            anterior = _tarea_anterior[instance.pk]
            
            # Cambio de estado
            if anterior['estado'] != instance.estado:
                HistorialTarea.objects.create(
                    tarea=instance,
                    tipo_cambio='CAMBIO_ESTADO',
                    campo_modificado='estado',
                    valor_anterior=anterior['estado'],
                    valor_nuevo=instance.estado,
                    descripcion=f'Estado cambiado de {anterior["estado"]} a {instance.estado}',
                    usuario=usuario
                )
                
                # Registrar fecha de completado si cambió a COMPLETADA
                if instance.estado == 'COMPLETADA' and not instance.fecha_completada:
                    instance.fecha_completada = timezone.now()
                    instance.save(update_fields=['fecha_completada'])
            
            # Cambio de prioridad
            if anterior['prioridad'] != instance.prioridad:
                HistorialTarea.objects.create(
                    tarea=instance,
                    tipo_cambio='CAMBIO_PRIORIDAD',
                    campo_modificado='prioridad',
                    valor_anterior=anterior['prioridad'],
                    valor_nuevo=instance.prioridad,
                    descripcion=f'Prioridad cambiada de {anterior["prioridad"]} a {instance.prioridad}',
                    usuario=usuario
                )
            
            # Cambio de mecánico (asignación/reasignación)
            if anterior['mecanico'] != instance.mecanico:
                valor_ant = anterior['mecanico'].nombre if anterior['mecanico'] else 'Sin asignar'
                valor_nue = instance.mecanico.nombre if instance.mecanico else 'Sin asignar'
                
                HistorialTarea.objects.create(
                    tarea=instance,
                    tipo_cambio='ASIGNACION',
                    campo_modificado='mecanico',
                    valor_anterior=valor_ant,
                    valor_nuevo=valor_nue,
                    descripcion=f'Mecánico cambiado de {valor_ant} a {valor_nue}',
                    usuario=usuario
                )
            
            # Cambio de título o descripción
            if anterior['titulo'] != instance.titulo or anterior['descripcion'] != instance.descripcion:
                HistorialTarea.objects.create(
                    tarea=instance,
                    tipo_cambio='MODIFICACION',
                    descripcion='Detalles de la tarea modificados',
                    usuario=usuario
                )
            
            # Limpiar el diccionario temporal
            del _tarea_anterior[instance.pk]