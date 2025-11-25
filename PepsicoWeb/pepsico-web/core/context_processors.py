from django.utils.translation import gettext_lazy as _


def solicitudes_pendientes_count(request):
    """
    Context processor que agrega el conteo de solicitudes pendientes para supervisores
    y vehículos listos para retiro para choferes.
    """
    solicitudes_count = 0
    vehiculos_listos_count = 0
    
    if request.user.is_authenticated:
        if request.user.rol == 'SUPERVISOR':
            from ingresos.models import SolicitudIngreso
            solicitudes_count = SolicitudIngreso.objects.filter(estado='PENDIENTE').count()
        elif request.user.rol == 'CHOFER':
            from ingresos.models import IngresoTaller
            vehiculos_listos_count = IngresoTaller.objects.filter(
                chofer=request.user,
                estado='TERMINADO'
            ).count()
    
    return {
        'solicitudes_pendientes_count': solicitudes_count,
        'vehiculos_listos_retiro_count': vehiculos_listos_count,
    }
