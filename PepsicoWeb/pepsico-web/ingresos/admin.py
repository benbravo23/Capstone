from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import IngresoTaller, Pausa, Tarea, Documento, HistorialTarea, RegistroGuardia, Maquina, SolicitudIngreso


class PausaInline(admin.TabularInline):
    model = Pausa
    extra = 0
    readonly_fields = ('duracion_minutos',)


class TareaInline(admin.TabularInline):
    model = Tarea
    extra = 0


class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 0


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'numero', 'activa')
    list_filter = ('tipo', 'activa')
    search_fields = ('nombre',)
    ordering = ('tipo', 'numero')


@admin.register(IngresoTaller)
class IngresoTallerAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'fecha_programada', 'maquina', 'estado', 'supervisor', 'chofer', 'registro_guardia')
    list_filter = ('estado', 'fecha_programada', 'maquina')
    search_fields = ('vehiculo__patente', 'motivo')
    ordering = ('-fecha_programada',)
    inlines = [TareaInline, PausaInline, DocumentoInline]
    
    fieldsets = (
        ('Vehículo', {
            'fields': ('vehiculo', 'kilometraje_ingreso')
        }),
        ('Control de Acceso', {
            'fields': ('registro_guardia',)
        }),
        ('Máquina Asignada', {
            'fields': ('maquina',)
        }),
        ('Programación', {
            'fields': ('fecha_programada', 'supervisor', 'chofer')
        }),
        ('Detalles', {
            'fields': ('motivo', 'observaciones', 'estado')
        }),
        ('Fechas de Proceso', {
            'fields': ('fecha_llegada', 'fecha_inicio', 'fecha_termino')
        }),
    )

@admin.register(Pausa)
class PausaAdmin(admin.ModelAdmin):
    list_display = ('ingreso', 'motivo', 'fecha_inicio', 'fecha_fin', 'duracion_minutos')
    list_filter = ('fecha_inicio',)
    search_fields = ('ingreso__vehiculo__patente', 'motivo')


class HistorialTareaInline(admin.TabularInline):
    model = HistorialTarea
    extra = 0
    readonly_fields = ('tipo_cambio', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'usuario', 'fecha')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'ingreso', 'mecanico', 'estado', 'prioridad', 'tiempo_transcurrido_minutos', 'fecha_inicio')
    list_filter = ('estado', 'prioridad', 'mecanico', 'fecha_asignacion')
    search_fields = ('titulo', 'ingreso__vehiculo__patente')
    inlines = [HistorialTareaInline]
    readonly_fields = ('fecha_creacion', 'fecha_asignacion', 'tiempo_transcurrido_minutos')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('ingreso', 'titulo', 'descripcion', 'mecanico')
        }),
        ('Detalles', {
            'fields': ('estado', 'prioridad', 'repuestos_utilizados', 'observaciones')
        }),
        ('Tiempos', {
            'fields': ('tiempo_estimado_minutos', 'fecha_inicio', 'fecha_completada', 'tiempo_transcurrido_minutos')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_asignacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre_original', 'tipo', 'vehiculo', 'ingreso', 'fecha_subida', 'subido_por')
    list_filter = ('tipo', 'fecha_subida')
    search_fields = ('nombre_original', 'vehiculo__patente')


@admin.register(HistorialTarea)
class HistorialTareaAdmin(admin.ModelAdmin):
    list_display = ('tarea', 'tipo_cambio', 'campo_modificado', 'usuario', 'fecha')
    list_filter = ('tipo_cambio', 'fecha')
    search_fields = ('tarea__titulo', 'descripcion')
    readonly_fields = ('tarea', 'tipo_cambio', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'usuario', 'fecha')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RegistroGuardia)
class RegistroGuardiaAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'chofer_nombre', 'fecha_entrada', 'fecha_salida', 'registrado_por')
    list_filter = ('fecha_entrada', 'registrado_por')
    search_fields = ('patente', 'marca', 'chofer_nombre', 'vehiculo__patente')
    readonly_fields = ('fecha_entrada', 'duracion_minutos')
    ordering = ('-fecha_entrada',)
    
    fieldsets = (
        ('Vehículo', {
            'fields': ('vehiculo', 'patente', 'marca')
        }),
        ('Chofer', {
            'fields': ('chofer_nombre', 'chofer')
        }),
        ('Detalles', {
            'fields': ('motivo', 'observaciones')
        }),
        ('Registro', {
            'fields': ('fecha_entrada', 'fecha_salida', 'duracion_minutos', 'registrado_por'),
            'classes': ('collapse',)
        }),
    )