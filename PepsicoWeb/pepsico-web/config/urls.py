from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('health/', include('health_check.urls')),
    path('vehiculos/', include('vehiculos.urls')),
    path('ingresos/', include('ingresos.urls')),
    path('reportes/', include('reportes.urls')),
    path('', include('core.urls')),
]
