from django.contrib import admin
from .models import Notificacion


# Notificaciones deshabilitadas del panel de admin
# @admin.register(Notificacion)
# class NotificacionAdmin(admin.ModelAdmin):
#     list_display = ('titulo', 'usuario', 'tipo', 'leida', 'fecha_creacion')
#     list_filter = ('tipo', 'leida', 'fecha_creacion')
#     search_fields = ('titulo', 'mensaje', 'usuario__nombre')
#     ordering = ('-fecha_creacion',)
#     
#     actions = ['marcar_como_leidas']
#     
#     def marcar_como_leidas(self, request, queryset):
#         for notif in queryset:
#             notif.marcar_como_leida()
#         self.message_user(request, f'{queryset.count()} notificaciones marcadas como leídas.')
#     marcar_como_leidas.short_description = 'Marcar como leídas'