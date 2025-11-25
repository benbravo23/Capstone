from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='user_logout'),  
    
    # Importación CSV
    path('import/vehiculos/', views.import_vehiculos, name='import_vehiculos'),
    path('import/usuarios/', views.import_usuarios, name='import_usuarios'),
    path('import/result/', views.import_result, name='import_result'),
    
    # Descargar plantillas
    path('download/vehiculos-template/', views.download_vehiculos_template, name='download_vehiculos_template'),
    path('download/usuarios-template/', views.download_usuarios_template, name='download_usuarios_template'),
    
    # Gestión de usuarios
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('usuarios/<int:usuario_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:usuario_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
]