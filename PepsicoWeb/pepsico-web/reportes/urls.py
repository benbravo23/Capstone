from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_reportes, name='reportes_dashboard'),
    path('tiempos/', views.reporte_tiempos, name='reporte_tiempos'),
    path('productividad/', views.reporte_productividad, name='reporte_productividad'),
    path('repuestos/', views.reporte_repuestos, name='reporte_repuestos'),
    path('vehiculos-criticos/', views.reporte_vehiculos_criticos, name='reporte_vehiculos_criticos'),
    path('exportar/', views.exportar_reporte_csv, name='exportar_reporte_csv'),
    path('exportar_pdf/', views.exportar_reporte_pdf, name='exportar_reporte_pdf'),
]