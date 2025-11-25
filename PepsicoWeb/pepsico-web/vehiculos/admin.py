from django.contrib import admin
from .models import Vehiculo


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'año', 'tipo', 'flota', 'kilometraje', 'activo')
    list_filter = ('tipo', 'activo', 'marca')
    search_fields = ('patente', 'vin', 'marca', 'modelo', 'flota')
    ordering = ('patente',)
    list_per_page = 25
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('patente', 'vin', 'marca', 'modelo', 'año', 'tipo')
        }),
        ('Detalles Operativos', {
            'fields': ('flota', 'kilometraje', 'activo')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
