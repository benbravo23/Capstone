from django.urls import path

from . import views

urlpatterns = [
    path('', views.vehiculos_list, name='vehiculos_list'),
    path('exportar_excel/', views.vehiculos_export_excel, name='vehiculos_export_excel'),
    path('<int:pk>/', views.vehiculo_detail, name='vehiculo_detail'),
    path('crear/', views.vehiculo_create, name='vehiculo_create'),
    path('<int:pk>/editar/', views.vehiculo_edit, name='vehiculo_edit'),
    path('<int:pk>/eliminar/', views.vehiculo_delete, name='vehiculo_delete'),
    path('documento/<int:doc_id>/eliminar/', views.eliminar_documento_vehiculo, name='eliminar_documento_vehiculo'),
]