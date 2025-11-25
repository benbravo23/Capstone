from django.urls import path
from . import views

urlpatterns = [
    path('', views.ingresos_list, name='ingresos_list'),
    path('<int:pk>/', views.ingreso_detail, name='ingreso_detail'),
    path('crear/', views.ingreso_create, name='ingreso_create'),
    path('<int:pk>/checkin/', views.ingreso_checkin, name='ingreso_checkin'),
    path('<int:pk>/retirado/', views.ingreso_marcar_retirado, name='ingreso_marcar_retirado'),
    path('<int:pk>/pausar/', views.ingreso_pausar, name='ingreso_pausar'),
    path('<int:pk>/reanudar/', views.ingreso_reanudar, name='ingreso_reanudar'),
    path('<int:pk>/terminar/', views.ingreso_terminar, name='ingreso_terminar'),
    path('<int:pk>/eliminar/', views.ingreso_eliminar, name='ingreso_eliminar'),
    path('<int:ingreso_pk>/tarea/crear/', views.tarea_create, name='tarea_create'),
    path('guardia/', views.guard_dashboard, name='guard_dashboard'),
    path('guardia/export/', views.guard_export_registros, name='guard_export_registros'),
    path('mecanico/tareas/', views.mecanico_tareas, name='mecanico_tareas'),
    path('tarea/<int:pk>/', views.tarea_detail, name='tarea_detail'),
    path('tarea/<int:pk>/iniciar/', views.tarea_iniciar, name='tarea_iniciar'),
    path('tarea/<int:pk>/pausar/', views.tarea_pausar, name='tarea_pausar'),
    path('tarea/<int:pk>/reanudar/', views.tarea_reanudar, name='tarea_reanudar'),
    path('tarea/<int:pk>/completar/', views.tarea_completar, name='tarea_completar'),
    path('tarea/<int:pk>/editar-estado/', views.tarea_editar_estado, name='tarea_editar_estado'),
    path('tarea/<int:pk>/editar/', views.tarea_edit, name='tarea_edit'),
    path('tarea/<int:pk>/comentario/', views.tarea_agregar_comentario, name='tarea_agregar_comentario'),
    path('<int:ingreso_pk>/documento/subir/', views.documento_upload, name='documento_upload'),
    
    # Rutas para Chofer - Solicitud de Ingreso
    path('chofer/solicitar/', views.chofer_solicitar_ingreso, name='chofer_solicitar_ingreso'),
    path('chofer/mis-solicitudes/', views.chofer_mis_solicitudes, name='chofer_mis_solicitudes'),
    path('chofer/notificaciones/', views.chofer_notificaciones, name='chofer_notificaciones'),
    
    # Rutas para Supervisor - Notificaciones y Aprobación
    path('supervisor/notificaciones/', views.supervisor_notificaciones, name='supervisor_notificaciones'),
    path('supervisor/solicitud/<int:solicitud_id>/aprobar/', views.supervisor_aprobar_solicitud, name='supervisor_aprobar_solicitud'),
    path('supervisor/solicitud/<int:solicitud_id>/rechazar/', views.supervisor_rechazar_solicitud, name='supervisor_rechazar_solicitud'),
    path('supervisor/solicitud/<int:solicitud_id>/agendar/', views.supervisor_agendar_solicitud, name='supervisor_agendar_solicitud'),
    
    # API para autocompletar datos del guardia
    path('api/vehiculo-por-patente/', views.api_vehiculo_por_patente, name='api_vehiculo_por_patente'),
]